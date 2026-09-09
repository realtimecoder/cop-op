from django.core.management.base import BaseCommand
from workers.models import WorkerProfile

class Command(BaseCommand):
    help = "Check status and availability of workers"

    def handle(self, *args, **options):
        workers = WorkerProfile.objects.all()
        for w in workers:
            print(f"Worker: {w.user.get_full_name() or w.user.phone_number} | Verified: {w.verification_status} | Available: {w.is_available_now}")
