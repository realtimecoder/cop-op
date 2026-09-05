"""
Institution flow: Bulk/multiple-worker service requests -> Cooperative
assignment -> Completion (Section 5 of the SRS).

This is the piece that was previously missing — the old `Booking.
workers_required` field only multiplied a single worker's price, it
never actually linked several distinct WorkerProfile records to one
request, and no society ever "assigned" anyone. This module implements
the real three-step flow:

  1. An institution (role=builder) creates a BulkServiceRequest.
  2. A society operator "claims" it for their cooperative society, then
     hand-picks N of their OWN verified workers to fulfil it.
  3. The institution confirms completion once the work is done, and each
     assigned worker's payout is recorded (Section 12 "Track wages").
"""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404

from accounts.models import User
from workers.models import WorkerProfile, WorkerServiceOffering
from .models import BulkServiceRequest, BulkAssignment
from .bulk_forms import BulkServiceRequestForm


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

        # Split the total payout evenly across every assigned worker —
        # Section 12 "Track wages": each worker's earning is individually
        # recorded, not just one lump sum for the whole request.
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


# ---------------------------------------------------------------------
# Society-operator side: claim a request, then assign specific verified
# workers from their own cooperative society to fulfil it.
# ---------------------------------------------------------------------

@login_required
@user_passes_test(_is_society_operator, login_url='core:home')
def bulk_request_queue(request):
    """Unclaimed bulk requests any society can pick up, plus this
    operator's own society's already-claimed requests still in progress."""
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

    # Only THIS society's own verified workers who actually offer the
    # requested service can be picked — never another society's workers.
    eligible_workers = WorkerProfile.objects.filter(
        society=managed_society,
        verification_status=WorkerProfile.VerificationStatus.VERIFIED,
        offerings__service=bulk.service,
    ).distinct().select_related('user')

    if request.method == 'POST':
        selected_ids = request.POST.getlist('worker_ids')
        for worker_id in selected_ids:
            worker = get_object_or_404(WorkerProfile, id=worker_id, society=managed_society)
            BulkAssignment.objects.get_or_create(bulk_request=bulk, worker=worker)
        if bulk.workers_assigned_count > 0:
            bulk.status = BulkServiceRequest.Status.ASSIGNED if not bulk.is_fully_staffed else BulkServiceRequest.Status.IN_PROGRESS
            bulk.save(update_fields=['status'])
        messages.success(request, f"{len(selected_ids)} worker(s) assigned.")
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
