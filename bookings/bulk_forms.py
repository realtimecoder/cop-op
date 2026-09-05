from django import forms
from django.utils import timezone

from .models import BulkServiceRequest


class BulkServiceRequestForm(forms.ModelForm):
    """Institution → bulk/multiple-worker service request (Section 5,
    the "Institution" flow: Bulk request -> Cooperative assignment ->
    Completion)."""
    class Meta:
        model = BulkServiceRequest
        fields = ['service', 'workers_required', 'duration_days', 'start_date',
                  'address', 'city', 'pincode', 'instructions']
        widgets = {
            'service': forms.Select(attrs={'class': 'input-field'}),
            'workers_required': forms.NumberInput(attrs={'class': 'input-field', 'min': 1}),
            'duration_days': forms.NumberInput(attrs={'class': 'input-field', 'min': 1}),
            'start_date': forms.DateInput(attrs={'class': 'input-field', 'type': 'date'}),
            'address': forms.TextInput(attrs={'class': 'input-field'}),
            'city': forms.TextInput(attrs={'class': 'input-field'}),
            'pincode': forms.TextInput(attrs={'class': 'input-field'}),
            'instructions': forms.Textarea(attrs={'class': 'input-field', 'rows': 3}),
        }

    def clean_start_date(self):
        date = self.cleaned_data['start_date']
        if date < timezone.localdate():
            raise forms.ValidationError("Please choose today or a future date.")
        return date
