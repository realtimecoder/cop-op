from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from catalog.models import Service
from payments.models import Payment
from .models import WorkerProfile, WorkerServiceOffering, WorkerBlockedDate, WorkerCategoryChangeRequest
from .forms import (WorkerOnboardingForm, WorkerDocumentForm, WorkerProfileEditForm,
                     WorkerCategoryChangeRequestForm, WorkerBlockedDateForm)
from .geo import annotate_workers_with_distance, is_configured as maps_configured


def worker_list_for_service(request, service_id):
    """FR-022/023/024 — public comparison of eligible verified workers.
    Anyone can browse this without logging in; login is only required
    to actually create a booking.

    FR-034 to FR-038 — if the browser supplies the customer's GPS
    coordinates (lat/lng query params, set client-side via the
    "Use my location" button) and a Google Maps API key is configured,
    workers are annotated with real road distance/ETA via the Distance
    Matrix API and can be sorted by genuine nearest-first order."""
    service = get_object_or_404(Service, id=service_id, is_active=True)
    offerings = WorkerServiceOffering.objects.filter(
        service=service, worker__verification_status=WorkerProfile.VerificationStatus.VERIFIED
    ).select_related('worker', 'worker__user')

    sort = request.GET.get('sort', 'recommended')
    workers = [o.worker for o in offerings]

    customer_lat = request.GET.get('lat')
    customer_lng = request.GET.get('lng')
    used_saved_address = False
    geo_available = False

    if not customer_lat and not customer_lng and request.user.is_authenticated \
            and request.user.latitude is not None and request.user.longitude is not None:
        # No GPS button click this visit — but the customer already has a
        # geocoded address on file (saved automatically from their profile
        # address via Google Geocoding), so use that as the origin instead
        # of requiring them to click "Find nearest to me" every time.
        customer_lat = request.user.latitude
        customer_lng = request.user.longitude
        used_saved_address = True

    if customer_lat and customer_lng:
        try:
            customer_lat = float(customer_lat)
            customer_lng = float(customer_lng)
            workers, geo_available = annotate_workers_with_distance(customer_lat, customer_lng, workers)
        except ValueError:
            customer_lat = customer_lng = None
    else:
        for w in workers:
            w.distance_km = None
            w.duration_min = None
            w.duration_text = None

    if sort == 'nearest' and geo_available:
        workers.sort(key=lambda w: (w.distance_km is None, w.distance_km or 0))
    elif sort == 'rating':
        workers.sort(key=lambda w: w.average_rating, reverse=True)
    elif sort == 'experience':
        workers.sort(key=lambda w: w.years_experience, reverse=True)
    elif sort == 'available':
        workers.sort(key=lambda w: w.is_available_now, reverse=True)
    else:
        workers.sort(key=lambda w: w.recommended_score(distance_km=w.distance_km or 2.0), reverse=True)

    return render(request, 'workers/worker_list.html', {
        'service': service, 'workers': workers, 'sort': sort,
        'geo_available': geo_available,
        'maps_configured': maps_configured(),
        'used_saved_address': used_saved_address,
        'customer_lat': customer_lat, 'customer_lng': customer_lng,
    })


def worker_public_profile(request, worker_id):
    worker = get_object_or_404(WorkerProfile, id=worker_id, verification_status=WorkerProfile.VerificationStatus.VERIFIED)
    reviews = worker.reviews.select_related('customer').order_by('-created_at')[:10]
    services = Service.objects.filter(worker_offerings__worker=worker, is_active=True).distinct()
    return render(request, 'workers/worker_profile.html', {
        'worker': worker, 'reviews': reviews, 'services': services,
    })


@login_required
def onboarding(request):
    """First-time setup only. Once a worker already has categories saved,
    we send them to the profile page instead — from there, any further
    category change must go through admin approval."""
    profile, _created = WorkerProfile.objects.get_or_create(user=request.user)
    if profile.categories.exists():
        return redirect('workers:my_dashboard')

    if request.method == 'POST':
        form = WorkerOnboardingForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            # Auto-create a service offering for every active service in
            # each selected category — without this, a worker who just
            # picked categories would never actually appear for any
            # specific service's booking/comparison list (this was a real
            # bug: onboarding saved categories but never created the
            # offerings that worker_list_for_service actually queries).
            for category in profile.categories.all():
                for service in category.services.filter(is_active=True):
                    WorkerServiceOffering.objects.get_or_create(worker=profile, service=service)
            messages.success(request, "Onboarding details saved. Upload your documents to proceed to verification.")
            return redirect('workers:documents')
    else:
        form = WorkerOnboardingForm(instance=profile)
    return render(request, 'workers/onboarding.html', {'form': form})


@login_required
def documents(request):
    profile, _created = WorkerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = WorkerDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.worker = profile
            doc.save()
            if profile.verification_status == WorkerProfile.VerificationStatus.PENDING:
                profile.verification_status = WorkerProfile.VerificationStatus.UNDER_REVIEW
                profile.save(update_fields=['verification_status'])
            messages.success(request, "Document uploaded. Status: Under review by your society.")
            return redirect('workers:documents')
    else:
        form = WorkerDocumentForm()
    return render(request, 'workers/documents.html', {'form': form, 'profile': profile})


@login_required
def my_dashboard(request):
    """Worker's home base. Work only — no service browsing/booking here.
    Shows: full profile (identity + category + skills), assigned bookings
    with the review received and income earned per job, total lifetime
    earnings, and quick links to edit profile / manage availability."""
    profile, _created = WorkerProfile.objects.get_or_create(user=request.user)
    bookings = (profile.bookings
                .select_related('service', 'customer', 'payment', 'review')
                .order_by('-created_at')[:30])

    total_income = Payment.objects.filter(
        booking__worker=profile, status=Payment.Status.SUCCESS
    ).aggregate(total=Sum('worker_payout'))['total'] or 0

    pending_category_request = profile.category_change_requests.filter(
        status=WorkerCategoryChangeRequest.Status.PENDING).first()

    return render(request, 'workers/my_dashboard.html', {
        'profile': profile, 'bookings': bookings, 'total_income': total_income,
        'pending_category_request': pending_category_request,
        'blocked_dates': profile.blocked_dates.filter(date__gte=timezone.localdate()).order_by('date'),
    })


@login_required
def edit_profile(request):
    """Editable identity/skill fields. Category changes are handled by a
    separate request-and-approve flow (see request_category_change)."""
    profile, _created = WorkerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = WorkerProfileEditForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('workers:my_dashboard')
    else:
        form = WorkerProfileEditForm(instance=profile)
    return render(request, 'workers/edit_profile.html', {'form': form, 'profile': profile})


@login_required
def request_category_change(request):
    """FR — category changes require federation-admin approval before
    they take effect. The worker's current categories are unaffected
    until the request is approved from the admin dashboard."""
    profile, _created = WorkerProfile.objects.get_or_create(user=request.user)
    existing_pending = profile.category_change_requests.filter(
        status=WorkerCategoryChangeRequest.Status.PENDING).first()
    if existing_pending:
        messages.info(request, "You already have a category-change request pending admin approval.")
        return redirect('workers:my_dashboard')

    if request.method == 'POST':
        form = WorkerCategoryChangeRequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.worker = profile
            req.save()
            form.save_m2m()
            messages.success(request, "Category-change request submitted. It will apply once a federation administrator approves it.")
            return redirect('workers:my_dashboard')
    else:
        form = WorkerCategoryChangeRequestForm(initial={'requested_categories': profile.categories.all()})
    return render(request, 'workers/request_category_change.html', {'form': form, 'profile': profile})


@login_required
def manage_availability(request):
    """Lets a worker block specific dates (leave / personal reasons) so
    customers see them as unavailable at booking time."""
    profile, _created = WorkerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = WorkerBlockedDateForm(request.POST)
        if form.is_valid():
            blocked = form.save(commit=False)
            blocked.worker = profile
            try:
                blocked.save()
                messages.success(request, f"{blocked.date} marked as unavailable.")
            except Exception:
                messages.error(request, "That date is already marked unavailable.")
            return redirect('workers:manage_availability')
    else:
        form = WorkerBlockedDateForm()

    upcoming_blocks = profile.blocked_dates.order_by('date')
    upcoming_bookings = profile.bookings.filter(
        status__in=profile.bookings.model.ACTIVE_STATUSES
    ).order_by('scheduled_date')
    return render(request, 'workers/manage_availability.html', {
        'form': form, 'profile': profile,
        'upcoming_blocks': upcoming_blocks, 'upcoming_bookings': upcoming_bookings,
    })


@login_required
def unblock_date(request, block_id):
    profile = get_object_or_404(WorkerProfile, user=request.user)
    block = get_object_or_404(WorkerBlockedDate, id=block_id, worker=profile)
    if request.method == 'POST':
        block.delete()
        messages.info(request, "Date unblocked.")
    return redirect('workers:manage_availability')


def worker_passport(request, worker_id):
    """The Digital Skill Passport (SIH Phase 1A).
    Aggregates a worker's verified identity, certifications, skills,
    and professional history into a public-facing digital credential.
    """
    worker = get_object_or_404(WorkerProfile, id=worker_id, verification_status=WorkerProfile.VerificationStatus.VERIFIED)
    # Aggregate data
    docs = worker.documents.filter(is_approved=True)
    offerings = worker.offerings.select_related('service')
    bookings = worker.bookings.all().order_by('-created_at')
    reviews = worker.reviews.select_related('customer').order_by('-created_at')

    return render(request, 'workers/passport.html', {
        'worker': worker,
        'docs': docs,
        'offerings': offerings,
        'bookings': bookings,
        'reviews': reviews,
    })
