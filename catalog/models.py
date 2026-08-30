from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class ServiceCategory(models.Model):
    """Major service category, e.g. Electrician, Plumber (Section 2.4)."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=40, default='tool',
                             help_text="SVG icon key used by the front-end icon set.")
    is_active = models.BooleanField(default=True)

    # FR-017 Global Visit Charge — configured once per category by the
    # federation administrator and applied to every worker in it.
    fixed_visit_charge = models.DecimalField(max_digits=8, decimal_places=2, default=150)

    class Meta:
        verbose_name_plural = 'Service categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:category_detail', args=[self.slug])


class Service(models.Model):
    """A specific bookable service within a category, e.g. 'Fan installation'
    under Electrician (FR-013 to FR-016)."""

    class Variant(models.TextChoices):
        BASIC = 'basic', 'Basic'
        STANDARD = 'standard', 'Standard'
        PREMIUM = 'premium', 'Premium'
        EMERGENCY = 'emergency', 'Emergency'
        RESIDENTIAL = 'residential', 'Residential'
        INSTITUTIONAL = 'institutional', 'Institutional'
        BUILDER = 'builder', 'Builder / Project'

    class PricingType(models.TextChoices):
        FIXED = 'fixed', 'Fixed price'
        HOURLY = 'hourly', 'Per hour'

    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, blank=True)
    description = models.TextField(blank=True)
    required_skill = models.CharField(max_length=100, blank=True)
    estimated_duration_minutes = models.PositiveIntegerField(default=60)
    tools_required = models.CharField(max_length=255, blank=True)
    variant = models.CharField(max_length=20, choices=Variant.choices, default=Variant.STANDARD)

    # FR-018 Global Labour Charge — fixed, federation-configured, identical
    # for every worker performing this service (Section 3.3). Some services
    # (e.g. domestic help, caregiving, driving) are billed per hour instead
    # of a flat labour charge — the federation administrator chooses which
    # model applies per service, and sets whichever rate applies.
    pricing_type = models.CharField(max_length=10, choices=PricingType.choices, default=PricingType.FIXED)
    fixed_labour_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                               help_text="Used when pricing type is Fixed price.")
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                       help_text="Used when pricing type is Per hour.")
    min_hours = models.PositiveIntegerField(default=1, help_text="Minimum billable hours for hourly services.")

    warranty_days = models.PositiveIntegerField(default=7)
    cancellation_policy = models.TextField(
        blank=True, default="Free cancellation up to 2 hours before the scheduled visit.")
    service_area = models.CharField(max_length=150, blank=True, default="Delhi-NCR")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category__name', 'name']
        unique_together = ('category', 'slug')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    def get_absolute_url(self):
        return reverse('catalog:service_detail', args=[self.category.slug, self.slug])

    @property
    def is_hourly(self):
        return self.pricing_type == self.PricingType.HOURLY

    @property
    def visit_charge(self):
        return self.category.fixed_visit_charge

    @property
    def total_charge(self):
        """Section 3.5 Customer Payment = fixed visit charge + labour
        component. For hourly services this shows the minimum-hours total;
        the exact amount is recalculated at booking time from the hours
        the customer actually selects."""
        if self.is_hourly:
            return self.visit_charge + (self.hourly_rate * self.min_hours)
        return self.visit_charge + self.fixed_labour_charge
