from django.db import models
from django.conf import settings
from catalog.models import ServiceCategory, Service
from workers.models import WorkerProfile

class CommunityChannel(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110, unique=True)
    description = models.TextField(blank=True)
    is_announcement = models.BooleanField(default=False)
    community = models.ForeignKey('Community', on_delete=models.CASCADE, related_name='channels', null=True, blank=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='community_channels')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.community.name} - {self.name}"

class Community(models.Model):
    """Represents a Federation or a Local Worker Community."""
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to='community_logos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class CommunityMembership(models.Model):
    """Tracks join requests and active memberships in a community."""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='memberships')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='community_memberships')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('community', 'worker')

    def __str__(self):
        return f"{self.worker} -> {self.community} ({self.status})"

class CommunityMessage(models.Model):
    channel = models.ForeignKey(CommunityChannel, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user} in {self.channel.name}: {self.content[:20]}..."

class WageUnit(models.TextChoices):
    HOUR = 'hour', 'Per Hour'
    DAY = 'day', 'Per Day'
    JOB = 'job', 'Per Job'

class WageSuggestion(models.Model):
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='wage_suggestions')
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    suggested_wage = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=10, choices=WageUnit.choices, default='day')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('worker', 'category', 'service', 'unit')

    def __str__(self):
        return f"{self.worker} suggested {self.suggested_wage}/{self.unit} for {self.category.name}"

class FairPayRecommendation(models.Model):
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='pay_recommendations')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    min_wage = models.DecimalField(max_digits=10, decimal_places=2)
    max_wage = models.DecimalField(max_digits=10, decimal_places=2)
    unit_value = models.CharField(max_length=10, choices=WageUnit.choices, default='day')
    note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rec for {self.category.name}: {self.min_wage}-{self.max_wage}/{self.unit_value}"

class GovernmentOpportunity(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        OPEN = 'open', 'Open'
        CLOSED = 'closed', 'Closed'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    title = models.CharField(max_length=255)
    organization = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    workers_required = models.PositiveIntegerField(default=1)
    location = models.CharField(max_length=255)
    start_date = models.DateField()
    deadline = models.DateTimeField()
    budget_info = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.organization}"

class OpportunityApplication(models.Model):
    class Status(models.TextChoices):
        APPLIED = 'applied', 'Applied'
        UNDER_REVIEW = 'under_review', 'Under Review'
        SHORTLISTED = 'shortlisted', 'Shortlisted'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    opportunity = models.ForeignKey(GovernmentOpportunity, on_delete=models.CASCADE, related_name='applications')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='gov_applications')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('opportunity', 'worker')

    def __str__(self):
        return f"{self.worker} applied for {self.opportunity.title}"
