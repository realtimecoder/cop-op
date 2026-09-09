from django.conf import settings
from django.db import models

from bookings.models import Booking, BulkAssignment
from workers.models import WorkerProfile


class Review(models.Model):
    """FR-057 to FR-061 — customer rates a completed, verified booking only."""
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review', null=True, blank=True)
    bulk_assignment = models.OneToOneField(BulkAssignment, on_delete=models.CASCADE, related_name='review', null=True, blank=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews_given')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='reviews')

    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    photo = models.ImageField(upload_to='review_photos/', blank=True, null=True)
    is_verified = models.BooleanField(default=True)  # always true: linked to completed booking
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.booking:
            return f"{self.rating}★ for {self.worker} on booking #{self.booking_id}"
        if self.bulk_assignment:
            return f"{self.rating}★ for {self.worker} on bulk assignment #{self.bulk_assignment_id}"
        return f"{self.rating}★ for {self.worker}"


class WorkerFeedback(models.Model):
    """FR-059 — worker rates customer cooperation / site readiness / payment behaviour."""
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='worker_feedback', null=True, blank=True)
    bulk_assignment = models.OneToOneField(BulkAssignment, on_delete=models.CASCADE, related_name='worker_feedback', null=True, blank=True)
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='feedback_given')
    cooperation_rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.booking:
            return f"Worker feedback on booking #{self.booking_id}"
        if self.bulk_assignment:
            return f"Worker feedback on bulk assignment #{self.bulk_assignment_id}"
        return "Worker feedback"
