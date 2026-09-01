import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from workers.models import WorkerProfile
from workers.geo import annotate_workers_with_distance

logger = logging.getLogger(__name__)

def find_best_workers(service, customer_lat=None, customer_lng=None, limit=5):
    """
    Matching Engine: Finds the best available workers for a given service.
    Ranks based on the WorkerProfile's recommended_score (Distance, Work Distribution, Rating, etc.).
    Returns a list of (worker, score) tuples.
    """
    # 1. Filter: Verified, Available, and offers the specific service
    workers = WorkerProfile.objects.filter(
        verification_status='verified',
        is_available_now=True,
        offerings__service=service
    ).select_related('user').distinct()

    if not workers.exists():
        return []

    # 2. Annotate with real road distance if coordinates are available
    workers, geo_available = annotate_workers_with_distance(customer_lat, customer_lng, list(workers))

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

def find_best_worker(service, customer_lat=None, customer_lng=None):
    """Helper to get the single best worker."""
    results = find_best_workers(service, customer_lat, customer_lng, limit=1)
    return results[0][0] if results else None
