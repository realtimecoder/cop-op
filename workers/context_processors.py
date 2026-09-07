from django.conf import settings
from bookings.models import Booking
from .models import WorkerProfile

def sos_alerts(request):
    """
    Provides a list of open emergency SOS requests to all templates
    if the logged-in user is a VERIFIED worker.
    """
    if request.user.is_authenticated and request.user.role == 'worker':
        try:
            profile = WorkerProfile.objects.get(user=request.user)
            if profile.verification_status == WorkerProfile.VerificationStatus.VERIFIED:
                # Fetch SOS Requests waiting for acceptance (Broadcast-and-Claim)
                open_sos = Booking.objects.filter(
                    status=Booking.Status.WAITING_FOR_ACCEPTANCE,
                    is_emergency=True
                ).select_related('service', 'customer').order_by('-created_at')

                return {'global_open_sos': open_sos}
        except WorkerProfile.DoesNotExist:
            pass

    return {'global_open_sos': None}
