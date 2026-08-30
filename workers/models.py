from django.conf import settings
from django.db import models

from catalog.models import ServiceCategory, Service


class Society(models.Model):
    """Cooperative society that onboards and manages workers (FR-006)."""
    name = models.CharField(max_length=150)
    federation_name = models.CharField(max_length=150, default="Delhi-NCR Labour Federation")
    city = models.CharField(max_length=100, default="Delhi")
    registration_number = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.name


class WorkerProfile(models.Model):
    """Extended profile for users with role=worker (Section 5.2)."""

    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        UNDER_REVIEW = 'under_review', 'Under review'
        VERIFIED = 'verified', 'Verified'
        SUSPENDED = 'suspended', 'Temporarily suspended'
        REJECTED = 'rejected', 'Rejected'
        EXPIRED = 'expired', 'Verification expired'

    class SkillGrade(models.TextChoices):
        BASIC = 'basic', 'Basic'
        SKILLED = 'skilled', 'Skilled'
        ADVANCED = 'advanced', 'Advanced'
        EXPERT = 'expert', 'Expert'
        CERTIFIED = 'certified', 'Certified professional'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='worker_profile')
    society = models.ForeignKey(Society, on_delete=models.SET_NULL, null=True, blank=True, related_name='workers')
    categories = models.ManyToManyField(ServiceCategory, related_name='workers', blank=True)

    membership_number = models.CharField(max_length=40, blank=True)
    membership_date = models.DateField(null=True, blank=True)
    verification_status = models.CharField(max_length=20, choices=VerificationStatus.choices,
                                            default=VerificationStatus.PENDING)
    verification_officer = models.CharField(max_length=150, blank=True)
    verification_date = models.DateField(null=True, blank=True)

    skill_grade = models.CharField(max_length=20, choices=SkillGrade.choices, default=SkillGrade.BASIC)
    years_experience = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)
    languages_spoken = models.CharField(max_length=200, blank=True, default="Hindi, English")

    service_radius_km = models.PositiveIntegerField(default=5)
    is_available_now = models.BooleanField(default=True)

    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    completed_jobs = models.PositiveIntegerField(default=0)
    reliability_score = models.DecimalField(max_digits=4, decimal_places=2, default=0.80)

    # Section 3.6 — worker payout percentage/amount configured by the
    # federation. Kept simple as a percentage of the labour+visit charge.
    payout_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=78.0,
                                             help_text="Percentage of total charge paid to the worker.")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Worker: {self.user.get_full_name() or self.user.phone_number}"

    @property
    def is_verified(self):
        return self.verification_status == self.VerificationStatus.VERIFIED

    def recommended_score(self, distance_km=2.0):
        """FR-025 Recommended Ranking formula:
        Score = 0.35*Rating + 0.25*SkillMatch + 0.20*Availability + 0.15*Distance + 0.05*Reliability
        Normalised inputs on a 0-1 scale for a stable composite score."""
        rating_component = float(self.average_rating) / 5.0
        skill_map = {'basic': .5, 'skilled': .65, 'advanced': .8, 'expert': .9, 'certified': 1.0}
        skill_component = skill_map.get(self.skill_grade, .5)
        availability_component = 1.0 if self.is_available_now else 0.3
        distance_component = max(0.0, 1 - (distance_km / max(self.service_radius_km, 1)))
        reliability_component = float(self.reliability_score)
        score = (0.35 * rating_component + 0.25 * skill_component + 0.20 * availability_component
                 + 0.15 * distance_component + 0.05 * reliability_component)
        return round(score * 100, 1)


class WorkerDocument(models.Model):
    """FR-009 Document Upload."""
    class DocType(models.TextChoices):
        IDENTITY = 'identity', 'Identity proof'
        ADDRESS = 'address', 'Address proof'
        SKILL_CERT = 'skill_cert', 'Skill certificate'
        LICENCE = 'licence', 'Driving licence'
        POLICE = 'police', 'Police / background verification'
        INSURANCE = 'insurance', 'Insurance details'
        TRAINING = 'training', 'Training certificate'

    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=20, choices=DocType.choices)
    file = models.FileField(upload_to='worker_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_doc_type_display()} - {self.worker}"


class WorkerServiceOffering(models.Model):
    """Links a verified worker to the specific services they can perform,
    so the matching engine (FR-038) and worker-comparison list (FR-023) can
    surface eligible workers per service. Price is never editable here —
    it always comes from Service.fixed_labour_charge / category visit charge."""
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='offerings')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='worker_offerings')
    typical_arrival_minutes = models.PositiveIntegerField(default=30)

    class Meta:
        unique_together = ('worker', 'service')

    def __str__(self):
        return f"{self.worker} -> {self.service}"


class WorkerBlockedDate(models.Model):
    """A date the worker has manually marked as unavailable (leave,
    personal reasons, etc.). Used together with existing active bookings
    to compute the blocked/occupied calendar shown at booking time."""
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='blocked_dates')
    date = models.DateField()
    reason = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('worker', 'date')
        ordering = ['date']

    def __str__(self):
        return f"{self.worker} blocked on {self.date}"


class WorkerCategoryChangeRequest(models.Model):
    """A worker's request to add/change the service categories they work
    in. Per platform policy, category changes must be approved by a
    federation administrator before they take effect — this keeps skill
    verification meaningful and prevents unverified self-declaration."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='category_change_requests')
    requested_categories = models.ManyToManyField(ServiceCategory, related_name='change_requests')
    reason = models.TextField(blank=True, help_text="Why the worker wants this change (optional).")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    admin_note = models.CharField(max_length=255, blank=True)
    reviewed_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Category change request by {self.worker} ({self.get_status_display()})"
