from django.conf import settings
import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.utils import timezone

from bookings.models import Booking


class Wallet(models.Model):
    """Each user has a wallet to store earnings and credits (FR-018)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='INR')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet: {self.user.username} - {self.balance} {self.currency}"

    def credit(self, amount, transaction_type='earning', reference=None):
        amount = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
        self.balance += amount
        self.save()
        return WalletTransaction.objects.create(
            wallet=self, amount=amount, transaction_type='credit',
            category=transaction_type, reference=reference
        )

    def debit(self, amount, transaction_type='withdrawal', reference=None):
        amount = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
        if self.balance < amount:
            raise ValueError("Insufficient wallet balance.")
        self.balance -= amount
        self.save()
        return WalletTransaction.objects.create(
            wallet=self, amount=amount, transaction_type='debit',
            category=transaction_type, reference=reference
        )


class WalletTransaction(models.Model):
    """Audit trail for all wallet movements."""
    class Type(models.TextChoices):
        CREDIT = 'credit', 'Credit'
        DEBIT = 'debit', 'Debit'

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=Type.choices)
    category = models.CharField(max_length=50, help_text="e.g., 'earning', 'withdrawal', 'commission'")
    reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} ({self.category})"


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
    platform_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)


    created_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment {self.reference_id} - {self.get_status_display()}"

    def compute_settlement(self):
        worker = self.booking.worker
        # Use Decimal for all financial calculations to avoid precision errors and TypeErrors
        pct = Decimal(str(worker.payout_percentage)) if worker else Decimal('78.0')

        # Total amount as Decimal
        amount = self.amount

        # Worker Payout = amount * payout_percentage / 100
        self.worker_payout = (amount * pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        gross_cooperative_fee = amount - self.worker_payout

        # Calculate platform commission from the cooperative fee
        from workers.models import PlatformConfig
        comm_pct = Decimal(str(PlatformConfig.get('DEFAULT_COMMISSION', '10.0')))
        if worker and worker.society and worker.society.federation:
            comm_pct = Decimal(str(worker.society.federation.commission_percent))

        self.platform_commission = (gross_cooperative_fee * comm_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.cooperative_fee = gross_cooperative_fee - self.platform_commission


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
