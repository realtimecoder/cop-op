import logging
from datetime import timedelta, datetime, time
from django.utils import timezone
from django.db.models import Q
from workers.models import WorkerProfile, WorkerBlockedDate
from workers.geo import annotate_workers_with_distance, filter_workers_by_distance
from .models import Booking, BulkAssignment

logger = logging.getLogger(__name__)

def is_worker_available(worker, date, start_time=None, duration_days=1, hours_booked=1):
    """Checks if a worker is available for a requested time slot.
    Prevents concurrent bookings across individual bookings, bulk assignments, and blocked dates.
    """
    # 1. Check manually blocked dates
    if WorkerBlockedDate.objects.filter(worker=worker, date=date).exists():
        return False

    # Define the requested interval [S_req, E_req]
    if start_time:
        # Specific time slot booking
        s_req = datetime.combine(date, start_time)
        # timedelta hours must be a float or int, not Decimal
        e_req = s_req + timedelta(hours=float(hours_booked))
    else:
        # Whole-day/Bulk booking
        s_req = datetime.combine(date, time.min)
        e_req = s_req + timedelta(days=duration_days)

    # 2. Check individual bookings (overlap check)
    active_bookings = Booking.objects.filter(
        worker=worker,
        status__in=Booking.ACTIVE_STATUSES
    ).filter(
        # Rough date filter to optimize query
        scheduled_date__gte=date - timedelta(days=1),
        scheduled_date__lte=date + timedelta(days=duration_days + 1)
    )
    for b in active_bookings:
        # Individual bookings can span multiple days if duration_days > 1
        b_start = datetime.combine(b.scheduled_date, b.scheduled_time)
        b_end = b_start + timedelta(days=b.duration_days - 1, hours=float(b.hours_booked))
        if s_req < b_end and b_start < e_req:
            return False

    # 3. Check bulk assignments (overlap check)
    bulk_assignments = BulkAssignment.objects.filter(worker=worker).select_related('bulk_request')
    for ba in bulk_assignments:
        bulk = ba.bulk_request
        b_start = datetime.combine(bulk.start_date, time.min)
        b_end = b_start + timedelta(days=bulk.duration_days)
        if s_req < b_end and b_start < e_req:
            return False

    return True

def find_best_workers(service, customer_user=None, customer_lat=None, customer_lng=None, limit=5, scheduled_date=None, scheduled_time=None):
    """
    Matching Engine: Finds the best available workers for a given service.
    Ranks based on the WorkerProfile's recommended_score (Distance, Work Distribution, Rating, etc.).
    Returns a list of (worker, score) tuples.
    """
    # 1. Filter: Verified, Available, linked to a society, and offers the specific service
    workers = WorkerProfile.objects.filter(
        verification_status='verified',
        is_available_now=True,
        society__isnull=False,
        offerings__service=service
    ).select_related('user').distinct()

    # Availability Filter: If a date/time is specified, exclude occupied workers
    if scheduled_date:
        # We filter in Python because the interval check is complex
        worker_list = list(workers)
        available_workers = [
            w for w in worker_list
            if is_worker_available(w, scheduled_date, start_time=scheduled_time)
        ]
        # Re-wrap as a list to maintain flow, though we lose the queryset for a moment
        # We'll convert back to list for distance annotation anyway
        workers = available_workers
    else:
        workers = list(workers)

    # Prevent workers from booking themselves
    if customer_user:
        workers = [w for w in workers if w.user != customer_user]

    if not workers:
        return []

    # 2. Annotate with real road distance if coordinates are available
    # Note: annotate_workers_with_distance expects a list of workers
    workers, geo_available = annotate_workers_with_distance(customer_lat, customer_lng, workers)

    # Apply strict distance filtering to ensure we don't match workers from distant cities
    if geo_available:
        workers = filter_workers_by_distance(workers, customer_lat, customer_lng)

    # 3. Scoring Logic using the model's unified recommended_score
    scored_workers = []
    for worker in workers:
        # Use the distance from geo-annotation if available, otherwise default to 2.0km
        dist = worker.distance_km if (geo_available and worker.distance_km is not None) else 2.0
        score = worker.recommended_score(distance_km=dist)
        scored_workers.append((worker, score))

    # Sort by score descending, then by completed_jobs as tie-breaker
    scored_workers.sort(key=lambda x: (x[1], x[0].completed_jobs), reverse=True)

    return scored_workers[:limit]

def find_best_worker(service, customer_user=None, customer_lat=None, customer_lng=None, scheduled_date=None, scheduled_time=None):
    """Helper to get the single best worker."""
    results = find_best_workers(service, customer_user=customer_user, customer_lat=customer_lat, customer_lng=customer_lng, limit=1, scheduled_date=scheduled_date, scheduled_time=scheduled_time)
    return results[0][0] if results else None
