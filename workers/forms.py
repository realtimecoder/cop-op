from django import forms
from django.utils import timezone

from .models import WorkerProfile, WorkerDocument, WorkerBlockedDate, WorkerCategoryChangeRequest
from catalog.models import ServiceCategory


class WorkerOnboardingForm(forms.ModelForm):
    """First-time onboarding, before the worker is verified. Categories can
    be set directly here because the whole profile — including these
    categories — is reviewed by the society operator during verification.
    Once verified, further category changes go through
    WorkerCategoryChangeRequest instead (see profile editing below)."""
    class Meta:
        model = WorkerProfile
        fields = ['categories', 'skill_grade', 'years_experience', 'bio',
                  'languages_spoken', 'service_radius_km']
        widgets = {
            'categories': forms.CheckboxSelectMultiple(),
            'skill_grade': forms.Select(attrs={'class': 'input-field'}),
            'years_experience': forms.NumberInput(attrs={'class': 'input-field', 'min': 0}),
            'bio': forms.Textarea(attrs={'class': 'input-field', 'rows': 3,
                                          'placeholder': 'Brief professional summary'}),
            'languages_spoken': forms.TextInput(attrs={'class': 'input-field'}),
            'service_radius_km': forms.NumberInput(attrs={'class': 'input-field', 'min': 1}),
        }


class WorkerProfileEditForm(forms.ModelForm):
    """Editing an already-onboarded worker's profile. Deliberately excludes
    `categories` — changing which service categories a worker performs
    always requires federation-admin approval (see
    WorkerCategoryChangeRequestForm), so it never appears here."""
    class Meta:
        model = WorkerProfile
        fields = ['skill_grade', 'years_experience', 'bio', 'languages_spoken',
                  'service_radius_km', 'is_available_now']
        widgets = {
            'skill_grade': forms.Select(attrs={'class': 'input-field'}),
            'years_experience': forms.NumberInput(attrs={'class': 'input-field', 'min': 0}),
            'bio': forms.Textarea(attrs={'class': 'input-field', 'rows': 3}),
            'languages_spoken': forms.TextInput(attrs={'class': 'input-field'}),
            'service_radius_km': forms.NumberInput(attrs={'class': 'input-field', 'min': 1}),
            'is_available_now': forms.CheckboxInput(attrs={'class': 'input-checkbox'}),
        }


class WorkerCategoryChangeRequestForm(forms.ModelForm):
    """Submits a request to change service categories. Takes effect only
    once a federation administrator approves it (see dashboard app)."""
    class Meta:
        model = WorkerCategoryChangeRequest
        fields = ['requested_categories', 'reason']
        widgets = {
            'requested_categories': forms.CheckboxSelectMultiple(),
            'reason': forms.Textarea(attrs={'class': 'input-field', 'rows': 2,
                                             'placeholder': 'Why do you want to change your categories? (optional)'}),
        }


class WorkerDocumentForm(forms.ModelForm):
    class Meta:
        model = WorkerDocument
        fields = ['doc_type', 'file', 'expiry_date']
        widgets = {
            'doc_type': forms.Select(attrs={'class': 'input-field'}),
            'file': forms.ClearableFileInput(attrs={'class': 'input-file',
                                                      'accept': 'image/png,image/jpeg,image/webp,application/pdf'}),
            'expiry_date': forms.DateInput(attrs={'class': 'input-field', 'type': 'date'}),
        }

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if not f or not hasattr(f, 'content_type'):
            return f
        max_size_mb = 8
        if f.size > max_size_mb * 1024 * 1024:
            raise forms.ValidationError(
                f"That file is too large ({f.size // (1024*1024)} MB). Please upload one under {max_size_mb} MB.")
        allowed_types = {'image/jpeg', 'image/png', 'image/webp', 'application/pdf'}
        if f.content_type not in allowed_types:
            raise forms.ValidationError(
                "Please upload a JPG, PNG, WEBP image or a PDF. iPhone HEIC photos aren't supported — "
                "switch your camera to 'Most Compatible' format, or share via WhatsApp first to auto-convert.")
        return f


class WorkerBlockedDateForm(forms.ModelForm):
    """Lets a worker mark a specific date as unavailable (leave, personal
    reasons), which the booking-date picker then greys out for customers."""
    class Meta:
        model = WorkerBlockedDate
        fields = ['date', 'reason']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'input-field', 'type': 'date'}),
            'reason': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Reason (optional)'}),
        }

    def clean_date(self):
        date = self.cleaned_data['date']
        if date < timezone.localdate():
            raise forms.ValidationError("Please choose today or a future date.")
        return date
