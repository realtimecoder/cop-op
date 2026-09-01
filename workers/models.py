from django.conf import settings
from django.db import models
from django.utils import timezone

from catalog.models import ServiceCategory, Service


class Federation(models.Model):
    """Top-level cooperative federation — only an Admin (platform
    superuser) can create one and appoint who manages it. A federation
    owns its own pricing (Phase 4) and has many societies under it.
    A society without a federation is "independent" and runs its own
    pricing/queries/work — see Society.federation (nullable)."""
    name = models.CharField(max_length=150, unique=True)
    city = models.CharField(max_length=100, default="Delhi")
    registration_number = models.CharField(max_length=50, blank=True)

    admin_user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='managed_federation',
        help_text="The user account (role=federation) who administers this federation.")

    commission_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.0,
        help_text="Platform commission taken from this federation's earnings, set by Admin only.")

    is_banned = models.BooleanField(default=False)
    ban_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, help_text="False once deleted/deactivated by Admin.")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_currently_banned(self):
        if not self.is_banned:
            return False
        if self.ban_until and self.ban_until < timezone.now():
            return False
        return True

    @property
    def average_rating(self):
        """Calculates the average rating of all societies under this federation."""
        societies = self.societies.all()
        if not societies.exists():
            return 0.0
        return round(sum(s.average_rating for s in societies) / societies.count(), 2)


class FederationJoinRequest(models.Model):
    """A society requesting to join a federation, OR a federation
    inviting an independent society — either direction requires the
    OTHER side's acceptance before the society actually becomes
    federation-governed (Section 4.2 of the platform's governance model)."""

    class InitiatedBy(models.TextChoices):
        SOCIETY = 'society', 'Requested by the society'
        FEDERATION = 'federation', 'Invited by the federation'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'

    society = models.ForeignKey('Society', on_delete=models.CASCADE, related_name='federation_requests')
    federation = models.ForeignKey(Federation, on_delete=models.CASCADE, related_name='join_requests')
    initiated_by = models.CharField(max_length=12, choices=InitiatedBy.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.society.name} <-> {self.federation.name} ({self.get_status_display()})"


class SocietyInvite(models.Model):
    """Allows a Society Operator to invite a specific verified worker by phone.
    The worker can then accept the invite from their dashboard to join the society."""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'

    society = models.ForeignKey('Society', on_delete=models.CASCADE, related_name='worker_invites')
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Invite from {self.society.name} to {self.phone_number} ({self.get_status_display()})"


class Society(models.Model):
    # ... (previous fields)
    # (Adding this to Society or creating a separate model)
    """A local Labour Cooperative Society. A society may be independent
    (federation=None — it runs its own pricing, work, and queries) or
    governed by a Federation once a join request is accepted by both
    sides (Section 4.1/4.2). Every worker belongs to exactly one
    society; a society has exactly one head account who claims/verifies
    -- wait: skill verification is Admin-only (Section 4.10) -- the head
    instead CLAIMS already admin-verified workers into the society, and
    handles the society's day-to-day work/queries/pricing."""
    name = models.CharField(max_length=150)
    city = models.CharField(max_length=100, default="Delhi")
    registration_number = models.CharField(max_length=50, blank=True)

    federation = models.ForeignKey(
        Federation, on_delete=models.SET_NULL, null=True, blank=True, related_name='societies',
        help_text="Null = independent society (sets its own pricing/policy). Set once a join request is accepted.")

    operator = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='managed_society',
        help_text="The society's Head — the account who claims workers and manages the society's day-to-day operations.")

    # Only meaningful when federation is set — the FEDERATION toggles
    # whether this society's head also personally does fieldwork
    # (Section 4.3). An independent society's head always works,
    # handles pricing, and resolves queries themselves, by definition.
    head_performs_fieldwork = models.BooleanField(default=True)

    is_banned = models.BooleanField(default=False)
    ban_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, help_text="False once deleted by Admin.")
    resignation_requested = models.BooleanField(default=False)
    resigned_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Societies'

    def __str__(self):
        return self.name

    @property
    def is_independent(self):
        return self.federation_id is None

    @property
    def is_currently_banned(self):
        if not self.is_banned:
            return False
        if self.ban_until and self.ban_until < timezone.now():
            return False
        return True

    @property
    def average_rating(self):
        """Section 4.4 — Society rating is computed from the average of its workers' ratings."""
        workers = self.workers.all()
        if not workers.exists():
            return 0.0
        return round(sum(w.average_rating for w in workers) / workers.count(), 2)


class SocietyPricing(models.Model):
    """Custom pricing for independent societies (FR-012).
    If a society is NOT associated with a federation, it can set its own
    rates for categories and services. If it is associated, it MUST
    follow the federation's pricing."""
    society = models.OneToOneField(Society, on_delete=models.CASCADE, related_name='custom_pricing')
    category_overrides = models.JSONField(
        default=dict,
        help_text="Mapping of category_id to custom visit charge. e.g. {'1': 200, '2': 150}")
    service_overrides = models.JSONField(
        default=dict,
        help_text="Mapping of service_id to custom labour charge. e.g. {'10': 500, '11': 300}")

    def __str__(self):
        return f"Custom Pricing for {self.society.name}"

    def get_visit_charge(self, category):
        return self.category_overrides.get(str(category.id))

    def get_labour_charge(self, service):
        return self.service_overrides.get(str(service.id))


class FederationPricing(models.Model):
    """Custom pricing for federations (FR-012).
    If a society is associated with a federation, it MUST follow the federation's pricing."""
    federation = models.OneToOneField(Federation, on_delete=models.CASCADE, related_name='custom_pricing')
    category_overrides = models.JSONField(
        default=dict,
        help_text='Mapping of category_id to custom visit charge.')
    service_overrides = models.JSONField(
        default=dict,
        help_text='Mapping of service_id to custom labour charge.')

    def __str__(self):
        return f"Custom Pricing for {self.federation.name}"

    def get_visit_charge(self, category):
        return self.category_overrides.get(str(category.id))

    def get_labour_charge(self, service):
        return self.service_overrides.get(str(service.id))


class PlatformConfig(models.Model):
    """Global platform settings, including the default commission for independent societies."""
    key = models.CharField(max_length=50, unique=True)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.key}: {self.value}"

    @classmethod
    def get(cls, key, default=None):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default




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
    last_worked_date = models.DateField(null=True, blank=True)

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
        """FR-025 Recommended Ranking formula (Updated for Fairness):
        Score = 0.30*Rating + 0.20*SkillMatch + 0.15*Availability + 0.10*Distance + 0.15*Fairness + 0.10*Reliability
        Fairness penalizes workers who worked in the last 1-2 days to ensure equitable work distribution."""
        rating_component = float(self.average_rating) / 5.0
        skill_map = {'basic': .5, 'skilled': .65, 'advanced': .8, 'expert': .9, 'certified': 1.0}
        skill_component = skill_map.get(self.skill_grade, .5)
        availability_component = 1.0 if self.is_available_now else 0.3
        distance_component = max(0.0, 1 - (distance_km / max(self.service_radius_km, 1)))
        reliability_component = float(self.reliability_score)

        # Fairness component: penalize very recent work (within 2 days)
        fairness_component = 1.0
        if self.last_worked_date:
            days_since_work = (timezone.localdate() - self.last_worked_date).days
            if days_since_work == 0:
                fairness_component = 0.1
            elif days_since_work == 1:
                fairness_component = 0.4
            elif days_since_work == 2:
                fairness_component = 0.7

        score = (0.30 * rating_component + 0.20 * skill_component + 0.15 * availability_component
                 + 0.10 * distance_component + 0.15 * fairness_component + 0.10 * reliability_component)
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
