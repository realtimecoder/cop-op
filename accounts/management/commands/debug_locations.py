from django.core.management.base import BaseCommand
from accounts.models import User
from workers.models import WorkerProfile

class Command(BaseCommand):
    help = "Debug user coordinates and worker profiles"

    def handle(self, *args, **options):
        self.stdout.write("--- User Locations ---")
        users = User.objects.all()
        for u in users:
            self.stdout.write(f"User: {u.get_full_name() or u.phone_number} | Role: {u.role} | Lat: {u.latitude} | Lng: {u.longitude}")

        self.stdout.write("\n--- Worker Profiles ---")
        profiles = WorkerProfile.objects.all()
        for p in profiles:
            self.stdout.write(f"Worker: {p.user.get_full_name() or p.user.phone_number} | Status: {p.verification_status} | Society: {p.society}")
