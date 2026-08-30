#!/usr/bin/env python3
"""
check_google_maps.py
=====================

Standalone script (no Django required) to verify that a Google Maps
Distance Matrix API key is set correctly and actually works — exactly
what Co-opSeva's "Find nearest worker" feature depends on.

USAGE
-----
    export GOOGLE_MAPS_API_KEY="your-key-here"
    python3 check_google_maps.py

Or pass the key directly as an argument (useful for a quick one-off test
without touching your shell's environment):

    python3 check_google_maps.py rzp_test_ignore_this_is_a_maps_key_example

WHAT IT DOES
------------
1. Confirms the key is present (env var or CLI argument).
2. Runs several real Distance Matrix API calls against well-known,
   fixed Delhi landmarks — a mix of short and long distances, and a
   multi-destination call (the same shape of request the app makes when
   comparing several workers at once).
3. Prints a clear PASS/FAIL per test case with the actual distance/time
   Google returned, so you can eyeball that the numbers look sane.
4. If anything fails, prints the most likely cause in plain language
   (API not enabled, billing not enabled, key restrictions, bad key,
   quota/rate limit, network issue) instead of just dumping a raw error.

This script deliberately has ONE dependency: the `requests` library
(`pip install requests`). It does not need Django, the project's
settings, or a database — you can run it on any machine to sanity-check
a key before deploying it.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error

DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

# A handful of real, fixed Delhi-NCR coordinates used purely as test
# fixtures — chosen because they're well-known, stable, and give a mix
# of short/medium/long distances so a working key returns clearly sane
# numbers (not all zeros, not all identical).
LANDMARKS = {
    "Connaught Place": (28.6315, 77.2167),
    "India Gate": (28.6129, 77.2295),
    "Qutub Minar": (28.5245, 77.1855),
    "Indira Gandhi Intl Airport (T3)": (28.5562, 77.1000),
    "Noida Sector 62": (28.6270, 77.3720),
}

TEST_CASES = [
    # (label, origin_name, destination_names)
    ("Short in-city hop", "Connaught Place", ["India Gate"]),
    ("Medium distance", "Connaught Place", ["Qutub Minar"]),
    ("Longer cross-city distance", "Connaught Place", ["Noida Sector 62"]),
    ("Airport route", "Connaught Place", ["Indira Gandhi Intl Airport (T3)"]),
    ("Multi-destination (mirrors real worker-comparison call)", "Connaught Place",
     ["India Gate", "Qutub Minar", "Noida Sector 62"]),
]


def color(text, code):
    # Plain ANSI colors; harmless if the terminal doesn't support them.
    return f"\033[{code}m{text}\033[0m"


def ok(text):
    return color(text, "92")  # green


def fail(text):
    return color(text, "91")  # red


def warn(text):
    return color(text, "93")  # yellow


def get_api_key():
    if len(sys.argv) > 1:
        return sys.argv[1].strip()
    return os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()


def call_distance_matrix(api_key, origin, destinations):
    """Raw call to the Distance Matrix API. Returns (success, data_or_error)."""
    params = {
        "origins": f"{origin[0]},{origin[1]}",
        "destinations": "|".join(f"{lat},{lng}" for lat, lng in destinations),
        "mode": "driving",
        "units": "metric",
        "key": api_key,
    }
    url = f"{DISTANCE_MATRIX_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            body = response.read().decode("utf-8")
            return True, json.loads(body)
    except urllib.error.URLError as exc:
        return False, {"network_error": str(exc)}
    except json.JSONDecodeError as exc:
        return False, {"parse_error": str(exc)}


def diagnose(data):
    """Turns Google's response/error into a plain-language explanation."""
    top_status = data.get("status", "")
    error_message = data.get("error_message", "")

    if "network_error" in data:
        return ("Could not reach Google's servers at all. Check your internet "
                "connection or whether a firewall/proxy is blocking outbound "
                "HTTPS requests to maps.googleapis.com.")

    if top_status == "REQUEST_DENIED":
        return (
            "Google explicitly denied the request. This almost always means one of:\n"
            "    1. The Distance Matrix API isn't enabled for this key's project\n"
            "       -> https://console.cloud.google.com/google/maps-apis/api-list\n"
            "    2. Billing isn't enabled on the Google Cloud project (required even for free-tier usage)\n"
            "       -> https://console.cloud.google.com/billing\n"
            "    3. The API key has restrictions (HTTP referrer / IP / API restriction) that "
            "block this kind of request — check under APIs & Services -> Credentials\n"
            f"    Google's own message: {error_message or '(none provided)'}"
        )
    if top_status == "OVER_QUERY_LIMIT":
        return ("You've hit your quota or rate limit for this key. Check your usage/quota "
                "in the Google Cloud Console, or wait and retry.")
    if top_status == "INVALID_REQUEST":
        return ("The request itself was malformed — this would indicate a bug in how the "
                "request was built, not a key problem. Please report this.")
    if top_status and top_status != "OK":
        return f"Google returned status '{top_status}'. Message: {error_message or '(none)'}"
    return "Unknown issue — see the raw response printed above for details."


def run():
    print("=" * 70)
    print("Co-opSeva — Google Maps Distance Matrix API key checker")
    print("=" * 70)

    api_key = get_api_key()

    if not api_key:
        print(fail("\nNo API key found."))
        print("Set it as an environment variable and re-run:")
        print('    export GOOGLE_MAPS_API_KEY="your-key-here"')
        print("    python3 check_google_maps.py")
        print("\nOr pass it directly as an argument:")
        print("    python3 check_google_maps.py your-key-here")
        sys.exit(1)

    masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 14 else api_key[:4] + "..."
    print(f"\nUsing key: {masked}")
    print(f"Running {len(TEST_CASES)} test cases against real Delhi landmarks...\n")

    passed = 0
    failed = 0

    for label, origin_name, dest_names in TEST_CASES:
        origin = LANDMARKS[origin_name]
        destinations = [LANDMARKS[name] for name in dest_names]

        print(f"--- {label} ---")
        print(f"    Origin:       {origin_name}")
        print(f"    Destinations: {', '.join(dest_names)}")

        success, data = call_distance_matrix(api_key, origin, destinations)

        if not success:
            print(fail(f"    FAIL — {diagnose(data)}"))
            failed += 1
            print()
            continue

        status = data.get("status")
        if status != "OK":
            print(fail(f"    FAIL — Google status: {status}"))
            print(fail(f"    {diagnose(data)}"))
            failed += 1
            print()
            continue

        try:
            elements = data["rows"][0]["elements"]
        except (KeyError, IndexError):
            print(fail("    FAIL — response was OK but had no usable results. Raw response:"))
            print(json.dumps(data, indent=2))
            failed += 1
            print()
            continue

        all_ok = True
        for dest_name, element in zip(dest_names, elements):
            if element.get("status") != "OK":
                print(fail(f"    FAIL — could not route to {dest_name}: {element.get('status')}"))
                all_ok = False
                continue
            dist = element["distance"]["text"]
            dur = element["duration"]["text"]
            print(ok(f"    OK — {dest_name}: {dist}, {dur} by car"))

        if all_ok:
            passed += 1
        else:
            failed += 1
        print()

    print("=" * 70)
    if failed == 0:
        print(ok(f"ALL {passed} TEST CASES PASSED."))
        print(ok("Your Google Maps API key is correctly configured and working."))
        print(ok("'Find nearest to me' in Co-opSeva will show real distances and travel times."))
    else:
        print(fail(f"{failed} of {len(TEST_CASES)} test cases FAILED, {passed} passed."))
        print(warn("\nFix the issue(s) printed above, then run this script again."))
        print(warn("Common checklist:"))
        print(warn("  [ ] Distance Matrix API is enabled on the Google Cloud project"))
        print(warn("  [ ] Billing account is linked to that project"))
        print(warn("  [ ] The API key has no restriction that blocks server-side calls"))
        print(warn("  [ ] The key was copied correctly (no extra spaces/quotes)"))
    print("=" * 70)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run()
