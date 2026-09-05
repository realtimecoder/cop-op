from django import forms
from .models import Booking, Complaint, BookingRequest


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['scheduled_date', 'scheduled_time', 'address', 'city', 'pincode',
                  'instructions', 'is_emergency', 'is_recurring', 'recurrence_frequency',
                  'workers_required', 'duration_days', 'hours_booked']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'class': 'input-field', 'type': 'date'}),
            'scheduled_time': forms.TimeInput(attrs={'class': 'input-field', 'type': 'time'}),
            'address': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Full service address'}),
            'city': forms.TextInput(attrs={'class': 'input-field'}),
            'pincode': forms.TextInput(attrs={'class': 'input-field'}),
            'instructions': forms.Textarea(attrs={'class': 'input-field', 'rows': 3,
                                                    'placeholder': 'Any special instructions (optional)'}),
            'is_emergency': forms.CheckboxInput(attrs={'class': 'input-checkbox'}),
            'is_recurring': forms.CheckboxInput(attrs={'class': 'input-checkbox'}),
            'recurrence_frequency': forms.Select(attrs={'class': 'input-field'}),
            'workers_required': forms.NumberInput(attrs={'class': 'input-field', 'min': 1}),
            'duration_days': forms.NumberInput(attrs={'class': 'input-field', 'min': 1}),
            'hours_booked': forms.NumberInput(attrs={'class': 'input-field', 'min': 1, 'step': '0.5'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # These fields only apply to specific booking types (builder/team jobs
        # or hourly services). Making them optional here — with sane defaults
        # applied in the view — is what actually fixes bookings: previously
        # the template only rendered these inputs conditionally, but Django
        # still required them, so every non-builder, non-hourly booking
        # failed form validation silently. Never repeat that mistake.
        self.fields['workers_required'].required = False
        self.fields['duration_days'].required = False
        self.fields['hours_booked'].required = False
        self.fields['recurrence_frequency'].required = False
        self.fields['instructions'].required = False


class BookingRequestForm(forms.ModelForm):
    class Meta:
        model = BookingRequest
        fields = ['scheduled_date', 'scheduled_time', 'address', 'city', 'pincode',
                  'instructions', 'workers_required', 'duration_days', 'hours_booked']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'class': 'input-field', 'type': 'date'}),
            'scheduled_time': forms.TimeInput(attrs={'class': 'input-field', 'type': 'time'}),
            'address': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Full service address'}),
            'city': forms.TextInput(attrs={'class': 'input-field'}),
            'pincode': forms.TextInput(attrs={'class': 'input-field'}),
            'instructions': forms.Textarea(attrs={'class': 'input-field', 'rows': 3,
                                                    'placeholder': 'Any special instructions (optional)'}),
            'workers_required': forms.NumberInput(attrs={'class': 'input-field', 'min': 1}),
            'duration_days': forms.NumberInput(attrs={'class': 'input-field', 'min': 1}),
            'hours_booked': forms.NumberInput(attrs={'class': 'input-field', 'min': 1, 'step': '0.5'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['workers_required'].required = False
        self.fields['duration_days'].required = False
        self.fields['hours_booked'].required = False
        self.fields['instructions'].required = False

class ComplaintForm(forms.ModelForm):

    class Meta:
        model = Complaint
        fields = ['subject', 'description']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Subject'}),
            'description': forms.Textarea(attrs={'class': 'input-field', 'rows': 4,
                                                   'placeholder': 'Describe the issue in detail'}),
        }
