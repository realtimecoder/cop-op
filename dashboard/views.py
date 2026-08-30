from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.models import User
from catalog.models import ServiceCategory, Service
from workers.models import WorkerProfile, WorkerCategoryChangeRequest, WorkerServiceOffering
from bookings.models import Booking, Complaint
from payments.models import Payment
from reviews.models import Review


def is_federation_admin(user):
    return user.is_authenticated and (user.role == User.Role.FEDERATION or user.is_superuser)


def is_society_operator(user):
    return user.is_authenticated and (user.role == User.Role.SOCIETY or user.is_superuser)


def is_staff_role(user):
    return user.is_authenticated and (
        user.role in [User.Role.FEDERATION, User.Role.SOCIETY, User.Role.SUPPORT,
                      User.Role.FINANCE, User.Role.WELFARE, User.Role.PLATFORM_ADMIN]
        or user.is_superuser
    )


@login_required
@user_passes_test(is_staff_role, login_url='core:home')
def overview(request):
    """Role-aware dashboard landing page (FR-003 Role-Based Access)."""
    context = {
        'total_bookings': Booking.objects.count(),
        'total_workers': WorkerProfile.objects.count(),
        'total_customers': User.objects.filter(role=User.Role.CUSTOMER).count(),
        'pending_verifications': WorkerProfile.objects.filter(
            verification_status=WorkerProfile.VerificationStatus.UNDER_REVIEW).count(),
        'pending_category_requests': WorkerCategoryChangeRequest.objects.filter(
            status=WorkerCategoryChangeRequest.Status.PENDING).count(),
        'open_complaints': Complaint.objects.filter(status=Complaint.Status.OPEN).count(),
        'total_categories': ServiceCategory.objects.count(),
        'is_federation_admin': is_federation_admin(request.user),
        'is_society_operator': is_society_operator(request.user),
    }
    return render(request, 'dashboard/overview.html', context)


@login_required
@user_passes_test(is_federation_admin, login_url='core:home')
def pricing_config(request):
    """UC-002 Configure Fixed Charges — only the federation administrator
    can change visit charges, fixed labour charges, and hourly rates
    (FR-017 to FR-019, BR-015). This is the *only* place prices can be
    edited anywhere in the platform — the public /pricing-policy/ page is
    intentionally read-only, since anyone (logged in or not) can view it."""
    categories = ServiceCategory.objects.all().prefetch_related('services')

    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        new_visit_charge = request.POST.get('fixed_visit_charge')
        category = get_object_or_404(ServiceCategory, id=category_id)
        category.fixed_visit_charge = new_visit_charge
        category.save(update_fields=['fixed_visit_charge'])
        messages.success(request, f"Visit charge for {category.name} updated to ₹{new_visit_charge}.")
        return redirect('dashboard:pricing_config')

    return render(request, 'dashboard/pricing_config.html', {
        'categories': categories, 'pricing_types': Service.PricingType.choices,
    })


@login_required
@user_passes_test(is_federation_admin, login_url='core:home')
def update_service_charge(request, service_id):
    """Handles both fixed-price and hourly services: the federation admin
    picks the pricing type here and sets whichever rate applies."""
    service = get_object_or_404(Service, id=service_id)
    if request.method == 'POST':
        pricing_type = request.POST.get('pricing_type', service.pricing_type)
        service.pricing_type = pricing_type
        if pricing_type == Service.PricingType.HOURLY:
            service.hourly_rate = request.POST.get('hourly_rate') or service.hourly_rate
            service.min_hours = request.POST.get('min_hours') or service.min_hours
        else:
            service.fixed_labour_charge = request.POST.get('fixed_labour_charge') or service.fixed_labour_charge
        service.save()
        messages.success(request, f"Pricing for {service.name} updated.")
    return redirect('dashboard:pricing_config')


@login_required
@user_passes_test(is_society_operator, login_url='core:home')
def worker_verification_queue(request):
    """Society operators verify workers (FR-010, UC use in Section 5.2)."""
    workers = WorkerProfile.objects.filter(
        verification_status__in=[WorkerProfile.VerificationStatus.PENDING,
                                  WorkerProfile.VerificationStatus.UNDER_REVIEW]
    ).select_related('user')
    return render(request, 'dashboard/worker_verification_queue.html', {'workers': workers})


@login_required
@user_passes_test(is_society_operator, login_url='core:home')
def verify_worker(request, worker_id):
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    if request.method == 'POST':
        decision = request.POST.get('decision')
        worker.verification_officer = request.user.get_full_name() or request.user.phone_number
        worker.verification_date = timezone.now().date()
        if decision == 'approve':
            worker.verification_status = WorkerProfile.VerificationStatus.VERIFIED
            messages.success(request, f"{worker.user.get_full_name()} verified successfully.")
        else:
            worker.verification_status = WorkerProfile.VerificationStatus.REJECTED
            messages.warning(request, f"{worker.user.get_full_name()} rejected.")
        worker.save()
    return redirect('dashboard:worker_verification_queue')


@login_required
@user_passes_test(is_federation_admin, login_url='core:home')
def category_change_queue(request):
    """Federation-admin approval queue for worker category-change requests.
    Approving a request replaces the worker's categories with the
    requested set and auto-creates service offerings for every service in
    the newly-approved categories, so the worker immediately shows up in
    customer searches for them."""
    requests_qs = WorkerCategoryChangeRequest.objects.filter(
        status=WorkerCategoryChangeRequest.Status.PENDING
    ).select_related('worker__user').prefetch_related('requested_categories')
    return render(request, 'dashboard/category_change_queue.html', {'requests': requests_qs})


@login_required
@user_passes_test(is_federation_admin, login_url='core:home')
def decide_category_change(request, request_id):
    change_request = get_object_or_404(WorkerCategoryChangeRequest, id=request_id)
    if request.method == 'POST':
        decision = request.POST.get('decision')
        change_request.admin_note = request.POST.get('admin_note', '')
        change_request.reviewed_by = request.user.get_full_name() or request.user.phone_number
        change_request.reviewed_at = timezone.now()
        if decision == 'approve':
            worker = change_request.worker
            new_categories = list(change_request.requested_categories.all())
            worker.categories.set(new_categories)
            for category in new_categories:
                for service in category.services.filter(is_active=True):
                    WorkerServiceOffering.objects.get_or_create(worker=worker, service=service)
            change_request.status = WorkerCategoryChangeRequest.Status.APPROVED
            messages.success(request, f"Category change approved for {worker.user.get_full_name()}.")
        else:
            change_request.status = WorkerCategoryChangeRequest.Status.REJECTED
            messages.warning(request, "Category change request rejected.")
        change_request.save()
    return redirect('dashboard:category_change_queue')


@login_required
@user_passes_test(is_staff_role, login_url='core:home')
def complaints_queue(request):
    complaints = Complaint.objects.select_related('booking', 'raised_by').order_by('-created_at')
    return render(request, 'dashboard/complaints_queue.html', {'complaints': complaints})


@login_required
@user_passes_test(is_staff_role, login_url='core:home')
def resolve_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    if request.method == 'POST':
        complaint.status = Complaint.Status.RESOLVED
        complaint.resolution_notes = request.POST.get('resolution_notes', '')
        complaint.resolved_at = timezone.now()
        complaint.save()
        messages.success(request, "Complaint marked as resolved.")
    return redirect('dashboard:complaints_queue')


# ---------------------------------------------------------------------
# Full history views — admin can see every customer's and worker's
# complete activity (bookings, spend/earnings, reviews, documents).
# ---------------------------------------------------------------------

@login_required
@user_passes_test(is_staff_role, login_url='core:home')
def customer_list(request):
    customers = (User.objects.filter(role=User.Role.CUSTOMER)
                 .annotate(booking_count=Count('bookings'))
                 .order_by('-date_joined'))
    return render(request, 'dashboard/customer_list.html', {'customers': customers})


@login_required
@user_passes_test(is_staff_role, login_url='core:home')
def customer_detail(request, user_id):
    customer = get_object_or_404(User, id=user_id, role=User.Role.CUSTOMER)
    bookings = customer.bookings.select_related('service', 'worker__user', 'payment').order_by('-created_at')
    total_spend = Payment.objects.filter(
        booking__customer=customer, status=Payment.Status.SUCCESS
    ).aggregate(total=Sum('amount'))['total'] or 0
    complaints = Complaint.objects.filter(raised_by=customer).order_by('-created_at')
    return render(request, 'dashboard/customer_detail.html', {
        'customer': customer, 'bookings': bookings, 'total_spend': total_spend, 'complaints': complaints,
    })


@login_required
@user_passes_test(is_staff_role, login_url='core:home')
def worker_list(request):
    workers = (WorkerProfile.objects.select_related('user', 'society')
               .annotate(booking_count=Count('bookings'))
               .order_by('-created_at'))
    return render(request, 'dashboard/worker_list.html', {'workers': workers})


@login_required
@user_passes_test(is_staff_role, login_url='core:home')
def worker_detail(request, worker_id):
    worker = get_object_or_404(WorkerProfile.objects.select_related('user', 'society'), id=worker_id)
    bookings = worker.bookings.select_related('service', 'customer', 'payment', 'review').order_by('-created_at')
    total_income = Payment.objects.filter(
        booking__worker=worker, status=Payment.Status.SUCCESS
    ).aggregate(total=Sum('worker_payout'))['total'] or 0
    reviews = worker.reviews.select_related('customer', 'booking').order_by('-created_at')
    documents = worker.documents.order_by('-uploaded_at')
    category_requests = worker.category_change_requests.order_by('-created_at')
    return render(request, 'dashboard/worker_detail.html', {
        'worker': worker, 'bookings': bookings, 'total_income': total_income,
        'reviews': reviews, 'documents': documents, 'category_requests': category_requests,
    })
