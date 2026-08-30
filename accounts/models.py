import random
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Co-opSeva platform user. Extends Django's auth user with roles
    and profile fields required across the marketplace (FR-001 to FR-005)."""

    class Role(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        BUILDER = 'builder', 'Builder / Institutional Customer'
        WORKER = 'worker', 'Worker'
        SOCIETY = 'society', 'Cooperative Society Operator'
        FEDERATION = 'federation', 'Federation Administrator'
        WELFARE = 'welfare', 'Welfare Administrator'
        FINANCE = 'finance', 'Finance Administrator'
        SUPPORT = 'support', 'Support Officer'
        PLATFORM_ADMIN = 'platform_admin', 'Platform Administrator'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    phone_number = models.CharField(max_length=15, unique=True, db_index=True)
    preferred_language = models.CharField(max_length=8, default='en')
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    emergency_contact = models.CharField(max_length=15, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    is_phone_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_federation_admin(self):
        return self.role == self.Role.FEDERATION or self.is_superuser

    @property
    def is_society_operator(self):
        return self.role == self.Role.SOCIETY


class OTPRequest(models.Model):
    """Mobile-number OTP login (FR-002). In this reference build the OTP is
    displayed on screen instead of being sent via a real SMS gateway —
    plug in an SMS provider (MSG91 / Twilio Verify / etc.) in production."""

    phone_number = models.CharField(max_length=15, db_index=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    purpose = models.CharField(
        max_length=20,
        choices=[('login', 'Login'), ('register', 'Register'), ('recovery', 'Account Recovery')],
        default='login',
    )

    @classmethod
    def generate(cls, phone_number, purpose='login'):
        code = f"{random.randint(100000, 999999)}"
        return cls.objects.create(phone_number=phone_number, code=code, purpose=purpose)

    def is_valid(self):
        return (not self.is_used) and (timezone.now() - self.created_at < timedelta(minutes=10))

    def __str__(self):
        return f"OTP {self.code} for {self.phone_number}"
