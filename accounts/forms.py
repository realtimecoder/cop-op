from django import forms
from django.core.validators import RegexValidator
from django.apps import apps

from .models import User

phone_validator = RegexValidator(
    regex=r'^[6-9]\d{9}$',
    message="Enter a valid 10-digit Indian mobile number."
)


class PhoneForm(forms.Form):
    """Step 1 of OTP login/registration: capture phone number."""
    phone_number = forms.CharField(
        max_length=10, validators=[phone_validator],
        widget=forms.TextInput(attrs={
            'placeholder': '9XXXXXXXXX', 'class': 'input-field', 'inputmode': 'numeric',
            'maxlength': '10', 'autocomplete': 'tel',
        })
    )


class OTPVerifyForm(forms.Form):
    """Step 2 of OTP login: verify the 6-digit code."""
    code = forms.CharField(
        max_length=6, min_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': '••••••', 'class': 'input-field otp-field', 'inputmode': 'numeric',
            'maxlength': '6', 'autocomplete': 'one-time-code',
        })
    )


class RegistrationForm(forms.ModelForm):
    """Used right after first-time OTP verification to complete the profile."""
    society = forms.ModelChoiceField(
        queryset=apps.get_model('workers', 'Society').objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'input-field'}),
        label="Join a Cooperative Society"
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'role', 'address', 'city', 'pincode', 'preferred_language']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Last name'}),
            'role': forms.Select(attrs={'class': 'input-field'}),
            'address': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Address'}),
            'city': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'City'}),
            'pincode': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'PIN code'}),
            'preferred_language': forms.Select(attrs={'class': 'input-field'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Public self-registration is limited to customer / builder / worker.
        self.fields['role'].choices = [
            (User.Role.CUSTOMER, 'Customer'),
            (User.Role.BUILDER, 'Builder / Institutional Customer'),
            (User.Role.WORKER, 'Worker'),
        ]
        from django.conf import settings
        self.fields['preferred_language'].widget = forms.Select(choices=settings.LANGUAGES,
                                                                  attrs={'class': 'input-field'})


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'address', 'city', 'pincode',
                  'emergency_contact', 'preferred_language', 'profile_photo']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input-field'}),
            'last_name': forms.TextInput(attrs={'class': 'input-field'}),
            'address': forms.TextInput(attrs={'class': 'input-field'}),
            'city': forms.TextInput(attrs={'class': 'input-field'}),
            'pincode': forms.TextInput(attrs={'class': 'input-field'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'input-field'}),
            'preferred_language': forms.Select(attrs={'class': 'input-field'}),
            'profile_photo': forms.ClearableFileInput(attrs={'class': 'input-file', 'accept': 'image/png,image/jpeg,image/webp'}),
        }

    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        if not photo or not hasattr(photo, 'content_type'):
            # No new file uploaded (or it's the existing already-saved file) — nothing to validate.
            return photo
        max_size_mb = 5
        if photo.size > max_size_mb * 1024 * 1024:
            raise forms.ValidationError(
                f"That image is too large ({photo.size // (1024*1024)} MB). Please upload one under {max_size_mb} MB.")
        allowed_types = {'image/jpeg', 'image/png', 'image/webp'}
        if photo.content_type not in allowed_types:
            raise forms.ValidationError(
                "Please upload a JPG, PNG or WEBP image. iPhone photos saved as HEIC aren't supported — "
                "switch your camera to 'Most Compatible' format in Settings, or convert the photo first.")
        return photo
