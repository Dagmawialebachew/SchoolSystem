from django import forms
from .models import Teacher

class TailwindModelForm(forms.ModelForm):
    """Base form that applies Tailwind styling to all fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget

            # Add Tailwind base classes
            classes = ""
            
            # Different defaults depending on widget type
            if isinstance(widget, forms.Select):
                classes += " bg-white"
            elif isinstance(widget, forms.DateInput):
                widget.input_type = "date"

            existing_classes = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing_classes} {classes}".strip()



class TeacherForm(TailwindModelForm):
    class Meta:
        model = Teacher
        fields = [
            "first_name",
            "last_name",
            "bio",
            "phone",
            "is_active",
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900',
                'placeholder': 'Enter last name'
            }),  
            'phone': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900',
                'placeholder': 'Enter phone number',
                'type': 'tel'
            }),
             'bio': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900',
            }),
              'is_active': forms.CheckboxInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md  text-gray-900',
            }),
             
        }