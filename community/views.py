from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Min, Max
from django.http import HttpResponseForbidden
from django.utils import timezone

from catalog.models import ServiceCategory, Service
from bookings.models import Booking, Project
from .models import (
    CommunityChannel, CommunityMessage, WageSuggestion,
    FairPayRecommendation, GovernmentOpportunity, OpportunityApplication,
    Community, CommunityMembership
)
from workers.models import WorkerProfile

@login_required
def global_chat(request):
    """
    A single global chat room for all registered workers.
    """
    if not hasattr(request.user, 'worker_profile'):
        return HttpResponseForbidden("Workers only.")

    # Ensure a global community and general channel exist
    community, _ = Community.objects.get_or_create(
        slug='global',
        defaults={'name': 'Global Worker Hub', 'description': 'A place for all workers to connect.'}
    )
    channel, _ = CommunityChannel.objects.get_or_create(
        slug='general',
        community=community,
        defaults={'name': 'General Chat', 'description': 'General discussion'}
    )

    messages_list = channel.messages.select_related('user').all()
    all_channels = community.channels.all()

    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            CommunityMessage.objects.create(channel=channel, user=request.user, content=content)
            return redirect('community:global_chat')

    return render(request, 'community/channel.html', {
        'community': community,
        'channel': channel,
        'messages': messages_list,
        'channels': all_channels
    })

def community_dashboard(request):
    """
    Feature 1: Community Service Request Dashboard.
    Now shows a list of Federations/Communities that workers can request to join.
    """
    if not request.user.is_authenticated or not hasattr(request.user, 'worker_profile'):
        messages.error(request, "Only registered workers can access the community dashboard.")
        return redirect('core:home')

    communities = Community.objects.all()
    worker_profile = request.user.worker_profile

    # Track which communities the worker has already requested or joined
    memberships = CommunityMembership.objects.filter(worker=worker_profile).values_list('community_id', 'status')
    membership_map = {comm_id: status for comm_id, status in memberships}

    return render(request, 'community/dashboard.html', {
        'communities': communities,
        'membership_map': membership_map,
    })

@login_required
def request_join_community(request, community_id):
    """Allows a worker to request to join a specific community/federation."""
    if not hasattr(request.user, 'worker_profile'):
        return HttpResponseForbidden("Workers only.")

    community = get_object_or_404(Community, id=community_id)
    worker_profile = request.user.worker_profile

    membership, created = CommunityMembership.objects.get_or_create(
        community=community, worker=worker_profile
    )

    if created:
        messages.success(request, f"Your request to join {community.name} has been submitted.")
    else:
        messages.info(request, f"You have already submitted a request or are a member of {community.name}.")

    return redirect('community:dashboard')

@login_required
def manage_communities(request):
    """
    Admin view to add and manage federations/communities.
    """
    if not (request.user.is_superuser or request.user.role in ['federation', 'platform_admin']):
        return HttpResponseForbidden("Only administrators can manage communities.")

    if request.method == 'POST':
        name = request.POST.get('name')
        slug = request.POST.get('slug')
        description = request.POST.get('description', '')
        location = request.POST.get('location', '')

        if name and slug:
            Community.objects.update_or_create(
                slug=slug,
                defaults={'name': name, 'description': description, 'location': location}
            )
            messages.success(request, f"Community {name} saved successfully.")
            return redirect('community:manage_communities')
        else:
            messages.error(request, "Name and slug are required.")

    communities = Community.objects.all()
    return render(request, 'community/manage_communities.html', {
        'communities': communities
    })

@login_required
def manage_memberships(request):
    """
    Admin view to approve or reject join requests for communities.
    """
    if not (request.user.is_superuser or request.user.role in ['federation', 'platform_admin']):
        return HttpResponseForbidden("Only administrators can manage memberships.")

    # Filter for pending requests
    pending_requests = CommunityMembership.objects.filter(status=CommunityMembership.Status.PENDING).select_related('community', 'worker__user')

    return render(request, 'community/manage_memberships.html', {
        'requests': pending_requests
    })

@login_required
def update_membership_status(request, membership_id, status):
    """
    Update the status of a join request (approve/reject).
    """
    if not (request.user.is_superuser or request.user.role in ['federation', 'platform_admin']):
        return HttpResponseForbidden("Only administrators can update membership status.")

    if status not in [CommunityMembership.Status.APPROVED, CommunityMembership.Status.REJECTED]:
        messages.error(request, "Invalid status update.")
        return redirect('community:manage_memberships')

    try:
        membership = CommunityMembership.objects.get(id=membership_id)
        membership.status = status
        membership.save()

        status_text = "approved" if status == CommunityMembership.Status.APPROVED else "rejected"
        messages.success(request, f"Request from {membership.worker.user.get_full_name()} has been {status_text}.")
    except CommunityMembership.DoesNotExist:
        messages.error(request, "Membership request not found.")

    return redirect('community:manage_memberships')

@login_required
def community_index(request, community_slug):
    """
    Feature 2: Worker Community - Community Hub.
    Shows the channels for a specific community.
    """
    if not hasattr(request.user, 'worker_profile'):
        messages.error(request, "Only registered workers can access the community.")
        return redirect('core:home')

    community = get_object_or_404(Community, slug=community_slug)
    channels = community.channels.all()
    return render(request, 'community/index.html', {
        'community': community,
        'channels': channels
    })

@login_required
def community_channel(request, community_slug, channel_slug):
    """
    Feature 2: Worker Community - Full Chat Hub.
    Displays a sidebar of channels for the community and the active chat room.
    """
    if not hasattr(request.user, 'worker_profile'):
        return HttpResponseForbidden("Workers only.")

    community = get_object_or_404(Community, slug=community_slug)
    channel = get_object_or_404(CommunityChannel, slug=channel_slug, community=community)

    messages_list = channel.messages.select_related('user').all()
    all_channels = community.channels.all()

    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            CommunityMessage.objects.create(channel=channel, user=request.user, content=content)
            return redirect('community:channel', community_slug=community.slug, channel_slug=channel.slug)

    return render(request, 'community/channel.html', {
        'community': community,
        'channel': channel,
        'messages': messages_list,
        'channels': all_channels
    })

@login_required
def fair_pay_index(request):
    """
    Feature 3: Minimum Wage / Fair Pay Consensus.
    Displays aggregated anonymous worker suggestions and official recommendations.
    """
    if not hasattr(request.user, 'worker_profile'):
        messages.info(request, "You must be registered as a worker to contribute to fair pay consensus.")

    categories = ServiceCategory.objects.filter(is_active=True)

    category_stats = []
    for cat in categories:
        # Get all suggested wages for this category sorted
        suggestions = list(WageSuggestion.objects.filter(category=cat).values_list('suggested_wage', flat=True).order_by('suggested_wage'))
        count = len(suggestions)

        median_wage = None
        if count > 0:
            mid = count // 2
            if count % 2 == 0:
                median_wage = (suggestions[mid - 1] + suggestions[mid]) / 2
            else:
                median_wage = suggestions[mid]

        stats = {
            'category': cat,
            'count': count,
            'min': suggestions[0] if count > 0 else None,
            'max': suggestions[-1] if count > 0 else None,
            'avg': sum(suggestions) / count if count > 0 else None,
            'median': median_wage,
            'recommendation': FairPayRecommendation.objects.filter(category=cat, is_active=True).first()
        }
        category_stats.append(stats)

    return render(request, 'community/fair_pay.html', {
        'stats': category_stats
    })

@login_required
def fair_pay_submit(request):
    """
    Feature 3: Wage Submission.
    """
    if not hasattr(request.user, 'worker_profile'):
        return HttpResponseForbidden("Workers only.")

    if request.method == 'POST':
        cat_id = request.POST.get('category')
        service_id = request.POST.get('service')
        wage = request.POST.get('wage')
        unit = request.POST.get('unit')

        category = get_object_or_404(ServiceCategory, id=cat_id)
        service = Service.objects.filter(id=service_id).first() if service_id else None

        WageSuggestion.objects.update_or_create(
            worker=request.user.worker_profile,
            category=category,
            service=service,
            unit=unit,
            defaults={'suggested_wage': wage}
        )
        messages.success(request, "Wage suggestion submitted anonymously.")
        return redirect('community:fair_pay')

    categories = ServiceCategory.objects.filter(is_active=True)
    return render(request, 'community/fair_pay_submit.html', {
        'categories': categories
    })

def gov_hub_index(request):
    """
    Feature 4: Government Opportunities Hub - Listing.
    """
    opportunities = GovernmentOpportunity.objects.filter(is_published=True, status='open')
    return render(request, 'community/gov_index.html', {
        'opportunities': opportunities
    })

def gov_opportunity_detail(request, opp_id):
    """
    Feature 4: Government Opportunity Details.
    """
    opportunity = get_object_or_404(GovernmentOpportunity, id=opp_id)
    has_applied = False
    if request.user.is_authenticated and hasattr(request.user, 'worker_profile'):
        has_applied = OpportunityApplication.objects.filter(
            opportunity=opportunity, worker=request.user.worker_profile
        ).exists()

    return render(request, 'community/gov_detail.html', {
        'opportunity': opportunity,
        'has_applied': has_applied
    })

@login_required
def gov_apply(request, opp_id):
    """
    Feature 4: Worker Application.
    """
    if not hasattr(request.user, 'worker_profile'):
        messages.error(request, "You must be a registered worker to apply.")
        return redirect('community:gov_hub')

    opportunity = get_object_or_404(GovernmentOpportunity, id=opp_id)

    if not opportunity.is_published or opportunity.status != 'open':
        messages.error(request, "This opportunity is no longer accepting applications.")
        return redirect('community:gov_detail', opp_id=opportunity.id)

    if request.method == 'POST':
        application, created = OpportunityApplication.objects.get_or_create(
            opportunity=opportunity,
            worker=request.user.worker_profile
        )
        if created:
            messages.success(request, "Application submitted successfully.")
        else:
            messages.info(request, "You have already applied for this opportunity.")
        return redirect('community:gov_detail', opp_id=opportunity.id)

    return redirect('community:gov_detail', opp_id=opportunity.id)
