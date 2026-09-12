import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from workers.models import WorkerProfile, WorkerBlockedDate
from workers.geo import annotate_workers_with_distance, filter_workers_by_distance
from .models import Booking, BulkAssignment

logger = logging.getLogger(__name__)

def auto_book_ranking_key(worker, distance_km):
    """
    Ranking key for Auto Booking (Strict Priority):
    1. Shortest distance (asc)
    2. Skill Grade (Certified > Expert > Advanced > Skilled > Basic)
    3. Reliability Score (desc)
    4. Average Rating (desc)
    5. Completed Jobs (desc)
    """
    skill_map = {
        WorkerProfile.SkillGrade.CERTIFIED: 0,
        WorkerProfile.SkillGrade.EXPERT: 1,
        WorkerProfile.SkillGrade.ADVANCED: 2,
        WorkerProfile.SkillGrade.SKILLED: 3,
        WorkerProfile.SkillGrade.BASIC: 4,
    }
    grade_val = skill_map.get(worker.skill_grade, 5)

    return (
        distance_km if distance_km is not None else 999.0,
        grade_val,
        -float(worker.reliability_score),
        -float(worker.average_rating),
        -worker.completed_jobs
    )

def is_worker_available_for_range(worker, start_date, duration_days):
    """
    Checks if a worker is free for the entire range [start_date, start_date + duration_days).
    """
    end_date = start_date + timedelta(days=duration_days - 1)

    # 1. Check manually blocked dates
    if WorkerBlockedDate.objects.filter(worker=worker, date__range=(start_date, end_date)).exists():
        return False

    # 2. Check individual bookings in active statuses
    if Booking.objects.filter(
        worker=worker,
        status__in=Booking.ACTIVE_STATUSES,
        scheduled_date__range=(start_date, end_date)
    ).exists():
        return False

    # 3. Check bulk assignments
    if BulkAssignment.objects.filter(
        worker=worker,
        bulk_request__status__in=['assigned', 'in_progress', 'work_completed'],
        bulk_request__start_date__range=(start_date, end_date)
    ).exists():
        return False

    return True

def find_best_workers(service, customer_user=None, customer_lat=None, customer_lng=None, limit=5):
    """
    Matching Engine: Finds the best available workers for a given service.
    Ranks based on the WorkerProfile's recommended_score (Distance, Work Distribution, Rating, etc.).
    Returns a list of (worker, score) tuples.
    """
    all_verified_available = WorkerProfile.objects.filter(
        verification_status='verified',
        is_available_now=True,
        society__isnull=False
    ).count()

    workers = WorkerProfile.objects.filter(
        verification_status='verified',
        is_available_now=True,
        society__isnull=False,
        offerings__service=service
    ).select_related('user').distinct()

    if customer_user:
        workers = workers.exclude(user=customer_user)

    if not workers.exists():
        return []

    # 2. Annotate with real road distance if coordinates are available
    workers, geo_available = annotate_workers_with_distance(customer_lat, customer_lng, list(workers))

    # Apply strict distance filtering to ensure we don't match workers from distant cities
    if geo_available:
        workers = filter_workers_by_distance(workers, customer_lat, customer_lng)

    # 3. Scoring Logic using the model's unified recommended_score
    scored_workers = []
    for worker in workers:
        dist = worker.distance_km if (geo_available and worker.distance_km is not None) else 2.0
        score = worker.recommended_score(distance_km=dist)
        scored_workers.append((worker, score))

    # Sort by score descending, then by completed_jobs as tie-breaker
    scored_workers.sort(key=lambda x: (x[1], x[0].completed_jobs), reverse=True)

    return scored_workers[:limit]

def find_best_worker(service, customer_user=None, customer_lat=None, customer_lng=None):
    """Helper to get the single best worker."""
    results = find_best_workers(service, customer_user=customer_user, customer_lat=customer_lat, customer_lng=customer_lng, limit=1)
    return results[0][0] if results else None
