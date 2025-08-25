from django import forms
from .models import Teacher


class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['first_name', 'last_name', 'bio', 'phone', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'bio': forms.Textarea(attrs={'class': 'form-input', 'rows': 4}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }