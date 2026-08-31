from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db import transaction

from catalog.models import Service, ServiceCategory
from workers.models import WorkerProfile, WorkerBlockedDate
from payments.models import Payment, Invoice
from payments import razorpay_client
from reviews.models import Review
from .models import Booking, Complaint, Project
from .forms import BookingForm, ComplaintForm


def _worker_occupied_dates(worker):
    """Dates the worker cannot be booked on: manually blocked days, plus
    any day already carrying an active (non-cancelled/rejected) booking.
    Kept simple for the MVP — one confirmed job per worker per day."""
    blocked = set(worker.blocked_dates.values_list('date', flat=True))
    booked = set(
        Booking.objects.filter(worker=worker, status__in=Booking.ACTIVE_STATUSES)
        .values_list('scheduled_date', flat=True)
    )
    return blocked | booked


@login_required
def project_detail(request, project_id):
    """Project Dashboard (SIH Phase 1B).
    Displays all atomic bookings associated with a bulk project.
    """
    project = get_object_or_404(Project, id=project_id)
    if project.customer != request.user and not request.user.is_staff:
        messages.error(request, "You do not have access to this project.")
        return redirect('core:home')

    bookings = project.bookings.select_related('service', 'worker__user').order_by('service__name', 'id')

    # Aggregate project stats
    total_bookings = bookings.count()
    completed_bookings = bookings.filter(status__in=[Booking.Status.PAYMENT_SETTLED, Booking.Status.RATED]).count()
    progress = round((completed_bookings / total_bookings * 100), 1) if total_bookings > 0 else 0

    return render(request, 'bookings/project_detail.html', {
        'project': project,
        'bookings': bookings,
        'progress': progress,
        'total_bookings': total_bookings,
    })


def guided_booking(request):
    """Guided booking wizard (SIH Phase 1A/1B).
    Collects booking details and creates either a single Booking or a Project with atomic Bookings.
    """
    category_slug = request.GET.get('category')

    if category_slug:
        category = get_object_or_404(ServiceCategory, slug=category_slug)
        request.session['booking_wizard'] = {
            'category_slug': category_slug,
            'category_name': category.name,
            'step': 1
        }
        services = category.services.filter(is_active=True)
        return render(request, 'bookings/wizard_step_1.html', {
            'category': category,
            'services': services,
            'step': 1,
            'data': request.session['booking_wizard']
        })

    wizard_data = request.session.get('booking_wizard')
    if not wizard_data:
        return redirect('core:home')

    step = int(wizard_data.get('step', 1))
    data = wizard_data.copy()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'prev' and step > 1:
            step -= 1
            data['step'] = step
            request.session['booking_wizard'] = data
            return redirect('bookings:guided_booking')

        if action == 'next':
            current_form_data = request.POST.copy()
            for key, value in current_form_data.items():
                if key != 'action':
                    data[key] = value

            step += 1

            if step > 6:
                service_id = data.get('service_id')
                service = get_object_or_404(Service, id=service_id)
                workers_qty = int(data.get('workers_required', 1))

                try:
                    with transaction.atomic():
                        project = None
                        # Create Project if bulk
                        if workers_qty > 1:
                            project = Project.objects.create(
                                customer=request.user,
                                title=f"Bulk {service.name} Booking",
                                description=data.get('instructions', ''),
                                status='requested'
                            )

                        # Create atomic bookings (1 per worker)
                        last_created_booking = None
                        for _ in range(workers_qty):
                            last_created_booking = Booking.objects.create(
                                project=project,
                                customer=request.user,
                                service=service,
                                address=data.get('address', request.user.address),
                                scheduled_date=data.get('scheduled_date'),
                                scheduled_time=data.get('scheduled_time'),
                                instructions=data.get('instructions', ''),
                                is_emergency=data.get('is_emergency') == 'true',
                                visit_charge=service.visit_charge,
                                labour_charge=service.fixed_labour_charge if not service.is_hourly else service.hourly_rate,
                                workers_required=1, # Atomic: each booking is for 1 worker
                                duration_days=int(data.get('duration_days', 1)),
                                status=Booking.Status.REQUESTED,
                            )

                        del request.session['booking_wizard']

                        if project:
                            messages.success(request, f"Bulk request for {workers_qty} workers submitted successfully.")
                            return redirect('bookings:project_detail', project_id=project.id)
                        else:
                            messages.success(request, "Booking request submitted successfully.")
                            return redirect('bookings:booking_detail', booking_id=last_created_booking.id)

                except Exception as e:
                    messages.error(request, f"An error occurred while creating your booking: {e}")
                    return redirect('bookings:guided_booking')

            data['step'] = step
            request.session['booking_wizard'] = data
            return redirect('bookings:guided_booking')

    step_templates = {
        1: 'bookings/wizard_step_1.html',
        2: 'bookings/wizard_step_2.html',
        3: 'bookings/wizard_step_3.html',
        4: 'bookings/wizard_step_4.html',
        5: 'bookings/wizard_step_5.html',
        6: 'bookings/wizard_step_6.html',
    }

    context = {'step': step, 'data': data}
    if step == 1:
        cat_slug = data.get('category_slug')
        category = get_object_or_404(ServiceCategory, slug=cat_slug)
        context['category'] = category
        context['services'] = category.services.filter(is_active=True)

    return render(request, step_templates.get(step, 'bookings/wizard_step_2.html'), context)


def worker_availability_json(request, worker_id):
    """JSON endpoint the booking-date picker calls to grey out dates the
    worker is already committed on (FR — worker availability check)."""
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    dates = sorted(_worker_occupied_dates(worker))
    return JsonResponse({'blocked_dates': [d.isoformat() for d in dates]})


@login_required
def create_booking(request, service_id, worker_id):
    """UC-001 Book Fixed Service. Requires login (session-based)."""
    service = get_object_or_404(Service, id=service_id, is_active=True)
    worker = get_object_or_404(WorkerProfile, id=worker_id, verification_status=WorkerProfile.VerificationStatus.VERIFIED)
    occupied_dates = _worker_occupied_dates(worker)

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            chosen_date = form.cleaned_data['scheduled_date']
            if chosen_date in occupied_dates:
                messages.error(request, "This worker is already booked on the selected date.")
            elif chosen_date < timezone.localdate():
                messages.error(request, "Please choose a current or future date.")
            else:
                booking = form.save(commit=False)
                booking.customer = request.user
                booking.service = service
                booking.worker = worker
                booking.visit_charge = service.visit_charge
                booking.workers_required = form.cleaned_data.get('workers_required') or 1
                booking.duration_days = form.cleaned_data.get('duration_days') or 1
                if service.is_hourly:
                    booking.labour_charge = service.hourly_rate
                    booking.hours_booked = form.cleaned_data.get('hours_booked') or service.min_hours
                else:
                    booking.labour_charge = service.fixed_labour_charge
                    booking.hours_booked = 1
                booking.status = Booking.Status.ASSIGNED
                booking.save()
                messages.success(request, "Booking created. Waiting for worker acceptance.")
                return redirect('bookings:booking_detail', booking_id=booking.id)
        else:
            messages.error(request, "Please correct the errors below and try again.")
    else:
        initial = {'city': request.user.city, 'address': request.user.address,
                   'hours_booked': service.min_hours}
        form = BookingForm(initial=initial)

    return render(request, 'bookings/create_booking.html', {
        'form': form, 'service': service, 'worker': worker,
        'total': service.total_charge,
        'occupied_dates_json': sorted(d.isoformat() for d in occupied_dates),
    })


@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    is_customer = booking.customer == request.user
    is_worker = booking.worker and booking.worker.user == request.user
    if not (is_customer or is_worker or request.user.is_staff):
        messages.error(request, "You do not have access to this booking.")
        return redirect('core:home')
    payment = getattr(booking, 'payment', None)
    review = getattr(booking, 'review', None)
    razorpay_ready = razorpay_client.is_configured()

    status_steps = []
    if booking.status not in (Booking.Status.CANCELLED, Booking.Status.REJECTED):
        try:
            current_idx = Booking.STATUS_FLOW.index(booking.status)
        except ValueError:
            current_idx = -1
        for idx, status_key in enumerate(Booking.STATUS_FLOW):
            status_steps.append({
                'key': status_key,
                'label': Booking.Status(status_key).label,
                'done': idx < current_idx,
                'current': idx == current_idx,
            })

    return render(request, 'bookings/booking_detail.html', {
        'booking': booking, 'payment': payment, 'review': review,
        'is_customer': is_customer, 'is_worker': is_worker,
        'status_steps': status_steps,
        'razorpay_ready': razorpay_ready,
    })


def booking_status_json(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if not request.user.is_authenticated or not (
        booking.customer_id == request.user.id
        or (booking.worker and booking.worker.user_id == request.user.id)
        or request.user.is_staff
    ):
        return HttpResponseForbidden()
    return JsonResponse({
        'status': booking.status,
        'status_display': booking.get_status_display(),
        'progress_percent': booking.progress_percent(),
    })


@login_required
@require_POST
def worker_action(request, booking_id, action):
    booking = get_object_or_404(Booking, id=booking_id)
    if not booking.worker or booking.worker.user != request.user:
        return HttpResponseForbidden("Only the assigned worker can update this booking.")

    action_to_status = {
        'accept': (Booking.Status.ASSIGNED, Booking.Status.ACCEPTED),
        'start_arriving': (Booking.Status.ACCEPTED, Booking.Status.WORKER_ARRIVING),
        'mark_arrived': (Booking.Status.WORKER_ARRIVING, Booking.Status.ARRIVED),
        'start_work': (Booking.Status.ARRIVED, Booking.Status.WORK_STARTED),
        'complete_work': (Booking.Status.WORK_STARTED, Booking.Status.WORK_COMPLETED),
    }
    if action == 'reject' and booking.status == Booking.Status.ASSIGNED:
        booking.status = Booking.Status.REJECTED
        booking.save(update_fields=['status', 'updated_at'])
        messages.info(request, "Booking rejected.")
        return redirect('bookings:booking_detail', booking_id=booking.id)

    if action not in action_to_status:
        messages.error(request, "Unknown action.")
        return redirect('bookings:booking_detail', booking_id=booking.id)

    required_status, new_status = action_to_status[action]
    if booking.status != required_status:
        messages.error(request, "This booking has already moved on — refresh the page.")
        return redirect('bookings:booking_detail', booking_id=booking.id)

    booking.status = new_status
    booking.save(update_fields=['status', 'updated_at'])
    messages.success(request, f"Status updated: {booking.get_status_display()}")
    return redirect('bookings:booking_detail', booking_id=booking.id)


@login_required
@require_POST
def confirm_completion(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    if booking.status != Booking.Status.WORK_COMPLETED:
        messages.error(request, "This booking isn't awaiting confirmation.")
        return redirect('bookings:booking_detail', booking_id=booking.id)
    booking.status = Booking.Status.CUSTOMER_CONFIRMED
    booking.save(update_fields=['status', 'updated_at'])
    messages.success(request, "Thanks for confirming — you can now pay for this booking.")
    return redirect('bookings:booking_detail', booking_id=booking.id)


@login_required
def my_bookings(request):
    # Single bookings (no project)
    single_bookings = Booking.objects.filter(customer=request.user, project__isnull=True).select_related('service', 'worker')
    # Bulk projects
    projects = Project.objects.filter(customer=request.user).order_by('-created_at')

    return render(request, 'bookings/my_bookings.html', {
        'bookings': single_bookings,
        'projects': projects,
    })


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    if request.method == 'POST':
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=['status'])
        messages.info(request, "Booking cancelled.")
    return redirect('bookings:my_bookings')


@login_required
def make_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    if hasattr(booking, 'payment'):
        return redirect('bookings:booking_detail', booking_id=booking.id)

    razorpay_ready = razorpay_client.is_configured()

    if request.method == 'POST':
        method = request.POST.get('method', Payment.Method.UPI)
        amount = booking.total_amount

        if razorpay_ready:
            order = razorpay_client.create_order(amount, receipt=f"booking-{booking.id}")
            if order:
                payment, _created = Payment.objects.get_or_create(
                    booking=booking,
                    defaults={'method': method, 'amount': amount, 'status': Payment.Status.PENDING,
                              'razorpay_order_id': order['id']}
                )
                return render(request, 'bookings/razorpay_checkout.html', {
                    'booking': booking, 'payment': payment, 'order': order,
                    'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                })
            messages.warning(request, "Could not reach Razorpay right now — falling back to a simulated payment.")

        payment = Payment(booking=booking, method=method, amount=amount, status=Payment.Status.SUCCESS,
                           is_simulated=True)
        payment.compute_settlement()
        payment.settled_at = timezone.now()
        payment.save()
        Invoice.objects.create(payment=payment, invoice_number=Invoice.generate_number(booking.id))
        booking.status = Booking.Status.PAYMENT_SETTLED
        booking.save(update_fields=['status'])
        messages.success(request, "Payment successful (simulated — Razorpay test keys not configured). Invoice generated.")
        return redirect('bookings:booking_detail', booking_id=booking.id)

    return render(request, 'bookings/make_payment.html', {'booking': booking, 'razorpay_ready': razorpay_ready})


@login_required
@require_POST
def razorpay_callback(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    payment = get_object_or_404(Payment, booking=booking)

    order_id = request.POST.get('razorpay_order_id')
    payment_id = request.POST.get('razorpay_payment_id')
    signature = request.POST.get('razorpay_signature')

    if razorpay_client.verify_payment_signature(order_id, payment_id, signature):
        payment.razorpay_payment_id = payment_id
        payment.status = Payment.Status.SUCCESS
        payment.compute_settlement()
        payment.settled_at = timezone.now()
        payment.save()
        Invoice.objects.get_or_create(payment=payment, defaults={
            'invoice_number': Invoice.generate_number(booking.id)})
        booking.status = Booking.Status.PAYMENT_SETTLED
        booking.save(update_fields=['status'])
        messages.success(request, "Payment verified successfully via Razorpay (test mode).")
    else:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=['status'])
        messages.error(request, "Payment verification failed. Please try again.")
    return redirect('bookings:booking_detail', booking_id=booking.id)


@login_required
def submit_review(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    if hasattr(booking, 'review'):
        return redirect('bookings:booking_detail', booking_id=booking.id)

    if request.method == 'POST':
        rating = int(request.POST.get('rating', 5))
        comment = request.POST.get('comment', '')
        Review.objects.create(booking=booking, customer=request.user, worker=booking.worker,
                               rating=rating, comment=comment)
        worker = booking.worker
        all_ratings = worker.reviews.all()
        if all_ratings.exists():
            worker.average_rating = round(sum(r.rating for r in all_ratings) / all_ratings.count(), 2)
        worker.completed_jobs += 1
        worker.save(update_fields=['average_rating', 'completed_jobs'])
        booking.status = Booking.Status.RATED
        booking.save(update_fields=['status'])
        messages.success(request, "Thank you for rating this service.")
        return redirect('bookings:booking_detail', booking_id=booking.id)

    return render(request, 'bookings/submit_review.html', {'booking': booking})


@login_required
def file_complaint(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.raised_by = request.user
            complaint.save()
            messages.success(request, "Complaint registered. Our support team will review it shortly.")
            return redirect('bookings:booking_detail', booking_id=booking.id)
    else:
        form = ComplaintForm()
    return render(request, 'bookings/file_complaint.html', {'form': form, 'booking': booking})
