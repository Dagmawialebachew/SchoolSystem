from django import forms
from .models import ClassProgram

class ClassProgramForm(forms.ModelForm):
    class Meta:
        model = ClassProgram
        fields = ["name", "division", "teacher", "schedule"]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            }),
            "division": forms.Select(attrs={
                "class": "w-full p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            }),
            "teacher": forms.Select(attrs={
                "class": "w-full p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            }),
            "schedule": forms.Textarea(attrs={
                "class": "w-full p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "rows": 3,
            })
            
        }
