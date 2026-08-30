from django.conf import settings
from django.db import models
from django.utils import timezone

from catalog.models import Service
from workers.models import WorkerProfile


class Booking(models.Model):
    """A customer's booking of a fixed-price service with a chosen worker
    (Section 5.6, FR-028 to FR-045, UC-001)."""

    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Requested'
        ASSIGNED = 'assigned', 'Assigned'
        ACCEPTED = 'accepted', 'Accepted'
        WORKER_ARRIVING = 'worker_arriving', 'Worker arriving'
        ARRIVED = 'arrived', 'Arrived'
        WORK_STARTED = 'work_started', 'Work started'
        WORK_COMPLETED = 'work_completed', 'Work completed'
        CUSTOMER_CONFIRMED = 'customer_confirmed', 'Customer confirmed'
        PAYMENT_SETTLED = 'payment_settled', 'Payment settled'
        RATED = 'rated', 'Rated'
        CANCELLED = 'cancelled', 'Cancelled'
        REJECTED = 'rejected', 'Rejected by worker'

    # Maps each status to the exact next status a WORKER action can trigger.
    # Used to validate worker action buttons server-side — nothing here is
    # a manual "simulate" step; every transition is caused by a real
    # accept/arrive/start/complete action taken by the assigned worker.
    WORKER_ACTION_MAP = {
        Status.ASSIGNED: Status.ACCEPTED,
        Status.ACCEPTED: Status.WORKER_ARRIVING,
        Status.WORKER_ARRIVING: Status.ARRIVED,
        Status.ARRIVED: Status.WORK_STARTED,
        Status.WORK_STARTED: Status.WORK_COMPLETED,
    }

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='bookings')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')

    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, default="Delhi")
    pincode = models.CharField(max_length=10, blank=True)
    instructions = models.TextField(blank=True)

    status = models.CharField(max_length=25, choices=Status.choices, default=Status.REQUESTED)
    is_emergency = models.BooleanField(default=False)
    is_recurring = models.BooleanField(default=False)
    recurrence_frequency = models.CharField(
        max_length=10, blank=True,
        choices=[('weekly', 'Weekly'), ('monthly', 'Monthly')])

    # Snapshot of pricing at booking time (fixed at booking, per Section 3).
    visit_charge = models.DecimalField(max_digits=8, decimal_places=2)
    labour_charge = models.DecimalField(max_digits=10, decimal_places=2)

    # Builder / team booking fields (FR-033)
    workers_required = models.PositiveIntegerField(default=1)
    duration_days = models.PositiveIntegerField(default=1)

    # Hourly-service booking field — only used when Service.pricing_type == hourly.
    hours_booked = models.DecimalField(max_digits=5, decimal_places=1, default=1)

    before_photo = models.ImageField(upload_to='booking_evidence/before/', blank=True, null=True)
    after_photo = models.ImageField(upload_to='booking_evidence/after/', blank=True, null=True)
    completion_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    STATUS_FLOW = [
        Status.REQUESTED, Status.ASSIGNED, Status.ACCEPTED, Status.WORKER_ARRIVING,
        Status.ARRIVED, Status.WORK_STARTED, Status.WORK_COMPLETED,
        Status.CUSTOMER_CONFIRMED, Status.PAYMENT_SETTLED, Status.RATED,
    ]

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking #{self.id} - {self.service.name} - {self.get_status_display()}"

    @property
    def total_amount(self):
        """Section 3.5 — total = fixed visit charge + labour component.
        Material cost is intentionally excluded (FR-048). Hourly services
        bill visit charge + (hourly rate × hours booked); builder/team
        bookings multiply the fixed labour charge by workers × days."""
        if self.service.is_hourly:
            hourly_rate = self.labour_charge  # snapshot stored at booking time
            return self.visit_charge + (hourly_rate * self.hours_booked)
        if self.workers_required > 1 or self.duration_days > 1:
            return (self.labour_charge * self.workers_required * self.duration_days) + self.visit_charge
        return self.visit_charge + self.labour_charge

    def next_status(self):
        try:
            idx = self.STATUS_FLOW.index(self.status)
        except ValueError:
            return None
        if idx + 1 < len(self.STATUS_FLOW):
            return self.STATUS_FLOW[idx + 1]
        return None

    def advance_status(self):
        nxt = self.next_status()
        if nxt:
            self.status = nxt
            self.save(update_fields=['status', 'updated_at'])
        return self.status

    def progress_percent(self):
        try:
            idx = self.STATUS_FLOW.index(self.status)
            return round((idx + 1) / len(self.STATUS_FLOW) * 100)
        except ValueError:
            return 0

    ACTIVE_STATUSES = [
        Status.REQUESTED, Status.ASSIGNED, Status.ACCEPTED, Status.WORKER_ARRIVING,
        Status.ARRIVED, Status.WORK_STARTED, Status.WORK_COMPLETED, Status.CUSTOMER_CONFIRMED,
    ]


class Complaint(models.Model):
    """FR complaint/dispute handling (Section 5, BR rules)."""
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In progress'
        RESOLVED = 'resolved', 'Resolved'
        REJECTED = 'rejected', 'Rejected'

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='complaints')
    raised_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='complaints')
    subject = models.CharField(max_length=150)
    description = models.TextField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Complaint #{self.id}: {self.subject}"
