# forms.py
from django import forms
from .models import Student
from classes_app.models import Division
from fees.models import FeeStructure


class TailwindModelForm(forms.ModelForm):
    """Base ModelForm for Tailwind styling if you want to extend later."""
    pass


class StudentForm(TailwindModelForm):
    class Meta:
        model = Student
        fields = [
            "full_name",
            "date_of_birth",
            "parent_name",
            "parent_phone",
            "division",
            "fee_structures",  # ✅ FIXED MISSING COMMA
            "billing_cycle",
            "custom_months",
            "payment_status",
            "starting_billing_month",
            "opening_balance",
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Enter full name'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'type': 'date',
            }),
            'parent_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Enter parent name'
            }),
            'parent_phone': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Enter phone number'
            }),
            'division': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500',
            }),
            'fee_structures': forms.SelectMultiple(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500',
            }),
            'billing_cycle': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500',
            }),
            'custom_months': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Enter months (if CUSTOM selected)',
                'min': 1,
            }),
            'payment_status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500',
            }),
            'starting_billing_month': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'type': 'date',
            }),
            'opening_balance': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Enter opening balance',
                'min': 0,
                'step': '0.01'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and hasattr(user, 'school'):
            self.fields['division'].queryset = Division.objects.filter(school=user.school)
            self.fields['fee_structures'].queryset = FeeStructure.objects.filter(school=user.school)
        else:
            self.fields['division'].queryset = Division.objects.none()
            self.fields['fee_structures'].queryset = FeeStructure.objects.none()

        self.fields['division'].label_from_instance = lambda obj: obj.name
        self.fields['fee_structures'].label_from_instance = lambda obj: f"{obj} - {obj.amount}"

    def clean(self):
        cleaned_data = super().clean()
        billing_cycle = cleaned_data.get("billing_cycle")
        custom_months = cleaned_data.get("custom_months")

        if billing_cycle == "CUSTOM":
            if not custom_months:
                self.add_error("custom_months", "This field is required when billing cycle is custom.")
            elif custom_months <= 0:
                self.add_error("custom_months", "Custom months must be greater than 0.")

        return cleaned_data


REVERSAL_REASONS = [
    ("Entered wrong amount", "Entered wrong amount"),
    ("Payment assigned to wrong student", "Payment assigned to wrong student"),
    ("Duplicate payment entry", "Duplicate payment entry"),
    ("Reversal requested by accountant", "Reversal requested by accountant"),
    ("Other", "Other (please specify)"),
]

class PaymentReversalForm(forms.Form):
    reason_choice = forms.ChoiceField(
        choices=REVERSAL_REASONS,
        required=True,
        label="Reason for Reversal",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    custom_reason = forms.CharField(
        required=False,
        label="Custom Reason",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    def clean(self):
        cleaned_data = super().clean()
        choice = cleaned_data.get('reason_choice')
        custom = cleaned_data.get('custom_reason')

        if choice == "Other" and not custom.strip():
            self.add_error('custom_reason', "Please specify a reason if selecting 'Other'.")
        return cleaned_data