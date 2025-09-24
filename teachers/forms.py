from django import forms
from classes_app.models import ClassProgram
from .models import Teacher


class TailwindModelForm(forms.ModelForm):
    """Base form that applies Tailwind styling to all fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            widget = field.widget

            # Base Tailwind classes
            base_classes = (
                "w-full px-3 py-2 border border-gray-300 rounded-md "
                "focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
            )

            if isinstance(widget, forms.Select):
                widget.attrs["class"] = f"{base_classes} bg-white"
            elif isinstance(widget, forms.DateInput):
                widget.input_type = "date"
                widget.attrs["class"] = base_classes
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = (
                    "h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                )
            else:
                widget.attrs["class"] = base_classes

            if not widget.attrs.get("placeholder"):
                widget.attrs["placeholder"] = f"Enter {field.label.lower()}"


class TeacherForm(TailwindModelForm):
    classes = forms.ModelMultipleChoiceField(
    queryset=ClassProgram.objects.none(),  # filtered by school in __init__
    required=False,
    widget=forms.SelectMultiple(
        attrs={"id": "classesSelect", "class": "w-full", "multiple": "multiple"}
    ),
    label="Assign Classes (optional)",
    help_text="Optional: assign this teacher to one or more classes.",
)

    class Meta:
        model = Teacher
        fields = [
            "first_name", "last_name", "phone", "email",
            "bio", "qualification", "specialization", "hire_date",
            "employment_status", "is_active",
        ]

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = ClassProgram.objects.select_related("division").order_by(
            "division__name", "name"
        )
        if school is not None:
            qs = qs.filter(school=school)
        self.fields["classes"].queryset = qs

        # <-- Add this block to pre-populate the selected classes
        if self.instance.pk:
            self.fields["classes"].initial = self.instance.all_classes
            print("Initial assigned classes:", self.fields["classes"].initial)

            print("All available classes in the field:")
            for c in self.fields["classes"].queryset:
                print(c)
