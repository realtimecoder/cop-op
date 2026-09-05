from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import models
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDay
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.models import User
from catalog.models import ServiceCategory, Service
from workers.models import (WorkerProfile, WorkerCategoryChangeRequest, WorkerServiceOffering,
                             Society, Federation, FederationJoinRequest, SocietyInvite)
from bookings.models import Booking, Complaint, BulkServiceRequest
from payments.models import Payment
from reviews.models import Review


def is_federation_admin(user):
    return user.is_authenticated and (user.role == User.Role.FEDERATION or user.is_superuser)


def is_platform_admin(user):
    """The true Admin persona — the ONLY one who can create Federations,
    verify worker skills/certificates, and ban/rename/delete/promote
    Federations & Societies. Distinct from `is_federation_admin`, which
    is about managing ONE already-created federation."""
    return user.is_authenticated and user.is_platform_admin


def is_society_operator(user):
    return user.is_authenticated and (user.role == User.Role.SOCIETY or user.is_superuser)


def is_staff_role(user):
    return user.is_authenticated and (
        user.role in [User.Role.FEDERATION, User.Role.SOCIETY, User.Role.SUPPORT,
                      User.Role.FINANCE, User.Role.WELFARE, User.Role.PLATFORM_ADMIN]
        or user.is_superuser
    )


@login_required
@user_passes_test(is_society_operator, login_url='core:home')
def send_society_invite(request):
    """Allows a society operator to invite a verified worker by phone number."""
    managed_society = getattr(request.user, 'managed_society', None)
    if not managed_society:
        messages.error(request, "You do not manage a society.")
        return redirect('dashboard:society_dashboard')

    if request.method == 'POST':
        phone_number = request.POST.get('phone_number', '').strip()
        if not phone_number:
            messages.error(request, "Please enter a phone number.")
            return redirect('dashboard:society_dashboard')

        # Check if a pending invite already exists
        if SocietyInvite.objects.filter(society=managed_society, phone_number=phone_number, status=SocietyInvite.Status.PENDING).exists():
            messages.info(request, "An invitation has already been sent to this number and is pending.")
            return redirect('dashboard:society_dashboard')

        SocietyInvite.objects.create(
            society=managed_society,
            phone_number=phone_number,
            status=SocietyInvite.Status.PENDING
        )
        messages.success(request, f"Invitation sent to {phone_number}.")
        return redirect('dashboard:society_dashboard')

    return redirect('dashboard:society_dashboard')


@login_required
@user_passes_test(is_federation_admin, login_url='core:home')
def federation_dashboard(request):
    """Federation dashboard with worker deployment and income graphs.
    Also includes filter for booked workers by society."""
    own_federation = getattr(request.user, 'managed_federation', None)
    if not own_federation:
        messages.error(request, "You don't manage a federation.")
        return redirect('dashboard:overview')

    # Filters
    society_id = request.GET.get('society_id')
    status_filter = request.GET.get('status')

    workers_qs = WorkerProfile.objects.filter(society__federation=own_federation).select_related('user', 'society')
    if society_id:
        workers_qs = workers_qs.filter(society_id=society_id)

    # Filter for "booked" workers (those with an active booking today)
    today = timezone.localdate()
    booked_workers = WorkerProfile.objects.filter(
        society__federation=own_federation,
        bookings__scheduled_date=today,
        bookings__status__in=Booking.ACTIVE_STATUSES
    ).distinct().select_related('user', 'society')

    if society_id:
        booked_workers = booked_workers.filter(society_id=society_id)

    if status_filter:
        booked_workers = booked_workers.filter(bookings__status=status_filter)

    # Graph Data: Deployed Workers (past 30 days)
    deployment_data = (
        Booking.objects.filter(worker__society__federation=own_federation, status__in=Booking.STATUS_FLOW)
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    # Graph Data: Income (past 30 days)
    income_data = (
        Payment.objects.filter(booking__worker__society__federation=own_federation, status=Payment.Status.SUCCESS)
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )

    return render(request, 'dashboard/federation_dashboard.html', {
        'federation': own_federation,
        'booked_workers': booked_workers,
        'societies': own_federation.societies.all(),
        'deployment_data': deployment_data,
        'income_data': income_data,
    })


@login_required
@user_passes_test(is_society_operator, login_url='core:home')
def society_dashboard(request):
    """Society dashboard with worker deployment and income graphs."""
    own_society = getattr(request.user, 'managed_society', None)
    if not own_society:
        messages.error(request, "You don't manage a society.")
        return redirect('dashboard:overview')

    # Filter for "booked" workers today
    today = timezone.localdate()
    status_filter = request.GET.get('status')
    booked_workers = WorkerProfile.objects.filter(
        society=own_society,
        bookings__scheduled_date=today,
        bookings__status__in=Booking.ACTIVE_STATUSES
    ).distinct().select_related('user')

    if status_filter:
        booked_workers = booked_workers.filter(bookings__status=status_filter)

    # Graph Data: Deployed Workers (past 30 days)
    deployment_data = (
        Booking.objects.filter(worker=own_society.workers.all(), status__in=Booking.STATUS_FLOW)
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    # Graph Data: Income (past 30 days)
    income_data = (
        Payment.objects.filter(booking__worker__society=own_society, status=Payment.Status.SUCCESS)
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )

    return render(request, 'dashboard/society_dashboard.html', {
        'society': own_society,
        'booked_workers': booked_workers,
        'deployment_data': deployment_data,
        'income_data': income_data,
    })

@login_required
@user_passes_test(is_staff_role, login_url='core:home')
def overview(request):
    """Role-aware dashboard landing page (FR-003 Role-Based Access)."""
    user = request.user

    # Determine dynamic dashboard title
    if is_platform_admin(user):
        dashboard_title = "Dashboard Admin"
    elif is_federation_owner(user):
        fed = getattr(user, 'managed_federation', None)
        dashboard_title = f"Dashboard {fed.name if fed else 'Federation'}"
    elif is_society_operator(user):
        soc = getattr(user, 'managed_society', None)
        dashboard_title = f"Dashboard {soc.name if soc else 'Society'}"
    else:
        dashboard_title = "Dashboard Overview"

    # Role-aware Statistics
    # Default global counts for Platform Admin
    total_bookings = Booking.objects.count()
    total_workers = WorkerProfile.objects.count()
    total_customers = User.objects.filter(role=User.Role.CUSTOMER).count()
    open_complaints = Complaint.objects.filter(status=Complaint.Status.OPEN).count()

    if not is_platform_admin(user):
        own_federation = getattr(user, 'managed_federation', None)
        own_society = getattr(user, 'managed_society', None)

        if own_federation:
            total_bookings = Booking.objects.filter(worker__society__federation=own_federation).count()
            total_workers = WorkerProfile.objects.filter(society__federation=own_federation).count()
            total_customers = User.objects.filter(
                role=User.Role.CUSTOMER,
                bookings__worker__society__federation=own_federation
            ).distinct().count()
            open_complaints = Complaint.objects.filter(
                status=Complaint.Status.OPEN,
                booking__worker__society__federation=own_federation
            ).count()
        elif own_society:
            total_bookings = Booking.objects.filter(worker__society=own_society).count()
            total_workers = WorkerProfile.objects.filter(society=own_society).count()
            total_customers = User.objects.filter(
                role=User.Role.CUSTOMER,
                bookings__worker__society=own_society
            ).distinct().count()
            open_complaints = Complaint.objects.filter(
                status=Complaint.Status.OPEN,
                booking__worker__society=own_society
            ).count()
        else:
            total_bookings = total_workers = total_customers = open_complaints = 0

    context = {
        'dashboard_title': dashboard_title,
        'total_bookings': total_bookings,
        'total_workers': total_workers,
        'total_customers': total_customers,
        'pending_verifications': WorkerProfile.objects.filter(
            verification_status=WorkerProfile.VerificationStatus.UNDER_REVIEW).count(),
        'pending_category_requests': WorkerCategoryChangeRequest.objects.filter(
            status=WorkerCategoryChangeRequest.Status.PENDING).count(),
        'open_complaints': open_complaints,
        'total_categories': ServiceCategory.objects.count(),
        'is_federation_admin': is_federation_admin(request.user),
        'is_society_operator': is_society_operator(request.user),
        'is_platform_admin': is_platform_admin(request.user),
        'is_federation_owner': is_federation_owner(request.user),
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
@user_passes_test(is_platform_admin, login_url='core:home')
def worker_verification_queue(request):
    """Skill/certificate verification is Admin-only (Section 4.10) — not
    a society operator's job. This is the identity/skill/document check;
    once verified here, a worker becomes available for any society's
    head to CLAIM (see claim_worker below), separately."""
    workers = WorkerProfile.objects.filter(
        verification_status__in=[WorkerProfile.VerificationStatus.PENDING,
                                  WorkerProfile.VerificationStatus.UNDER_REVIEW]
    ).select_related('user', 'society')
    return render(request, 'dashboard/worker_verification_queue.html', {'workers': workers})


@login_required
@user_passes_test(is_platform_admin, login_url='core:home')
def verify_worker(request, worker_id):
    """Admin-only skill/certificate verification decision. This does NOT
    assign a society — that's a separate step a society head takes
    afterwards (claim_worker), from the pool of admin-verified workers."""
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    if request.method == 'POST':
        decision = request.POST.get('decision')
        worker.verification_officer = request.user.get_full_name() or request.user.phone_number
        worker.verification_date = timezone.now().date()
        if decision == 'approve':
            worker.verification_status = WorkerProfile.VerificationStatus.VERIFIED
            messages.success(request, f"{worker.user.get_full_name()} verified. "
                                       f"They can now be claimed by any cooperative society.")
        else:
            worker.verification_status = WorkerProfile.VerificationStatus.REJECTED
            messages.warning(request, f"{worker.user.get_full_name()} rejected.")
        worker.save()
    return redirect('dashboard:worker_verification_queue')


@login_required
@user_passes_test(is_society_operator, login_url='core:home')
def claim_workers_queue(request):
    """Society-head side: pick admin-verified, still-unclaimed workers
    to bring into your own society. This is what actually makes a
    worker a member of a specific society — never self-selected by the
    worker, and never done at the same moment as skill verification."""
    managed_society = getattr(request.user, 'managed_society', None)
    if not managed_society and not request.user.is_superuser:
        messages.warning(request, "You don't have a cooperative society assigned to you yet. "
                                   "Ask an Admin to appoint you as a society head first.")
        return render(request, 'dashboard/claim_workers_queue.html', {'workers': [], 'managed_society': None})

    available_workers = WorkerProfile.objects.filter(
        verification_status=WorkerProfile.VerificationStatus.VERIFIED, society__isnull=True
    ).select_related('user')
    return render(request, 'dashboard/claim_workers_queue.html', {
        'workers': available_workers, 'managed_society': managed_society,
    })


@login_required
@user_passes_test(is_society_operator, login_url='core:home')
def claim_worker(request, worker_id):
    managed_society = getattr(request.user, 'managed_society', None)
    if not managed_society:
        messages.error(request, "You need a society assigned to you before you can claim workers.")
        return redirect('dashboard:claim_workers_queue')

    worker = get_object_or_404(WorkerProfile, id=worker_id,
                                verification_status=WorkerProfile.VerificationStatus.VERIFIED, society__isnull=True)
    if request.method == 'POST':
        worker.society = managed_society
        worker.save(update_fields=['society'])
        messages.success(request, f"{worker.user.get_full_name()} added to {managed_society.name}.")
    return redirect('dashboard:claim_workers_queue')


@login_required
@user_passes_test(is_federation_admin, login_url='core:home')
def category_change_queue(request):
    """Federation-admin approval queue for worker category-change requests.
    Approving a request replaces the worker's categories with the
    requested set and auto-creates service offerings for every service in
    the newly-approved categories, so the worker immediately shows up in
    customer searches for them."""
    own_federation = getattr(request.user, 'managed_federation', None)

    requests_qs = WorkerCategoryChangeRequest.objects.filter(
        status=WorkerCategoryChangeRequest.Status.PENDING
    ).select_related('worker__user').prefetch_related('requested_categories')

    if not is_platform_admin(request.user):
        if own_federation:
            requests_qs = requests_qs.filter(worker__society__federation=own_federation)
        else:
            requests_qs = requests_qs.none()

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

    user = request.user
    if not is_platform_admin(user):
        own_federation = getattr(user, 'managed_federation', None)
        own_society = getattr(user, 'managed_society', None)

        if own_federation:
            complaints = complaints.filter(booking__worker__society__federation=own_federation)
        elif own_society:
            complaints = complaints.filter(booking__worker__society=own_society)
        else:
            complaints = complaints.none()

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
    user = request.user
    customers = (User.objects.filter(role=User.Role.CUSTOMER)
                 .annotate(booking_count=Count('bookings'))
                 .order_by('-date_joined'))

    if not is_platform_admin(user):
        own_federation = getattr(user, 'managed_federation', None)
        own_society = getattr(user, 'managed_society', None)

        if own_federation:
            customers = customers.filter(bookings__worker__society__federation=own_federation).distinct()
        elif own_society:
            customers = customers.filter(bookings__worker__society=own_society).distinct()
        else:
            customers = customers.none()

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
    user = request.user
    workers = (WorkerProfile.objects.select_related('user', 'society')
               .annotate(booking_count=Count('bookings'))
               .order_by('-created_at'))

    if not is_platform_admin(user):
        own_federation = getattr(user, 'managed_federation', None)
        own_society = getattr(user, 'managed_society', None)

        if own_federation:
            workers = workers.filter(society__federation=own_federation)
        elif own_society:
            workers = workers.filter(society=own_society)
        else:
            workers = workers.none()

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


@login_required
@user_passes_test(is_staff_role, login_url='core:home')
def society_workers_list(request, society_id):
    """List all workers associated with a specific society.
    Access is restricted to staff roles (Platform Admin, Federation Admin, Society Operator)."""
    society = get_object_or_404(Society, id=society_id)

    # If the user is a society operator, ensure they only see workers of their own society.
    if not is_platform_admin(request.user) and not is_federation_admin(request.user):
        managed_society = getattr(request.user, 'managed_society', None)
        if managed_society != society:
            messages.error(request, "You do not have permission to view workers of this society.")
            return redirect('dashboard:society_list')

    workers = (WorkerProfile.objects.filter(society=society)
                .select_related('user')
                .annotate(booking_count=Count('bookings'))
                .order_by('-created_at'))

    return render(request, 'dashboard/society_workers_list.html', {
        'society': society,
        'workers': workers,
    })

#   - Admin (is_platform_admin): creates an INDEPENDENT society
#     (federation=None) — it runs its own pricing/queries/work.
#   - A Federation's own admin_user (is_federation_owner): creates a
#     society automatically UNDER their own federation.
# Renaming, banning, deleting, and promoting a society/federation
# remain Admin-only actions (Section 9).
# ---------------------------------------------------------------------

def is_federation_owner(user):
    return user.is_authenticated and getattr(user, 'managed_federation', None) is not None


def _can_manage_societies(user):
    return is_platform_admin(user) or is_federation_owner(user)


@login_required
@user_passes_test(_can_manage_societies, login_url='core:home')
def society_list(request):
    own_federation = getattr(request.user, 'managed_federation', None)
    societies = (Society.objects
                 .select_related('operator', 'federation')
                 .annotate(worker_count=Count('workers'))
                 .order_by('name'))
    if own_federation and not is_platform_admin(request.user):
        # A federation's own admin only manages/sees ITS societies.
        societies = societies.filter(federation=own_federation)
    return render(request, 'dashboard/society_list.html', {
        'societies': societies, 'own_federation': own_federation,
        'is_admin': is_platform_admin(request.user),
        'all_federations': Federation.objects.filter(is_active=True) if is_platform_admin(request.user) else None,
    })


@login_required
@user_passes_test(_can_manage_societies, login_url='core:home')
def society_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        city = request.POST.get('city', 'Delhi').strip()
        registration_number = request.POST.get('registration_number', '').strip()
        own_federation = getattr(request.user, 'managed_federation', None)

        if not name:
            messages.error(request, "Society name is required.")
        else:
            if is_platform_admin(request.user):
                # Admin chooses: attach to a federation, or leave independent.
                federation_id = request.POST.get('federation_id') or None
                federation = Federation.objects.filter(id=federation_id).first() if federation_id else None
            else:
                # A federation's own admin can only create societies under themselves.
                federation = own_federation

            Society.objects.create(name=name, city=city, registration_number=registration_number,
                                    federation=federation)
            messages.success(request, f"Society '{name}' created"
                              + (f" under {federation.name}." if federation else " as an independent society.")
                              + " Now assign it a head.")
        return redirect('dashboard:society_list')
    return redirect('dashboard:society_list')


@login_required
@user_passes_test(_can_manage_societies, login_url='core:home')
def society_assign_operator(request, society_id):
    """Society heads can't self-register with role=society (that role
    is deliberately excluded from public sign-up for security). Instead,
    an Admin or that society's own federation appoints one here by
    phone number — the account is created if it doesn't exist yet, or
    promoted to role=society if it does (e.g. was previously a customer)."""
    society = get_object_or_404(Society, id=society_id)
    own_federation = getattr(request.user, 'managed_federation', None)
    if own_federation and not is_platform_admin(request.user) and society.federation_id != own_federation.id:
        messages.error(request, "You can only manage societies under your own federation.")
        return redirect('dashboard:society_list')

    if request.method == 'POST':
        phone_number = request.POST.get('phone_number', '').strip()
        if not phone_number:
            messages.error(request, "Enter a phone number to appoint as head.")
            return redirect('dashboard:society_list')

        operator, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={'username': phone_number, 'role': User.Role.SOCIETY}
        )
        if operator.role != User.Role.SOCIETY:
            operator.role = User.Role.SOCIETY
            operator.save(update_fields=['role'])

        # Free them from any other society they might have headed before.
        Society.objects.filter(operator=operator).exclude(id=society.id).update(operator=None)

        society.operator = operator
        society.save(update_fields=['operator'])
        label = operator.get_full_name() or operator.phone_number
        if created:
            messages.success(request, f"Created a new account for {phone_number} and appointed them head of {society.name}. They can log in via OTP as usual.")
        else:
            messages.success(request, f"{label} is now the head of {society.name}.")
    return redirect('dashboard:society_list')


@login_required
@user_passes_test(_can_manage_societies, login_url='core:home')
def society_remove_operator(request, society_id):
    society = get_object_or_404(Society, id=society_id)
    own_federation = getattr(request.user, 'managed_federation', None)
    if own_federation and not is_platform_admin(request.user) and society.federation_id != own_federation.id:
        messages.error(request, "You can only manage societies under your own federation.")
        return redirect('dashboard:society_list')
    if request.method == 'POST':
        society.operator = None
        society.save(update_fields=['operator'])
        messages.info(request, f"Head removed from {society.name}.")
    return redirect('dashboard:society_list')


@login_required
@user_passes_test(is_federation_admin, login_url='core:home')
def society_toggle_fieldwork(request, society_id):
    """Only the federation this society belongs to can toggle whether
    the society's head personally does fieldwork (Section 4.3). Not
    meaningful for independent societies — their head always works."""
    society = get_object_or_404(Society, id=society_id)
    own_federation = getattr(request.user, 'managed_federation', None)
    if not society.federation_id or (own_federation and society.federation_id != own_federation.id):
        messages.error(request, "This toggle only applies to societies under your federation.")
        return redirect('dashboard:society_list')
    if request.method == 'POST':
        society.head_performs_fieldwork = not society.head_performs_fieldwork
        society.save(update_fields=['head_performs_fieldwork'])
        messages.success(request, f"Updated for {society.name}.")
    return redirect('dashboard:society_list')


# ---------------------------------------------------------------------
# Admin-only governance: rename, ban (for a period), accept resignation,
# delete — for both Societies and Federations (Section 9).
# ---------------------------------------------------------------------

@login_required
@user_passes_test(_can_manage_societies, login_url='core:home')
def society_rename(request, society_id):
    society = get_object_or_404(Society, id=society_id)

    # Federation admins can only rename societies under their own federation.
    # Platform admins can rename any society.
    own_federation = getattr(request.user, 'managed_federation', None)
    if not is_platform_admin(request.user) and (not own_federation or society.federation_id != own_federation.id):
        messages.error(request, "You do not have permission to rename this society.")
        return redirect('dashboard:society_list')

    if request.method == 'POST':
        new_name = request.POST.get('name', '').strip()
        if new_name:
            society.name = new_name
            society.save(update_fields=['name'])
            messages.success(request, "Society renamed.")
    return redirect('dashboard:society_list')


@login_required
@user_passes_test(is_platform_admin, login_url='core:home')
def society_ban(request, society_id):
    society = get_object_or_404(Society, id=society_id)
    if request.method == 'POST':
        days = request.POST.get('days')
        society.is_banned = True
        society.ban_until = timezone.now() + timezone.timedelta(days=int(days)) if days else None
        society.save(update_fields=['is_banned', 'ban_until'])
        messages.warning(request, f"{society.name} banned" + (f" for {days} days." if days else " indefinitely."))
    return redirect('dashboard:society_list')


@login_required
@user_passes_test(is_platform_admin, login_url='core:home')
def society_unban(request, society_id):
    society = get_object_or_404(Society, id=society_id)
    if request.method == 'POST':
        society.is_banned = False
        society.ban_until = None
        society.save(update_fields=['is_banned', 'ban_until'])
        messages.success(request, f"{society.name} unbanned.")
    return redirect('dashboard:society_list')


@login_required
@user_passes_test(is_platform_admin, login_url='core:home')
def society_accept_resignation(request, society_id):
    society = get_object_or_404(Society, id=society_id, resignation_requested=True)
    if request.method == 'POST':
        society.resigned_at = timezone.now()
        society.is_active = False
        society.save(update_fields=['resigned_at', 'is_active'])
        messages.info(request, f"Resignation accepted for {society.name}.")
    return redirect('dashboard:society_list')


@login_required
@user_passes_test(is_platform_admin, login_url='core:home')
def society_delete(request, society_id):
    society = get_object_or_404(Society, id=society_id)
    if request.method == 'POST':
        name = society.name
        society.delete()
        messages.warning(request, f"{name} deleted permanently.")
    return redirect('dashboard:society_list')


@login_required
@user_passes_test(is_platform_admin, login_url='core:home')
def society_promote_to_federation(request, society_id):
    """Section 13 — Admin can promote an independent society into being
    its own federation (e.g. it has grown large enough to run
    sub-societies of its own)."""
    society = get_object_or_404(Society, id=society_id, federation__isnull=True)
    if request.method == 'POST':
        federation = Federation.objects.create(
            name=society.name, city=society.city, registration_number=society.registration_number,
            admin_user=society.operator,
        )
        messages.success(request, f"{society.name} promoted to a federation. "
                                   f"Its former head ({society.operator}) now administers the new federation — "
                                   f"appoint a new society head separately if needed.")
        # The society itself still exists as a society; if desired an
        # operator can create a new society under this new federation.
    return redirect('dashboard:society_list')


# ---------------------------------------------------------------------
# Federation management — Admin-only creation/governance, plus a
# federation's own admin_user can view/manage their one federation.
# ---------------------------------------------------------------------

@login_required
@user_passes_test(is_platform_admin, login_url='core:home')
def federation_list(request):
    federations = (Federation.objects
                   .select_related('admin_user')
                   .annotate(society_count=Count('societies'))
                   .order_by('name'))
    return render(request, 'dashboard/federation_list.html', {'federations': federations})


@login_required
@user_passes_test(is_platform_admin, login_url='core:home')
def federation_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        city = request.POST.get('city', 'Delhi').strip()
        registration_number = request.POST.get('registration_number', '').strip()
        commission = request.POST.get('commission_percent', '10').strip() or '10'
        if not name:
            messages.error(request, "Federation name is required.")
        else:
            Federation.objects.create(name=name, city=city, registration_number=registration_number,
                                       commission_percent=commission)
            messages.success(request, f"Federation '{name}' created. Now assign it an admin.")
    return redirect('dashboard:federation_list')


@login_required
@user_passes_test(is_platform_admin, login_url='core:home')
def federation_assign_admin(request, federation_id):
    federation = get_object_or_404(Federation, id=federation_id)
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number', '').strip()
        if not phone_number:
            messages.error(request, "Enter a phone number.")
            return redirect('dashboard:federation_list')
        admin_user, created = User.objects.get_or_create(
            phone_number=phone_number, defaults={'username': phone_number, 'role': User.Role.FEDERATION}
        )
        if admin_user.role != User.Role.FEDERATION:
            admin_user.role = User.Role.FEDERATION
            admin_user.save(update_fields=['role'])
        Federation.objects.filter(admin_user=admin_user).exclude(id=federation.id).update(admin_user=None)
        federation.admin_user = admin_user
        federation.save(update_fields=['admin_user'])
        messages.success(request, f"{admin_user.get_full_name() or admin_user.phone_number} now administers {federation.name}.")
    return redirect('dashboard:federation_list')


@login_required
@user_passes_test(is_platform_admin, login_url='core:home')
def federation_rename(request, federation_id):
    federation = get_object_or_404(Federation, id=federation_id)
    if request.method == 'POST':
        new_name = request.POST.get('name', '').strip()
        if new_name:
            federation.name = new_name
            federation.save(update_fields=['name'])
            messages.success(request, "Federation renamed.")
    return redirect('dashboard:federation_list')


@login_required
@user_passes_test(is_platform_admin, login_url='core:home')
def federation_ban(request, federation_id):
    federation = get_object_or_404(Federation, id=federation_id)
    if request.method == 'POST':
        days = request.POST.get('days')
        federation.is_banned = True
        federation.ban_until = timezone.now() + timezone.timedelta(days=int(days)) if days else None
        federation.save(update_fields=['is_banned', 'ban_until'])
        messages.warning(request, f"{federation.name} banned.")
    return redirect('dashboard:federation_list')


@login_required
@user_passes_test(is_platform_admin, login_url='core:home')
def federation_unban(request, federation_id):
    federation = get_object_or_404(Federation, id=federation_id)
    if request.method == 'POST':
        federation.is_banned = False
        federation.ban_until = None
        federation.save(update_fields=['is_banned', 'ban_until'])
        messages.success(request, f"{federation.name} unbanned.")
    return redirect('dashboard:federation_list')


@login_required
@user_passes_test(is_platform_admin, login_url='core:home')
def federation_delete(request, federation_id):
    federation = get_object_or_404(Federation, id=federation_id)
    if request.method == 'POST':
        name = federation.name
        # Societies under it become independent rather than orphaned/deleted.
        Society.objects.filter(federation=federation).update(federation=None)
        federation.delete()
        messages.warning(request, f"{name} deleted. Its societies are now independent.")
    return redirect('dashboard:federation_list')


@login_required
@user_passes_test(is_platform_admin, login_url='core:home')
def federation_set_commission(request, federation_id):
    federation = get_object_or_404(Federation, id=federation_id)
    if request.method == 'POST':
        federation.commission_percent = request.POST.get('commission_percent', federation.commission_percent)
        federation.save(update_fields=['commission_percent'])
        messages.success(request, f"Commission for {federation.name} updated.")
    return redirect('dashboard:federation_list')


# ---------------------------------------------------------------------
# Federation <-> independent-society join/invite flow (Section 4.2).
# Either side can initiate; the OTHER side must accept.
# ---------------------------------------------------------------------

@login_required
@user_passes_test(is_federation_admin, login_url='core:home')
def independent_societies_list(request):
    """A federation admin browses independent societies to invite."""
    societies = Society.objects.filter(federation__isnull=True, is_active=True)
    own_federation = getattr(request.user, 'managed_federation', None)
    pending_invites = set()
    if own_federation:
        pending_invites = set(FederationJoinRequest.objects.filter(
            federation=own_federation, status=FederationJoinRequest.Status.PENDING
        ).values_list('society_id', flat=True))
    return render(request, 'dashboard/independent_societies_list.html', {
        'societies': societies, 'own_federation': own_federation, 'pending_invites': pending_invites,
    })


@login_required
@user_passes_test(is_federation_admin, login_url='core:home')
def invite_society(request, society_id):
    own_federation = getattr(request.user, 'managed_federation', None)
    if not own_federation:
        messages.error(request, "You need your own federation to invite societies.")
        return redirect('dashboard:independent_societies_list')
    society = get_object_or_404(Society, id=society_id, federation__isnull=True)
    if request.method == 'POST':
        FederationJoinRequest.objects.create(
            society=society, federation=own_federation,
            initiated_by=FederationJoinRequest.InitiatedBy.FEDERATION,
        )
        messages.success(request, f"Invited {society.name} to join {own_federation.name}.")
    return redirect('dashboard:independent_societies_list')


@login_required
@user_passes_test(is_society_operator, login_url='core:home')
def federation_directory(request):
    """A society head browses federations to request joining."""
    federations = Federation.objects.filter(is_active=True)
    own_society = getattr(request.user, 'managed_society', None)
    pending_requests = set()
    if own_society:
        pending_requests = set(FederationJoinRequest.objects.filter(
            society=own_society, status=FederationJoinRequest.Status.PENDING
        ).values_list('federation_id', flat=True))
    return render(request, 'dashboard/federation_directory.html', {
        'federations': federations, 'own_society': own_society, 'pending_requests': pending_requests,
    })


@login_required
@user_passes_test(is_society_operator, login_url='core:home')
def request_join_federation(request, federation_id):
    own_society = getattr(request.user, 'managed_society', None)
    if not own_society or not own_society.is_independent:
        messages.error(request, "Only an independent society's head can request to join a federation.")
        return redirect('dashboard:federation_directory')
    federation = get_object_or_404(Federation, id=federation_id, is_active=True)
    if request.method == 'POST':
        FederationJoinRequest.objects.create(
            society=own_society, federation=federation,
            initiated_by=FederationJoinRequest.InitiatedBy.SOCIETY,
        )
        messages.success(request, f"Requested to join {federation.name}. Awaiting their acceptance.")
    return redirect('dashboard:federation_directory')


@login_required
def join_requests_queue(request):
    """Shows the requests THIS user needs to act on: a federation admin
    sees society-initiated requests to join them; a society head sees
    federation-initiated invitations to their society."""
    own_federation = getattr(request.user, 'managed_federation', None)
    own_society = getattr(request.user, 'managed_society', None)
    incoming = FederationJoinRequest.objects.none()
    if own_federation:
        incoming = FederationJoinRequest.objects.filter(
            federation=own_federation, initiated_by=FederationJoinRequest.InitiatedBy.SOCIETY,
            status=FederationJoinRequest.Status.PENDING)
    elif own_society:
        incoming = FederationJoinRequest.objects.filter(
            society=own_society, initiated_by=FederationJoinRequest.InitiatedBy.FEDERATION,
            status=FederationJoinRequest.Status.PENDING)
    else:
        messages.info(request, "You don't manage a federation or society yet.")
    return render(request, 'dashboard/join_requests_queue.html', {'incoming': incoming})


@login_required
def decide_join_request(request, request_id):
    join_request = get_object_or_404(FederationJoinRequest, id=request_id, status=FederationJoinRequest.Status.PENDING)
    own_federation = getattr(request.user, 'managed_federation', None)
    own_society = getattr(request.user, 'managed_society', None)

    # Only the RECEIVING side may decide.
    can_decide = (
        (join_request.initiated_by == FederationJoinRequest.InitiatedBy.SOCIETY
         and own_federation and join_request.federation_id == own_federation.id)
        or
        (join_request.initiated_by == FederationJoinRequest.InitiatedBy.FEDERATION
         and own_society and join_request.society_id == own_society.id)
    )
    if not can_decide:
        messages.error(request, "You cannot act on this request.")
        return redirect('dashboard:join_requests_queue')

    if request.method == 'POST':
        decision = request.POST.get('decision')
        join_request.responded_at = timezone.now()
        if decision == 'accept':
            join_request.status = FederationJoinRequest.Status.ACCEPTED
            join_request.society.federation = join_request.federation
            join_request.society.save(update_fields=['federation'])
            messages.success(request, f"{join_request.society.name} is now part of {join_request.federation.name}. "
                                       f"It will follow the federation's pricing and policies.")
        else:
            join_request.status = FederationJoinRequest.Status.REJECTED
            messages.info(request, "Request rejected.")
        join_request.save()
    return redirect('dashboard:join_requests_queue')


@login_required
def manage_custom_pricing(request):
    """Allows independent society heads or federation admins to override global prices.
    Independent societies can set their own; federations set prices for all their societies."""

    # Check if user is a society operator of an independent society
    own_society = getattr(request.user, 'managed_society', None)
    if own_society and own_society.is_independent:
        pricing_obj, pricing_type = getattr(own_society, 'custom_pricing', None), 'society'
        if not pricing_obj:
            from workers.models import SocietyPricing
            pricing_obj = SocietyPricing.objects.get_or_create(society=own_society)[0]
    else:
        # Check if user is a federation admin
        own_federation = getattr(request.user, 'managed_federation', None)
        if own_federation:
            pricing_obj, pricing_type = getattr(own_federation, 'custom_pricing', None), 'federation'
            if not pricing_obj:
                from workers.models import FederationPricing
                pricing_obj = FederationPricing.objects.get_or_create(federation=own_federation)[0]
        else:
            messages.error(request, "You do not have authority to manage custom pricing.")
            return redirect('dashboard:overview')

    categories = ServiceCategory.objects.all()
    services = Service.objects.all()

    if request.method == 'POST':
        # Handle category override
        cat_id = request.POST.get('category_id')
        cat_val = request.POST.get('category_value')
        if cat_id and cat_val:
            # Need to create a copy of the dict to trigger save in some Django versions
            overrides = dict(pricing_obj.category_overrides)
            overrides[str(cat_id)] = float(cat_val)
            pricing_obj.category_overrides = overrides
            pricing_obj.save()
            messages.success(request, "Category visit charge updated.")

        # Handle service override
        ser_id = request.POST.get('service_id')
        ser_val = request.POST.get('service_value')
        if ser_id and ser_val:
            overrides = dict(pricing_obj.service_overrides)
            overrides[str(ser_id)] = float(ser_val)
            pricing_obj.service_overrides = overrides
            pricing_obj.save()
            messages.success(request, "Service labour charge updated.")

        return redirect('dashboard:manage_custom_pricing')

    return render(request, 'dashboard/custom_pricing.html', {
        'pricing_obj': pricing_obj,
        'pricing_type': pricing_type,
        'categories': categories,
        'services': services,
    })
