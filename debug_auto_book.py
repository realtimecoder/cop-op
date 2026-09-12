import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coopseva.settings')
django.setup()

from bookings.models import BulkServiceRequest
from bookings.services import find_best_workers
from workers.models import WorkerProfile

def debug_worker(worker_id, service_id):
    try:
        worker = WorkerProfile.objects.get(id=worker_id)
        from catalog.models import Service
        service = Service.objects.get(id=service_id)
        
        print(f"--- Debugging Worker {worker_id} for Service {service_id} ---")
        print(f"Name: {worker.user.get_full_name()}")
        print(f"Verified: {worker.verification_status == 'verified'}")
        print(f"Available: {worker.is_available_now}")
        print(f"Society: {worker.society is not None}")
        
        offers = worker.offerings.filter(service=service).exists()
        print(f"Offers Service: {offers}")
        
        # Check the actual query used in find_best_workers
        qs = WorkerProfile.objects.filter(
            verification_status='verified',
            is_available_now=True,
            society__isnull=False,
            offerings__service=service
        ).distinct()
        
        print(f"Is worker in filtered queryset?: {qs.filter(id=worker_id).exists()}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # You can run this by passing arguments: python debug_auto_book.py <worker_id> <service_id>
    import sys
    if len(sys.argv) > 2:
        debug_worker(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python debug_auto_book.py <worker_id> <service_id>")
