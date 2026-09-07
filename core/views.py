from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from catalog.models import ServiceCategory
from workers.models import WorkerProfile
from .models import GovernmentOpportunity, GovernmentApplication
from accounts.models import User


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


@login_required
def apply_government_opportunity(request, project_id):
    opportunity = get_object_or_404(GovernmentOpportunity, id=project_id)

    # Ensure user is a worker
    if request.user.role != User.Role.WORKER:
        messages.error(request, "Only registered workers can apply for government opportunities.")
        return redirect('core:home')

    # Get worker profile
    try:
        worker_profile = request.user.worker_profile
    except AttributeError:
        messages.error(request, "You do not have a completed worker profile. Please set up your profile first.")
        return redirect('accounts:profile')

    if request.method == 'POST':
        cover_letter = request.POST.get('cover_letter', '').strip()

        # Check if already applied
        if GovernmentApplication.objects.filter(opportunity=opportunity, worker=worker_profile).exists():
            messages.warning(request, "You have already applied for this project.")
            return redirect('core:government_opportunities')

        GovernmentApplication.objects.create(
            opportunity=opportunity,
            worker=worker_profile,
            cover_letter=cover_letter
        )
        messages.success(request, f"Your application for {opportunity.title} has been submitted successfully!")
        return redirect('core:government_opportunities')

    return render(request, 'core/government_apply.html', {
        'opportunity': opportunity,
        'project_id': project_id
    })


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
