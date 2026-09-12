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
from django.db import transaction

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseForbidden
from django.conf import settings

from accounts.models import User, Notification
from workers.models import WorkerProfile, WorkerServiceOffering
from .models import BulkServiceRequest, BulkAssignment
from .bulk_forms import BulkServiceRequestForm
from .services import find_best_workers, auto_book_ranking_key, is_worker_available_for_range
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


# ... (existing code) ...
@login_required
@user_passes_test(_is_institution, login_url='core:home')
def auto_bulk_book(request, request_id):
    """
    Strict Auto Booking for Bulk Requests.
    Selects and assigns workers based on distance, skill, reliability, and availability.
    """
    bulk = get_object_or_404(BulkServiceRequest, id=request_id, institution=request.user)
    if bulk.status != BulkServiceRequest.Status.REQUESTED:
        messages.error(request, "Auto booking is only available for new requests.")
        return redirect('bookings:bulk_request_detail', request_id=request_id)

    with transaction.atomic():
        # 1. Lock the request to prevent concurrent claims or auto-books
        bulk = BulkServiceRequest.objects.select_for_update().get(pk=bulk.pk)
        if bulk.status != BulkServiceRequest.Status.REQUESTED:
            messages.error(request, "This request has already been claimed or processed.")
            return redirect('bookings:bulk_request_detail', request_id=request_id)

        # 2. Identify eligible candidates
        # Verified, available now, linked to a society, and offers the service
        candidates = WorkerProfile.objects.filter(
            verification_status=WorkerProfile.VerificationStatus.VERIFIED,
            is_available_now=True,
            society__isnull=False,
            offerings__service=bulk.service
        ).distinct()

        if not candidates.exists():
            messages.error(request, "No eligible workers found for this service.")
            return redirect('bookings:bulk_request_detail', request_id=request_id)

        # 3. Annotate with distance
        workers_list, geo_available = annotate_workers_with_distance(
            bulk.latitude, bulk.longitude, list(candidates)
        )

        # 4. Lock candidates to prevent double-booking
        candidate_ids = [w.id for w in workers_list]
        WorkerProfile.objects.filter(id__in=candidate_ids).select_for_update()

        # 5. Refine by distance and availability range
        final_candidates = []
        for w in workers_list:
            # Distance check (e.g., max 50km or worker's own radius)
            dist = getattr(w, 'distance_km', None)
            if dist is not None and dist > 50:
                continue

            # Availability check for the specific date range
            if not is_worker_available_for_range(w, bulk.start_date, bulk.duration_days):
                continue

            final_candidates.append(w)

        if not final_candidates:
            messages.error(request, "No available workers found for the requested dates and location.")
            return redirect('bookings:bulk_request_detail', request_id=request_id)

        # 6. Rank candidates using the strict ranking key
        # We use the annotated distance_km for the ranking key
        final_candidates.sort(key=lambda w: auto_book_ranking_key(w, getattr(w, 'distance_km', 2.0)))

        # 7. Assign top N workers
        matched_workers = final_candidates[:bulk.workers_required]
        count = len(matched_workers)

        for worker in matched_workers:
            BulkAssignment.objects.get_or_create(bulk_request=bulk, worker=worker)

        # Auto-assign the society of the first matched worker
        if matched_workers:
            bulk.assigned_society = matched_workers[0].society
            bulk.save(update_fields=['assigned_society'])

        # 8. Update status
        if count == bulk.workers_required:
            bulk.status = BulkServiceRequest.Status.ASSIGNED
            _notify_bulk_workers(bulk)
            messages.success(request, f"Auto Book successful! {count} workers have been assigned.")
        elif count > 0:
            bulk.status = BulkServiceRequest.Status.AWAITING_APPROVAL
            messages.warning(request, f"Partial fulfillment: {count} of {bulk.workers_required} workers found. Please review.")
        else:
            messages.error(request, "No workers could be automatically assigned.")
            return redirect('bookings:bulk_request_detail', request_id=request_id)

        bulk.save(update_fields=['status'])

    return redirect('bookings:bulk_request_detail', request_id=request_id)
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

def _notify_bulk_workers(bulk):
    """Sends notification to all workers assigned to a bulk request."""
    assignments = bulk.assignments.all()
    for assignment in assignments:
        worker_user = assignment.worker.user
        Notification.objects.create(
            user=worker_user,
            message=f"Bulk Request #{bulk.id} for {bulk.service.name} has been confirmed. Address: {bulk.address}. Please coordinate with your society operator.",
            link=f"/bookings/bulk/{bulk.id}/"
        )

@login_required
@user_passes_test(_is_institution, login_url='core:home')
def approve_bulk_fulfillment(request, request_id):
    """Approves partial fulfillment of a bulk request."""
    bulk = get_object_or_404(BulkServiceRequest, id=request_id, institution=request.user)
    if request.method == 'POST' and bulk.status == BulkServiceRequest.Status.AWAITING_APPROVAL:
        bulk.status = BulkServiceRequest.Status.ASSIGNED
        bulk.save(update_fields=['status'])
        if bulk.assigned_society and bulk.assigned_society.operator:
            Notification.objects.create(
                user=bulk.assigned_society.operator,
                message=f"Bulk Request #{bulk.id} for {bulk.service.name} has been accepted by the institution. Please proceed with worker coordination.",
                link=f"/bookings/bulk/{request_id}/"
            )
        _notify_bulk_workers(bulk)
        messages.success(request, "Partial fulfillment accepted. Workers assigned.")
    return redirect('bookings:bulk_request_detail', request_id=bulk.id)

@login_required
@user_passes_test(_is_institution, login_url='core:home')
def reject_bulk_fulfillment(request, request_id):
    """Rejects partial fulfillment and returns the request to the queue."""
    bulk = get_object_or_404(BulkServiceRequest, id=request_id, institution=request.user)
    if request.method == 'POST' and bulk.status == BulkServiceRequest.Status.AWAITING_APPROVAL:
        bulk.status = BulkServiceRequest.Status.REQUESTED
        bulk.assigned_society = None
        bulk.assignments.all().delete()
        bulk.save()
        messages.info(request, "Partial fulfillment rejected. Request returned to the queue for other societies.")
    return redirect('bookings:bulk_request_detail', request_id=bulk.id)

@login_required
@require_POST
def mark_bulk_assignment_complete(request, request_id, assignment_id):
    """Worker marks their specific part of the bulk request as complete."""
    assignment = get_object_or_404(BulkAssignment, id=assignment_id, worker__user=request.user)
    bulk = assignment.bulk_request
    if bulk.status != BulkServiceRequest.Status.IN_PROGRESS:
        messages.error(request, "Work has not started yet or is already completed.")
        return redirect('bookings:bulk_request_detail', request_id=bulk.id)
    assignment.is_completed = True
    assignment.completed_at = timezone.now()
    assignment.save()
    messages.success(request, "Your part of the work has been marked as complete.")
    return redirect('bookings:bulk_request_detail', request_id=bulk.id)

@login_required
@user_passes_test(_is_society_operator, login_url='core:home')
def society_confirm_bulk_completion(request, request_id):
    """Society admin confirms all workers are done and marks the request as WORK_COMPLETED."""
    bulk = get_object_or_404(BulkServiceRequest, id=request_id, assigned_society__operator=request.user)
    if request.method == 'POST':
        if bulk.assignments.filter(is_completed=False).exists():
            messages.error(request, "Some assigned workers have not yet marked their work as complete.")
            return redirect('bookings:bulk_request_detail', request_id=bulk.id)
        bulk.status = BulkServiceRequest.Status.WORK_COMPLETED
        bulk.save(update_fields=['status'])
        Notification.objects.create(
            user=bulk.institution,
            message=f"Bulk Request #{bulk.id} for {bulk.service.name} has been completed. Please verify and confirm the work.",
            link=f"/bookings/bulk/{bulk.id}/"
        )
        messages.success(request, "Bulk request marked as completed. Customer has been notified.")
    return redirect('bookings:bulk_request_detail', request_id=bulk.id)

@login_required
@user_passes_test(_is_institution, login_url='core:home')
def rapid_bulk_book(request, request_id):
    """Algo-driven Rapid Book for Bulk Requests."""
    bulk = get_object_or_404(BulkServiceRequest, id=request_id, institution=request.user)
    if bulk.status != BulkServiceRequest.Status.REQUESTED:
        messages.error(request, "Rapid booking is only available for new requests.")
        return redirect('bookings:bulk_request_detail', request_id=request_id)
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
        for worker in found_workers:
            BulkAssignment.objects.get_or_create(bulk_request=bulk, worker=worker)
        if found_workers:
            bulk.assigned_society = found_workers[0].society
            bulk.save(update_fields=['assigned_society'])
        bulk.status = BulkServiceRequest.Status.AWAITING_APPROVAL
        bulk.save(update_fields=['status'])
        messages.warning(request, f"Only {count} of {bulk.workers_required} workers were found. "
                                    f"Updated total: ₹{bulk.total_amount}. Please review and accept/reject.")
        return redirect('bookings:bulk_request_detail', request_id=request_id)
    for worker in found_workers:
        BulkAssignment.objects.get_or_create(bulk_request=bulk, worker=worker)
    if found_workers:
        bulk.assigned_society = found_workers[0].society
        bulk.save(update_fields=['assigned_society'])
    bulk.status = BulkServiceRequest.Status.ASSIGNED
    _notify_bulk_workers(bulk)
    bulk.save(update_fields=['status'])
    messages.success(request, f"Rapid Book successful! {count} workers have been assigned. They will be notified to accept.")
    return redirect('bookings:bulk_request_detail', request_id=request_id)

@login_required
@user_passes_test(_is_institution, login_url='core:home')
def auto_bulk_book(request, request_id):
    """
    Strict Auto Booking for Bulk Requests.
    Selects and assigns workers based on distance, skill, reliability, and availability.
    """
    bulk = get_object_or_404(BulkServiceRequest, id=request_id, institution=request.user)
    if bulk.status != BulkServiceRequest.Status.REQUESTED:
        messages.error(request, "Auto booking is only available for new requests.")
        return redirect('bookings:bulk_request_detail', request_id=request_id)

    with transaction.atomic():
        # 1. Lock the request to prevent concurrent claims or auto-books
        bulk = BulkServiceRequest.objects.select_for_update().get(pk=bulk.pk)
        if bulk.status != BulkServiceRequest.Status.REQUESTED:
            messages.error(request, "This request has already been claimed or processed.")
            return redirect('bookings:bulk_request_detail', request_id=request_id)

        # 2. Identify eligible candidates
        candidates = WorkerProfile.objects.filter(
            verification_status=WorkerProfile.VerificationStatus.VERIFIED,
            is_available_now=True,
            society__isnull=False,
            offerings__service=bulk.service
        ).distinct()

        if not candidates.exists():
            messages.error(request, "No eligible workers found for this service.")
            return redirect('bookings:bulk_request_detail', request_id=request_id)

        # 3. Annotate with distance
        workers_list, geo_available = annotate_workers_with_distance(
            bulk.latitude, bulk.longitude, list(candidates)
        )

        # 4. Lock candidates to prevent double-booking
        candidate_ids = [w.id for w in workers_list]
        WorkerProfile.objects.filter(id__in=candidate_ids).select_for_update()

        # 5. Refine by distance and availability range
        final_candidates = []
        for w in workers_list:
            dist = getattr(w, 'distance_km', None)
            if dist is not None and dist > 50:
                continue
            if not is_worker_available_for_range(w, bulk.start_date, bulk.duration_days):
                continue
            final_candidates.append(w)

        if not final_candidates:
            messages.error(request, "No available workers found for the requested dates and location.")
            return redirect('bookings:bulk_request_detail', request_id=request_id)

        # 6. Rank candidates using the strict ranking key
        final_candidates.sort(key=lambda w: auto_book_ranking_key(w, getattr(w, 'distance_km', 2.0)))

        # 7. Assign top N workers
        matched_workers = final_candidates[:bulk.workers_required]
        count = len(matched_workers)

        for worker in matched_workers:
            BulkAssignment.objects.get_or_create(bulk_request=bulk, worker=worker)

        if matched_workers:
            bulk.assigned_society = matched_workers[0].society
            bulk.save(update_fields=['assigned_society'])

        if count == bulk.workers_required:
            bulk.status = BulkServiceRequest.Status.ASSIGNED
            _notify_bulk_workers(bulk)
            messages.success(request, f"Auto Book successful! {count} workers have been assigned.")
        elif count > 0:
            bulk.status = BulkServiceRequest.Status.AWAITING_APPROVAL
            messages.warning(request, f"Partial fulfillment: {count} of {bulk.workers_required} workers found. Please review.")
        else:
            messages.error(request, "No workers could be automatically assigned.")
            return redirect('bookings:bulk_request_detail', request_id=request_id)

        bulk.save(update_fields=['status'])

    return redirect('bookings:bulk_request_detail', request_id=request_id)
