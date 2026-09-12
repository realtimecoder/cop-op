import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from workers.models import WorkerProfile
from workers.geo import annotate_workers_with_distance, filter_workers_by_distance

logger = logging.getLogger(__name__)

def find_best_workers(service, customer_user=None, customer_lat=None, customer_lng=None, limit=5):
    """
    Matching Engine: Finds the best available workers for a given service.
    Ranks based on the WorkerProfile's recommended_score (Distance, Work Distribution, Rating, etc.).
    Returns a list of (worker, score) tuples.
    """
    # 1. Filter: Verified, Available, linked to a society, and offers the specific service
    # Debugging: Let's see how many workers exist before filtering by service
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

    # Prevent workers from booking themselves
    if customer_user:
        workers = workers.exclude(user=customer_user)

    match_count = workers.count()

    match_count = workers.count()
    if match_count == 0 and all_verified_available > 0:
        logger.warning(f"Found {all_verified_available} verified available workers in societies, but 0 offer service '{service.name}'. "
                       f"Ensure workers have completed onboarding and selected the correct categories.")

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
        # Use the distance from geo-annotation if available, otherwise default to 2.0km
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
