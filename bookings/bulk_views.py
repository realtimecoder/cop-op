"""
Institution flow: Bulk/multiple-worker service requests -> Cooperative
assignment -> Completion (Section 5 of the SRS).
"""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseForbidden

from accounts.models import User, Notification
from workers.models import WorkerProfile, WorkerServiceOffering
from .models import BulkServiceRequest, BulkAssignment
from .bulk_forms import BulkServiceRequestForm
from .services import find_best_workers
from payments.models import Payment, Invoice
from payments import razorpay_client

def _is_institution(user):
    return user.is_authenticated and user.role == User.Role.BUILDER


def _is_society_operator(user):
    return user.is_authenticated and (user.role == User.Role.SOCIETY or user.is_superuser)


@login_required
@user_passes_test(_is_institution, login_url='core:home')
def create_bulk_request(request):
    if request.method == 'POST':
        form = BulkServiceRequestForm(request.POST)
        if form.is_valid():
            bulk = form.save(commit=False)
            bulk.institution = request.user
            bulk.visit_charge = bulk.service.visit_charge
            bulk.labour_charge = (bulk.service.hourly_rate if bulk.service.is_hourly
                                   else bulk.service.fixed_labour_charge)
            bulk.save()
            messages.success(request, "Bulk service request submitted. A cooperative society will pick it up shortly.")
            return redirect('bookings:bulk_request_detail', request_id=bulk.id)
    else:
        form = BulkServiceRequestForm(initial={'city': request.user.city, 'address': request.user.address})
    return render(request, 'bookings/create_bulk_request.html', {'form': form})


@login_required
@user_passes_test(_is_institution, login_url='core:home')
def my_bulk_requests(request):
    requests_qs = BulkServiceRequest.objects.filter(institution=request.user).select_related('service', 'assigned_society')
    return render(request, 'bookings/my_bulk_requests.html', {'requests': requests_qs})


@login_required
def bulk_request_detail(request, request_id):
    bulk = get_object_or_404(BulkServiceRequest, id=request_id)
    is_institution = bulk.institution == request.user
    managed_society = getattr(request.user, 'managed_society', None)
    is_assigned_society_operator = managed_society and bulk.assigned_society_id == managed_society.id
    is_assigned_worker = bulk.assignments.filter(worker__user=request.user).exists()

    if not (is_institution or is_assigned_society_operator or is_assigned_worker or request.user.is_staff):
        messages.error(request, "You do not have access to this request.")
        return redirect('core:home')

    assignments = bulk.assignments.select_related('worker__user').all()
    return render(request, 'bookings/bulk_request_detail.html', {
        'bulk': bulk, 'assignments': assignments,
        'is_institution': is_institution, 'is_assigned_society_operator': is_assigned_society_operator,
    })


@login_required
@user_passes_test(_is_institution, login_url='core:home')
def confirm_bulk_completion(request, request_id):
    bulk = get_object_or_404(BulkServiceRequest, id=request_id, institution=request.user)
    if request.method == 'POST' and bulk.status == BulkServiceRequest.Status.IN_PROGRESS:
        bulk.status = BulkServiceRequest.Status.COMPLETED
        bulk.save(update_fields=['status'])

        assignments = list(bulk.assignments.select_related('worker'))
        if assignments:
            per_worker_total = bulk.total_amount / len(assignments)
            for assignment in assignments:
                pct = float(assignment.worker.payout_percentage) / 100
                assignment.payout_amount = round(Decimal(per_worker_total) * Decimal(pct), 2)
                assignment.is_completed = True
                from django.utils import timezone as tz
                assignment.completed_at = tz.now()
                assignment.save(update_fields=['payout_amount', 'is_completed', 'completed_at'])
                assignment.worker.completed_jobs += 1
                assignment.worker.save(update_fields=['completed_jobs'])
        messages.success(request, "Bulk request marked complete. Worker payouts have been recorded.")
    return redirect('bookings:bulk_request_detail', request_id=bulk.id)


@login_required
@user_passes_test(_is_institution, login_url='core:home')
def cancel_bulk_request(request, request_id):
    bulk = get_object_or_404(BulkServiceRequest, id=request_id, institution=request.user)
    if request.method == 'POST' and bulk.status in (BulkServiceRequest.Status.REQUESTED, BulkServiceRequest.Status.CLAIMED):
        bulk.status = BulkServiceRequest.Status.CANCELLED
        bulk.save(update_fields=['status'])
        messages.info(request, "Bulk request cancelled.")
    return redirect('bookings:my_bulk_requests')


@login_required
@user_passes_test(_is_society_operator, login_url='core:home')
def bulk_request_queue(request):
    managed_society = getattr(request.user, 'managed_society', None)
    if not managed_society and not request.user.is_superuser:
        messages.warning(request, "You need a cooperative society assigned to you before you can claim bulk requests.")
        return render(request, 'bookings/bulk_request_queue.html', {'unclaimed': [], 'mine': [], 'managed_society': None})

    unclaimed = BulkServiceRequest.objects.filter(status=BulkServiceRequest.Status.REQUESTED).select_related('service', 'institution')
    mine = BulkServiceRequest.objects.filter(
        assigned_society=managed_society
    ).exclude(status=BulkServiceRequest.Status.REQUESTED).select_related('service', 'institution') if managed_society else []

    return render(request, 'bookings/bulk_request_queue.html', {
        'unclaimed': unclaimed, 'mine': mine, 'managed_society': managed_society,
    })


@login_required
@user_passes_test(_is_society_operator, login_url='core:home')
def claim_bulk_request(request, request_id):
    bulk = get_object_or_404(BulkServiceRequest, id=request_id, status=BulkServiceRequest.Status.REQUESTED)
    managed_society = getattr(request.user, 'managed_society', None)
    if not managed_society:
        messages.error(request, "You need a cooperative society assigned to you before you can claim requests.")
        return redirect('bookings:bulk_request_queue')

    if request.method == 'POST':
        bulk.assigned_society = managed_society
        bulk.status = BulkServiceRequest.Status.CLAIMED
        bulk.save(update_fields=['assigned_society', 'status'])
        messages.success(request, f"Claimed for {managed_society.name}. Now assign your workers to it.")
    return redirect('bookings:assign_bulk_workers', request_id=bulk.id)


@login_required
@user_passes_test(_is_society_operator, login_url='core:home')
def assign_bulk_workers(request, request_id):
    managed_society = getattr(request.user, 'managed_society', None)
    bulk = get_object_or_404(BulkServiceRequest, id=request_id, assigned_society=managed_society)

    eligible_workers = WorkerProfile.objects.filter(
        society=managed_society,
        verification_status=WorkerProfile.VerificationStatus.VERIFIED,
        offerings__service=bulk.service,
    ).distinct().select_related('user')

    if request.method == 'POST':
        selected_ids = request.POST.getlist('worker_ids')

        # 1. Remove workers no longer selected
        bulk.assignments.exclude(worker_id__in=selected_ids).delete()

        # 2. Add newly selected workers
        for worker_id in selected_ids:
            worker = get_object_or_404(WorkerProfile, id=worker_id, society=managed_society)
            BulkAssignment.objects.get_or_create(bulk_request=bulk, worker=worker)

        # 3. Update status based on final count
        count = bulk.workers_assigned_count
        if count > 0:
            if count < bulk.workers_required:
                bulk.status = BulkServiceRequest.Status.AWAITING_APPROVAL
            else:
                bulk.status = BulkServiceRequest.Status.ASSIGNED
            bulk.save(update_fields=['status'])
        else:
            bulk.status = BulkServiceRequest.Status.CLAIMED
            bulk.save(update_fields=['status'])

        messages.success(request, f"Assignments updated: {count} worker(s) assigned.")
        return redirect('bookings:bulk_request_detail', request_id=bulk.id)

    already_assigned_ids = set(bulk.assignments.values_list('worker_id', flat=True))
    return render(request, 'bookings/assign_bulk_workers.html', {
        'bulk': bulk, 'eligible_workers': eligible_workers, 'already_assigned_ids': already_assigned_ids,
    })


@login_required
@user_passes_test(_is_society_operator, login_url='core:home')
def start_bulk_work(request, request_id):
    """Operator marks the assigned team as having started, once staffed."""
    managed_society = getattr(request.user, 'managed_society', None)
    bulk = get_object_or_404(BulkServiceRequest, id=request_id, assigned_society=managed_society)
    if request.method == 'POST' and bulk.status == BulkServiceRequest.Status.ASSIGNED:
        bulk.status = BulkServiceRequest.Status.IN_PROGRESS
        bulk.save(update_fields=['status'])
        messages.success(request, "Marked as in progress.")
    return redirect('bookings:bulk_request_detail', request_id=bulk.id)


@login_required
@user_passes_test(_is_institution, login_url='core:home')
def approve_bulk_fulfillment(request, request_id):
    """Approves partial fulfillment of a bulk request."""
    bulk = get_object_or_404(BulkServiceRequest, id=request_id, institution=request.user)
    if bulk.status != BulkServiceRequest.Status.AWAITING_APPROVAL:
        return redirect('bookings:bulk_request_detail', request_id=request_id)

    bulk.status = BulkServiceRequest.Status.ASSIGNED
    bulk.save(update_fields=['status'])

    if bulk.assigned_society and bulk.assigned_society.operator:
        Notification.objects.create(
            user=bulk.assigned_society.operator,
            message=f"Bulk Request #{bulk.id} for {bulk.service.name} has been accepted by the institution. Please proceed with worker coordination.",
            link=f"/bookings/bulk/{request_id}/"
        )

    messages.success(request, "Partial fulfillment accepted. Workers assigned.")
    return redirect('bookings:bulk_request_detail', request_id=request_id)


@login_required
@user_passes_test(_is_institution, login_url='core:home')
def reject_bulk_fulfillment(request, request_id):
    """Rejects partial fulfillment and returns the request to the queue."""
    bulk = get_object_or_404(BulkServiceRequest, id=request_id, institution=request.user)

    if bulk.status == BulkServiceRequest.Status.AWAITING_APPROVAL:
        bulk.status = BulkServiceRequest.Status.REQUESTED
        bulk.assigned_society = None
        bulk.assignments.all().delete()
        messages.info(request, "Partial fulfillment rejected. Request returned to the queue for other societies.")
    else:
        bulk.status = BulkServiceRequest.Status.REJECTED
        messages.info(request, "Bulk request rejected.")

    bulk.save()
    return redirect('bookings:my_bulk_requests')

@login_required
@user_passes_test(_is_institution, login_url='core:home')
def rapid_bulk_book(request, request_id):
    """Algo-driven Rapid Book for Bulk Requests."""
    bulk = get_object_or_404(BulkServiceRequest, id=request_id, institution=request.user)
    if bulk.status != BulkServiceRequest.Status.REQUESTED:
        messages.error(request, "Rapid booking is only available for new requests.")
        return redirect('bookings:bulk_request_detail', request_id=request_id)

    # 1. Find best candidates using the matching engine
    best_candidates = find_best_workers(
        bulk.service,
        request.user.latitude,
        request.user.longitude,
        limit=bulk.workers_required
    )

    if not best_candidates:
        messages.error(request, "No available workers found for this service.")
        return redirect('bookings:bulk_request_detail', request_id=request_id)

    found_workers = [c[0] for c in best_candidates]
    count = len(found_workers)

    if count < bulk.workers_required:
        # Partial Fulfillment: Assign what we found, then wait for approval
        for worker in found_workers:
            BulkAssignment.objects.get_or_create(bulk_request=bulk, worker=worker)

        # Auto-assign the society of the first matched worker
        if found_workers:
            bulk.assigned_society = found_workers[0].society
            bulk.save(update_fields=['assigned_society'])

        bulk.status = BulkServiceRequest.Status.AWAITING_APPROVAL
        bulk.save(update_fields=['status'])

        messages.warning(request, f"Only {count} of {bulk.workers_required} workers were found. "
                                f"Updated total: ₹{bulk.total_amount}. Please review and accept/reject.")
        return redirect('bookings:bulk_request_detail', request_id=request_id)

    # Full Fulfillment: Auto-assign and move to assigned (workers must then accept)
    for worker in found_workers:
        BulkAssignment.objects.get_or_create(bulk_request=bulk, worker=worker)

    # Auto-assign the society of the first matched worker
    if found_workers:
        bulk.assigned_society = found_workers[0].society
        bulk.save(update_fields=['assigned_society'])

    bulk.status = BulkServiceRequest.Status.ASSIGNED
    bulk.save(update_fields=['status'])
    messages.success(request, f"Rapid Book successful! {count} workers have been assigned. They will be notified to accept.")
    return redirect('bookings:bulk_request_detail', request_id=request_id)
