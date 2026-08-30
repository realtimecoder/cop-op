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
    """
    Converts a typed street address into (lat, lng) using Google's
    Geocoding API — this is what actually lets "nearest worker" work
    from a plain typed address, instead of only from the browser's GPS
    button. Called automatically whenever a customer or worker saves
    their profile address (see accounts/views.py).

    Returns (lat, lng) tuple, or None if geocoding wasn't possible
    (no key configured, address too vague, API error, etc.) — callers
    should treat None as "leave existing coordinates alone", never as
    an error to surface to the user, since typed addresses are often
    incomplete and this must degrade gracefully.

    Note: this uses Google's Geocoding API, which is a *separate* API
    from Distance Matrx — both must be enabled on the same Google Cloud
    project for the full nearest-worker flow to work end to end:
    https://console.cloud.google.com/google/maps-apis/api-list
    """
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
        logger.info("Google Geocoding could not resolve %r: status=%s", full_address, data.get("status"))
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
    for every destination Google could resolve. Silently skips any it
    couldn't (e.g. a worker with no saved location).
    """
    if not is_configured() or not destinations:
        return {}

    dest_str = "|".join(f"{lat},{lng}" for _, lat, lng in destinations)
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
        logger.warning("Google Distance Matrix request failed: %s", exc)
        return {}

    if data.get("status") != "OK":
        logger.warning("Google Distance Matrix returned status=%s", data.get("status"))
        return {}

    results = {}
    try:
        elements = data["rows"][0]["elements"]
    except (KeyError, IndexError):
        return {}

    for (worker_id, _lat, _lng), element in zip(destinations, elements):
        if element.get("status") != "OK":
            continue
        results[worker_id] = {
            "distance_km": round(element["distance"]["value"] / 1000, 1),
            "duration_min": round(element["duration"]["value"] / 60),
            "distance_text": element["distance"]["text"],
            "duration_text": element["duration"]["text"],
        }
    return results


def annotate_workers_with_distance(customer_lat, customer_lng, workers):
    """
    Takes a list of WorkerProfile objects, attaches `.distance_km`,
    `.duration_min`, `.duration_text` to each (None if unavailable), and
    returns (workers, geo_available_bool).
    """
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
