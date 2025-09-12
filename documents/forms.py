# documents/forms.py
from django import forms
from .models import Document

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["file", "doc_type", "assigned_student", "assigned_class"]
        widgets = {
            "doc_type": forms.Select(attrs={"class": "form-control"}),
            "assigned_student": forms.Select(attrs={"class": "form-control"}),
            "assigned_class": forms.Select(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get("assigned_student")
        class_program = cleaned_data.get("assigned_class")

        if not student and not class_program:
            raise forms.ValidationError("You must assign the document either to a student or a class.")
        
        return cleaned_data
