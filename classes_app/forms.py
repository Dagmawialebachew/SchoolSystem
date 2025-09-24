from django import forms
from .models import ClassProgram, ClassTeacherAssignment, Division
from teachers.models import Teacher

class TailwindModelForm(forms.ModelForm):
    """Base form that applies Tailwind styling to all fields."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget

            # Add Tailwind base classes if not already set
            existing_classes = widget.attrs.get("class", "")
            base_classes = "w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
            widget.attrs["class"] = f"{existing_classes} {base_classes}".strip()

            # Special case for DateInput
            if isinstance(widget, forms.DateInput):
                widget.input_type = "date"

class ClassProgramForm(TailwindModelForm):
    # Override the teacher field to allow multiple selections
    homeroom_teachers = forms.ModelMultipleChoiceField(
        queryset=Teacher.objects.all(),
        required=False,
        widget=forms.MultipleHiddenInput(),
        help_text="Select up to 2 homeroom teachers (optional)."
    )

    class Meta:
        model = ClassProgram
        fields = ["name", "division", "schedule"]  # removed teacher field, using homeroom_teachers instead
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "(e.g., Grade 1A, Grade 4A, Kg 2A)",
                "class": "w-full p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            }),
            "division": forms.Select(attrs={
                "class": "w-full p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            }),
            "schedule": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Enter schedule details (optional, e.g., Mon 8-10, Wed 10-12)",
                "class": "w-full p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)  # pass request.user from view
        super().__init__(*args, **kwargs)

        if user:
            self.fields["division"].queryset = Division.objects.filter(school=user.school)
            self.fields["homeroom_teachers"].queryset = Teacher.objects.filter(school=user.school)
        
            
        if self.instance.pk:
            self.initial["homeroom_teachers"] = self.instance.teacher_assignments.filter(
                is_homeroom_teacher=True
            ).values_list("teacher_id", flat=True)

    def clean_homeroom_teachers(self):
        teachers = self.cleaned_data.get("homeroom_teachers")
        if teachers.count() > 2:
            raise forms.ValidationError("You can only select up to 2 homeroom teachers.")
        return teachers

    def save(self, commit=True, *args, **kwargs):
        instance = super().save(commit=commit)
        instance.school = self.instance.school or getattr(self, 'school', None)  # fallback if needed
        if commit:
            # Clear previous homeroom teachers
            ClassTeacherAssignment.objects.filter(class_program=instance, is_homeroom_teacher=True).delete()
            for teacher in self.cleaned_data.get("homeroom_teachers", []):
                ClassTeacherAssignment.objects.create(
                    class_program=instance,
                    teacher=teacher,
                    is_homeroom_teacher=True
                )
        return instance

    
   