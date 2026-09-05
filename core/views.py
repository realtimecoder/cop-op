from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from catalog.models import ServiceCategory
from workers.models import WorkerProfile
from .models import GovernmentOpportunity


def home(request):
    """Public homepage — fully browsable without login (Udemy-style)."""
    categories = ServiceCategory.objects.filter(is_active=True).prefetch_related('services')[:8]
    top_workers = WorkerProfile.objects.filter(
        verification_status=WorkerProfile.VerificationStatus.VERIFIED
    ).order_by('-average_rating')[:6]
    return render(request, 'core/home.html', {
        'categories': categories, 'top_workers': top_workers,
    })


def about(request):
    return render(request, 'core/about.html')


def how_it_works(request):
    return render(request, 'core/how_it_works.html')


def government_opportunities(request):
    opportunities = GovernmentOpportunity.objects.all().order_by('-created_at')
    return render(request, 'core/government_opportunities.html', {'opportunities': opportunities})


def apply_government_opportunity(request, project_id):
    return render(request, 'core/government_apply.html', {'project_id': project_id})


def contact(request):
    return render(request, 'core/contact.html')


def _is_federation_admin(user):
    return user.is_authenticated and (user.role == 'federation' or user.is_superuser)


@login_required
@user_passes_test(_is_federation_admin, login_url='core:home')
def pricing_policy(request):
    """Pricing policy is now an internal, federation-admin-only reference
    page (per platform policy) rather than a public page — customers see
    live pricing directly on each service/worker card at booking time,
    which is enough for transparency without exposing the full rate card."""
    categories = ServiceCategory.objects.filter(is_active=True).prefetch_related('services')
    return render(request, 'core/pricing_policy.html', {'categories': categories})
