from django.core.management.base import BaseCommand
from workers.models import WorkerProfile, WorkerServiceOffering
from catalog.models import ServiceCategory

class Command(BaseCommand):
    help = "Ensure all verified workers have offerings for their selected categories"

    def handle(self, *args, **options):
        verified_workers = WorkerProfile.objects.filter(verification_status='verified')
        count = 0
        for worker in verified_workers:
            categories = worker.categories.all()
            for cat in categories:
                for service in cat.services.filter(is_active=True):
                    offering, created = WorkerServiceOffering.objects.get_or_create(
                        worker=worker, service=service
                    )
                    if created:
                        count += 1
        self.stdout.write(self.style.SUCCESS(f"Created {count} missing service offerings for verified workers."))
