from django import forms
from .models import Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'date_of_birth',
            'parent_name', 'parent_phone', 'next_payment_date', 'payment_status'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'parent_name': forms.TextInput(attrs={'class': 'form-input'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-input'}),
            'next_payment_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'payment_status': forms.Select(attrs={'class': 'form-input'}),
        }