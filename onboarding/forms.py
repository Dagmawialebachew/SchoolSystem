from django import forms
from schools.models import School
from classes_app.models import Division
from fees.models import FeeStructure
from django.forms import formset_factory


class BaseStyledForm(forms.ModelForm):
    """Base form with Tailwind-friendly styling applied to all fields."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            })


class SchoolForm(BaseStyledForm):
    class Meta:
        model = School
        fields = ["name","address","phone","email","website"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }


class DivisionForm(BaseStyledForm):
    class Meta:
        model = Division
        fields = ["name", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

DivisionFormSet = forms.formset_factory(DivisionForm, extra=1, can_delete=True)




class FeeStructureForm(forms.ModelForm):
    class Meta:
        model = FeeStructure
        fields = ["name", "amount", "description"]