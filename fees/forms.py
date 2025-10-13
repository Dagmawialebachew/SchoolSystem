from django import forms
from dal import autocomplete
from dal_select2.widgets import ModelSelect2
from students.models import Student
from .models import FeeStructure, Invoice
from classes_app.models import Division, ClassProgram
from django.utils import timezone


# ----------------------
#  FEE FORM
# ----------------------
class FeeForm(forms.ModelForm):
    class Meta:
        model = FeeStructure
        fields = [
            "name", "division", "class_program",
            "amount", "description", "in_progress"
        ]
        widgets = {
            "name": forms.Select(attrs={"class": "w-full"}),
            "division": forms.Select(attrs={"class": "w-full"}),
            "class_program": forms.Select(attrs={"class": "w-full"}),
            "amount": forms.NumberInput(attrs={"class": "w-full", "placeholder": "Enter fee amount"}),
            "description": forms.Textarea(attrs={
                "class": "w-full", "rows": 1, "placeholder": "Optional description"
            }),
            "in_progress": forms.CheckboxInput(attrs={"class": "rounded"}),
        }
        
    def __init__(self, *args, **kwargs):
            user = kwargs.pop('user', None)
            super().__init__(*args, **kwargs)

            if user and hasattr(user, 'school'):
                self.fields['division'].queryset = Division.objects.filter(school=user.school)
                self.fields['class_program'].queryset = ClassProgram.objects.filter(school=user.school)
            else:
                self.fields['division'].queryset = Division.objects.none()
                self.fields['class_program'].queryset = ClassProgram.objects.none()

            self.fields['division'].label_from_instance = lambda obj: obj.name

# ----------------------
#  INVOICE FORM
# ----------------------
from django import forms
from .models import Invoice, FeeStructure
from students.models import Student

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["student", "fee", "amount_due", "amount_paid", "status", "due_date"]
        widgets = {
            "student": forms.Select(attrs={"class": "form-select w-full"}),
            "fee": forms.Select(attrs={"class": "form-select w-full"}),
            "amount_due": forms.NumberInput(attrs={"class": "form-input w-full", "placeholder": "Enter amount due"}),
            "amount_paid": forms.NumberInput(attrs={"class": "form-input w-full", "placeholder": "Enter amount paid"}),
            "status": forms.Select(attrs={"class": "form-select w-full"}),
            "due_date": forms.DateInput(attrs={"type": "date", "class": "form-input w-full"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Filter students & fees by the user's school
        if user and hasattr(user, "school"):
            self.fields["student"].queryset = Student.objects.filter(school=user.school)
            self.fields["fee"].queryset = FeeStructure.objects.filter(school=user.school)
        else:
            self.fields["student"].queryset = Student.objects.none()
            self.fields["fee"].queryset = FeeStructure.objects.none()

        # Use readable labels
        self.fields["student"].label_from_instance = lambda obj: obj.full_name
        self.fields["fee"].label_from_instance = lambda obj: obj.name
    class Meta:
        model = Invoice
        student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        widget=ModelSelect2(
            url='student-autocomplete',
            attrs={'class': 'form-select w-full'}
        )
    )
        fields = ["student", "fee", "amount_due", "amount_paid", "status", "due_date"]
        widgets = {
            "student": forms.Select(attrs={"class": "form-select w-full"}),
            "fee": forms.Select(attrs={"class": "form-select w-full"}),
            "amount_due": forms.NumberInput(attrs={"class": "form-input w-full", "placeholder": "Enter amount due"}),
            "amount_paid": forms.NumberInput(attrs={"class": "form-input w-full", "placeholder": "Enter amount paid"}),
            "status": forms.Select(attrs={"class": "form-select w-full"}),
            "due_date": forms.DateInput(attrs={"type": "date", "class": "form-input w-full"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['fee'].queryset = FeeStructure.objects.filter(school=user.school)
            self.fields['student'].queryset = Student.objects.filter(school=user.school)
        else:
            self.fields['fee'].queryset = FeeStructure.objects.none()
            self.fields['student'].queryset = Student.objects.none()

        self.fields['fee'].label_from_instance = lambda obj: obj.name
        self.fields['student'].label_from_instance = lambda obj: obj.full_name
    class Meta:
        model = Invoice
        fields = [
            "student", "fee", "amount_due", "amount_paid",
            "status", "due_date"
        ]
        widgets = {
            "student": forms.Select(attrs={
                "class": "form-select text-sm rounded-md border border-gray-300 px-3 py-2 focus:ring focus:ring-blue-500 focus:border-blue-500"
            }),
            "fee": forms.Select(attrs={
                "class": "form-select text-sm rounded-md border border-gray-300 px-3 py-2 focus:ring focus:ring-blue-500 focus:border-blue-500"
            }),
            "amount_due": forms.NumberInput(attrs={
                "class": "form-input text-sm rounded-md border border-gray-300 px-3 py-2 focus:ring focus:ring-blue-500 focus:border-blue-500",
                "placeholder": "Enter amount due"
            }),
            "amount_paid": forms.NumberInput(attrs={
                "class": "form-input text-sm rounded-md border border-gray-300 px-3 py-2 focus:ring focus:ring-blue-500 focus:border-blue-500",
                "placeholder": "Enter amount paid"
            }),
            "status": forms.Select(attrs={
                "class": "form-select text-sm rounded-md border border-gray-300 px-3 py-2 focus:ring focus:ring-blue-500 focus:border-blue-500"
            }),
            "due_date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-input text-sm rounded-md border border-gray-300 px-3 py-2 focus:ring focus:ring-blue-500 focus:border-blue-500"
            }),
        }


    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['fee'].queryset = FeeStructure.objects.filter(school=user.school)
        else:
            self.fields['fee'].queryset = FeeStructure.objects.none()

        self.fields['fee'].label_from_instance = lambda obj: obj.name
# ----------------------
#  PAYMENT FORM
# ----------------------
class PaymentForm(forms.Form):
    # Hidden fields for total payment and selected invoices
    invoice_ids = forms.CharField(widget=forms.HiddenInput())
    payment_amount = forms.DecimalField(widget=forms.HiddenInput())
    
    # Dropdown for Payment Method
    method = forms.ChoiceField(
        choices=[("Cash", "Cash"), ("Bank Transfer", "Bank Transfer"), ("Mobile Money", "Mobile Money")],
        widget=forms.Select(attrs={"class": "form-select w-full rounded-xl border-gray-300"})
    )

    # Optional transaction reference
    reference = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-input w-full rounded-xl border-gray-300",
            "placeholder": "Optional: Transaction ID, MPesa code..."
        })
    )

    # Optional date of payment
    paid_on = forms.DateTimeField(
        required= False,
        widget=forms.DateTimeInput(attrs={
            "type": "datetime-local",
            "class": "form-input w-full rounded-xl border-gray-300"
        })
    )
    
    receipt_type = forms.ChoiceField(
    choices=[
        ("single", "Single receipt for all invoices"),
        ("separate", "Separate receipt for each invoice"),
        ("none", "No receipt"),
    ],
    initial="single",  # Default option
    widget=forms.RadioSelect
)
    

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

        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,        'placeholder': 'e.g. Duplicate payment, wrong amount, payment entered for wrong student...',
})
    )

    def clean(self):
        cleaned_data = super().clean()
        choice = cleaned_data.get('reason_choice')
        custom = cleaned_data.get('custom_reason')

        if choice == "Other" and not custom.strip():
            self.add_error('custom_reason', "Please specify a reason if selecting 'Other'.")
        return cleaned_data