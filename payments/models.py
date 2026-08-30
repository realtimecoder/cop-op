import uuid
from django.db import models

from bookings.models import Booking


class Payment(models.Model):
    """Digital payment record for a booking (FR-051 to FR-055).
    Integrated with Razorpay in TEST MODE — see payments/razorpay_client.py.
    If Razorpay test keys aren't configured, the platform falls back to a
    clearly-labelled simulated payment so the flow never breaks."""

    class Method(models.TextChoices):
        UPI = 'upi', 'UPI'
        CARD = 'card', 'Debit / Credit card'
        NETBANKING = 'netbanking', 'Net banking'
        WALLET = 'wallet', 'Wallet'
        INSTITUTIONAL = 'institutional', 'Institutional billing'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
        PARTIALLY_REFUNDED = 'partial_refund', 'Partially refunded'

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    reference_id = models.CharField(max_length=40, unique=True, default=uuid.uuid4, editable=False)
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.UPI)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Razorpay test-mode integration fields.
    razorpay_order_id = models.CharField(max_length=64, blank=True)
    razorpay_payment_id = models.CharField(max_length=64, blank=True)
    razorpay_signature = models.CharField(max_length=128, blank=True)
    is_simulated = models.BooleanField(
        default=False, help_text="True if Razorpay wasn't configured and this payment was simulated instead.")

    # Section 3.6 / 12.3 — settlement split.
    worker_payout = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cooperative_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment {self.reference_id} - {self.get_status_display()}"

    def compute_settlement(self):
        worker = self.booking.worker
        pct = float(worker.payout_percentage) if worker else 78.0
        self.worker_payout = round(float(self.amount) * pct / 100, 2)
        self.cooperative_fee = round(float(self.amount) - self.worker_payout, 2)


class Invoice(models.Model):
    """FR-056 Invoice Generation — visit charge, labour charge and total
    only. Material cost is never included (FR-048, Section 3.5)."""
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=30, unique=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.invoice_number

    @staticmethod
    def generate_number(booking_id):
        return f"CSV-{booking_id:06d}-{uuid.uuid4().hex[:5].upper()}"
