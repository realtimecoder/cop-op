"""
Google Maps Distance Matrix integration for FR-034 to FR-038
(Geo-Location and Matching).

Given the customer's location and a list of eligible workers, this module
returns each worker annotated with real road distance (km) and travel
time (minutes) from the Google Distance Matrix API, so the platform can
sort by genuine "nearest worker" rather than a placeholder value.

If GOOGLE_MAPS_API_KEY is not configured, or the API call fails for any
reason, callers fall back to the existing rating-based recommended_score()
ranking — the feature degrades gracefully rather than breaking the page.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"

def is_configured():
    return bool(settings.GOOGLE_MAPS_API_KEY)

def geocode_address(address, city="", pincode=""):
    if not is_configured() or not address or not address.strip():
        return None

    full_address = ", ".join(part for part in [address, city, pincode, "India"] if part and part.strip())
    params = {"address": full_address, "key": settings.GOOGLE_MAPS_API_KEY}

    try:
        response = requests.get(GEOCODING_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Google Geocoding request failed for %r: %s", full_address, exc)
        return None

    if data.get("status") != "OK":
        return None

    try:
        location = data["results"][0]["geometry"]["location"]
        return (location["lat"], location["lng"])
    except (KeyError, IndexError):
        return None

def get_distances(origin_lat, origin_lng, destinations):
    """
    destinations: list of (worker_id, lat, lng) tuples.
    Returns: dict {worker_id: {"distance_km": float, "duration_min": float}}
    """
    if not is_configured() or not destinations:
        return {}

    results = {}
    # Google Distance Matrix API has a limit on the number of elements (origins * destinations).
    # To avoid MAX_DIMENSIONS_EXCEEDED, we process destinations in chunks.
    CHUNK_SIZE = 25

    for i in range(0, len(destinations), CHUNK_SIZE):
        chunk = destinations[i:i + CHUNK_SIZE]
        dest_str = "|".join(f"{lat},{lng}" for _, lat, lng in chunk)

        params = {
            "origins": f"{origin_lat},{origin_lng}",
            "destinations": dest_str,
            "mode": "driving",
            "units": "metric",
            "key": settings.GOOGLE_MAPS_API_KEY,
        }

        try:
            response = requests.get(DISTANCE_MATRIX_URL, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.error("GEO ERROR: HTTP request failed for chunk %d: %s", i, exc)
            continue

        status = data.get("status")
        if status != "OK":
            logger.error("GEO ERROR: Google API returned status: %s for chunk %d", status, i)
            continue

        try:
            rows = data.get("rows", [])
            if not rows:
                continue
            elements = rows[0].get("elements", [])

            for (worker_id, _lat, _lng), element in zip(chunk, elements):
                elem_status = element.get("status")
                if elem_status != "OK":
                    continue
                results[worker_id] = {
                    "distance_km": round(element["distance"]["value"] / 1000, 1),
                    "duration_min": round(element["duration"]["value"] / 60),
                    "distance_text": element["distance"]["text"],
                    "duration_text": element["duration"]["text"],
                }
        except (KeyError, IndexError) as exc:
            logger.error("GEO ERROR: Unexpected response structure in chunk %d: %s", i, exc)
            continue

    return results

def filter_workers_by_distance(workers, customer_lat=None, customer_lng=None):
    """
    Zomato-style distance filtering.
    Keep all workers within 50km.
    """
    if not customer_lat or not customer_lng:
        return workers

    has_dist = any(getattr(w, 'distance_km', None) is not None for w in workers)
    if not has_dist:
        return workers

    selected_workers = [w for w in workers if getattr(w, 'distance_km', None) is not None and w.distance_km <= 50]

    if len(selected_workers) > 50:
        selected_workers.sort(key=lambda w: w.distance_km)
        selected_workers = selected_workers[:50]

    return selected_workers

def annotate_workers_with_distance(customer_lat, customer_lng, workers):
    if not customer_lat or not customer_lng:
        for w in workers:
            w.distance_km = None
            w.duration_min = None
            w.duration_text = None
        return workers, False

    destinations = [
        (w.id, w.user.latitude, w.user.longitude)
        for w in workers
        if w.user.latitude is not None and w.user.longitude is not None
    ]

    distances = get_distances(customer_lat, customer_lng, destinations)

    for w in workers:
        info = distances.get(w.id)
        if info:
            w.distance_km = info["distance_km"]
            w.duration_min = info["duration_min"]
            w.duration_text = info["duration_text"]
        else:
            w.distance_km = None
            w.duration_min = None
            w.duration_text = None

    geo_available = bool(distances)
    return workers, geo_available
