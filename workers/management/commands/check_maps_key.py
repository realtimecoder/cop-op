from django.conf import settings
from django.core.management.base import BaseCommand

from workers.geo import get_distances, is_configured


class Command(BaseCommand):
    help = ("Verifies the configured GOOGLE_MAPS_API_KEY actually works by making a real "
            "Distance Matrix call between two well-known Delhi landmarks (Connaught Place "
            "and India Gate). Run this after setting the key to confirm 'nearest worker' "
            "will really work before relying on it in the app.")

    def handle(self, *args, **options):
        if not is_configured():
            self.stdout.write(self.style.ERROR(
                "GOOGLE_MAPS_API_KEY is not set. Run:\n"
                "  export GOOGLE_MAPS_API_KEY=\"your-key-here\"\n"
                "then try this command again."))
            return

        self.stdout.write(f"Using key: {settings.GOOGLE_MAPS_API_KEY[:8]}... (truncated)")
        self.stdout.write("Calling Google Distance Matrix API: Connaught Place -> India Gate, Delhi...")

        # Connaught Place, New Delhi -> India Gate, New Delhi (real, well-known coordinates)
        origin = (28.6315, 77.2167)
        destinations = [(1, 28.6129, 77.2295)]

        result = get_distances(origin[0], origin[1], destinations)

        if not result:
            self.stdout.write(self.style.ERROR(
                "No result came back. This usually means one of:\n"
                "  1. The Distance Matrix API isn't enabled for this key's project\n"
                "     -> https://console.cloud.google.com/google/maps-apis/api-list\n"
                "  2. Billing isn't enabled on the Google Cloud project\n"
                "  3. The API key has restrictions that block this request "
                "(check API/IP restrictions in Google Cloud Console)\n"
                "  4. The key is invalid or was copied incorrectly\n"
                "Re-check these in the Google Cloud Console, then run this command again."))
            return

        info = result[1]
        self.stdout.write(self.style.SUCCESS(
            f"Success! Connaught Place -> India Gate: {info['distance_text']} "
            f"({info['duration_text']} by car)."))
        self.stdout.write(self.style.SUCCESS(
            "Your Google Maps API key is working correctly. "
            "'Find nearest to me' on the worker-comparison page will now show real distances."))
