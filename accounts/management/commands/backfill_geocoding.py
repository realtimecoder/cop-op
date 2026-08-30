from django.core.management.base import BaseCommand

from accounts.models import User
from workers.geo import geocode_address, is_configured


class Command(BaseCommand):
    help = ("Geocodes the address of every existing user (customer or worker) who has "
            "an address on file but no saved coordinates yet — fixes 'nearest worker' "
            "not matching for accounts created before Google Maps was configured, "
            "without requiring them to re-save their profile.")

    def handle(self, *args, **options):
        if not is_configured():
            self.stdout.write(self.style.ERROR(
                "GOOGLE_MAPS_API_KEY is not set — nothing to backfill. "
                "Set the key first, then run this command."))
            return

        candidates = User.objects.exclude(address='').filter(latitude__isnull=True)
        total = candidates.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS(
                "Every user with an address already has coordinates saved. Nothing to do."))
            return

        self.stdout.write(f"Found {total} user(s) with an address but no coordinates. Geocoding now...")
        updated = 0
        failed = 0
        for user in candidates:
            coords = geocode_address(user.address, user.city, user.pincode)
            if coords:
                user.latitude, user.longitude = coords
                user.save(update_fields=['latitude', 'longitude'])
                updated += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  OK  {user.get_full_name() or user.phone_number} -> {coords[0]:.5f}, {coords[1]:.5f}"))
            else:
                failed += 1
                self.stdout.write(self.style.WARNING(
                    f"  SKIP {user.get_full_name() or user.phone_number} — could not resolve "
                    f"'{user.address}, {user.city} {user.pincode}'"))

        self.stdout.write(self.style.SUCCESS(f"\nDone. Updated {updated}, skipped {failed} (out of {total})."))
