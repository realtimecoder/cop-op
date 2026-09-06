from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import translation
from django.utils.translation import gettext as _
from django.conf import settings

from .forms import PhoneForm, OTPVerifyForm, RegistrationForm, ProfileUpdateForm
from .models import OTPRequest
from workers.geo import geocode_address
from workers.models import Society, WorkerProfile

User = get_user_model()


def _apply_language(request, response, user):
    """Activate and persist the user's preferred language via the standard
    Django language cookie (Django 6.x LocaleMiddleware reads the cookie,
    not the session)."""
    lang = user.preferred_language or 'en'
    translation.activate(lang)
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang)
    return response


def _geocode_and_save_location(user):
    """Converts the user's typed address/city/pincode into lat/lng via
    Google's Geocoding API and saves it — for BOTH customers and workers,
    since they share the same User model fields. This is what makes
    "nearest worker" actually work from a plain typed address instead of
    only from the browser's GPS button: as soon as either side saves a
    profile with an address, their coordinates are on file.

    Silently does nothing if no Google Maps key is configured or the
    address can't be resolved — never blocks the profile save itself."""
    if not user.address:
        return
    coords = geocode_address(user.address, user.city, user.pincode)
    if coords:
        user.latitude, user.longitude = coords
        user.save(update_fields=['latitude', 'longitude'])


def login_request(request):
    """Step 1: select role and enter phone number, receive OTP (FR-002)."""
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = PhoneForm(request.POST)
        login_role = request.POST.get('login_role', 'customer')
        if form.is_valid():
            phone = form.cleaned_data['phone_number']
            otp = OTPRequest.generate(phone, purpose='login')
            request.session['otp_phone'] = phone
            request.session['otp_id'] = otp.id
            request.session['login_role'] = login_role
            # Demo-mode: show OTP directly since no SMS gateway is configured.
            messages.info(request, _("Demo OTP for %(phone)s is %(code)s (valid 10 minutes).")
                          % {'phone': phone, 'code': otp.code})
            return redirect('accounts:verify_otp')
    else:
        form = PhoneForm()
    return render(request, 'accounts/login.html', {'form': form})


def verify_otp(request):
    """Step 2: verify OTP and log in, or route to registration if new user.
    Enforces strict checks for Federation Admin login."""
    phone = request.session.get('otp_phone')
    otp_id = request.session.get('otp_id')
    login_role = request.session.get('login_role', 'customer')
    if not phone or not otp_id:
        return redirect('accounts:login')

    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                otp = OTPRequest.objects.get(id=otp_id, phone_number=phone)
            except OTPRequest.DoesNotExist:
                messages.error(request, _("OTP session expired. Please request a new one."))
                return redirect('accounts:login')

            if otp.is_valid() and otp.code == code:
                otp.is_used = True
                otp.save(update_fields=['is_used'])

                # Check if user exists
                try:
                    user = User.objects.get(phone_number=phone)
                except User.DoesNotExist:
                    user = None

                # SPECIAL CHECK: Federation Admin
                if login_role == 'federation':
                    # Only allow if user exists AND is appointed as a federation head
                    if user and user.role == User.Role.FEDERATION and getattr(user, 'managed_federation', None) is not None:
                        pass # Authorized
                    else:
                        messages.error(request, _("You are not authorized as a Federation Admin. Please contact the Platform Administrator to be appointed as a Federation Head."))
                        return redirect('accounts:login')

                # Handle normal login/registration for other roles
                if not user:
                    # New user
                    user = User.objects.create(
                        phone_number=phone,
                        username=phone,
                        is_phone_verified=True,
                        role=User.Role[login_role.upper()] if login_role.upper() in User.Role.__members__ else User.Role.CUSTOMER
                    )
                else:
                    # Existing user - verify they aren't trying to log in as a role they don't have
                    # (except for superusers who can be anything)
                    if not user.is_superuser:
                        # Map login_role to User.Role
                        role_map = {
                            'customer': User.Role.CUSTOMER,
                            'builder': User.Role.BUILDER,
                            'worker': User.Role.WORKER,
                            'federation': User.Role.FEDERATION,
                        }
                        expected_role = role_map.get(login_role, User.Role.CUSTOMER)
                        if user.role != expected_role:
                            messages.error(request, _("Your account is registered as a %s, not a %s.") % (user.get_role_display(), login_role))
                            return redirect('accounts:login')

                login(request, user)
                del request.session['otp_phone']
                del request.session['otp_id']
                del request.session['login_role']

                if not user.first_name:
                    response = redirect('accounts:complete_profile')
                else:
                    messages.success(request, _("Welcome back, %(name)s!") % {'name': user.get_full_name() or user.phone_number})
                    response = redirect('core:home')
                return _apply_language(request, response, user)
            else:
                messages.error(request, _("Incorrect or expired OTP. Please try again."))
    else:
        form = OTPVerifyForm()
    return render(request, 'accounts/verify_otp.html', {'form': form, 'phone': phone})


@login_required
def complete_profile(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            _geocode_and_save_location(user)

            # Society joining logic for workers
            if user.role == User.Role.WORKER:
                society_id = form.cleaned_data.get('society')
                if not society_id:
                    messages.error(request, _("You must join a cooperative society to complete your profile."))
                    # Re-render form with error (do this by updating the form instance)
                    form = RegistrationForm(request.POST, instance=request.user)
                    return render(request, 'accounts/complete_profile.html', {'form': form})

                # Assign worker to selected society
                profile, _created = WorkerProfile.objects.get_or_create(user=user)
                profile.society = society_id
                profile.save(update_fields=['society'])

                messages.success(request, _("Profile completed and society joined. Welcome to Co-opSeva!"))
                response = redirect('workers:onboarding')
            else:
                messages.success(request, _("Profile completed. Welcome to Co-opSeva!"))
                response = redirect('core:home')

            return _apply_language(request, response, user)
    else:
        form = RegistrationForm(instance=request.user)
        # Populate society dropdown for workers
        form.fields['society'].queryset = Society.objects.filter(is_active=True)

    return render(request, 'accounts/complete_profile.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save()
            _geocode_and_save_location(user)
            messages.success(request, _("Profile updated successfully."))
            response = redirect('accounts:profile')
            return _apply_language(request, response, user)
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def update_location(request):
    """Saves the browser's GPS coordinates against the logged-in user.
    Used by the 'Use my location' control on the worker-onboarding form
    and the worker-comparison page (FR-034 Location Capture, with
    consent — the browser's own permission prompt is the consent gate)."""
    if request.method == 'POST':
        try:
            lat = float(request.POST.get('lat'))
            lng = float(request.POST.get('lng'))
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'error': 'Invalid coordinates'}, status=400)
        request.user.latitude = lat
        request.user.longitude = lng
        request.user.save(update_fields=['latitude', 'longitude'])
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'error': 'POST required'}, status=405)


def logout_view(request):
    logout(request)
    messages.info(request, _("You have been logged out."))
    return redirect('core:home')
