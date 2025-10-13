# attendance_app/forms.py
from django import forms
from django.core.exceptions import ValidationError
from datetime import datetime
from .models import Attendance
from classes_app.models import ClassProgram
from students.models import Student


class AttendanceModelForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ["student", "class_program", "date", "session", "status", "remarks"]

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school is None:
            raise ValueError("School is required.")
        # Scope queryset fields
        self.fields["class_program"].queryset = ClassProgram.objects.filter(school=school)
        self.fields["student"].queryset = Student.objects.filter(school=school)


class BaseSchoolScopedForm(forms.Form):
    """Inject school for scoped validation."""
    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.school = school
        if self.school is None:
            raise ValueError("School must be provided for attendance forms.")


class AttendanceEditForm(BaseSchoolScopedForm):
    student_id = forms.IntegerField()
    class_program_id = forms.IntegerField()
    date = forms.CharField()  # we'll parse YYYY-MM-DD
    session = forms.CharField(required=False)
    status = forms.ChoiceField(choices=Attendance.Status.choices)
    remarks = forms.CharField(required=False)

    def clean_date(self):
        value = self.cleaned_data["date"]
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Invalid date format. Use YYYY-MM-DD.")

    def clean(self):
        cleaned = super().clean()
        school = self.school
        # Validate relations within the same school
        try:
            cleaned["class_program"] = ClassProgram.objects.get(
                pk=cleaned["class_program_id"], school=school
            )
        except ClassProgram.DoesNotExist:
            raise ValidationError("Class program not found in this school.")

        try:
            cleaned["student"] = Student.objects.get(
                pk=cleaned["student_id"], school=school
            )
        except Student.DoesNotExist:
            raise ValidationError("Student not found in this school.")

        # Optional: normalize empty session to None (matches unique_together)
        cleaned["session"] = cleaned.get("session") or None
        # Normalize remarks
        cleaned["remarks"] = (cleaned.get("remarks") or "").strip() or None
        return cleaned


class AttendanceBulkStatusForm(BaseSchoolScopedForm):
    class_program_id = forms.IntegerField()
    date = forms.CharField()
    session = forms.CharField(required=False)
    status = forms.ChoiceField(choices=Attendance.Status.choices)
    student_ids = forms.TypedMultipleChoiceField(
        coerce=int, choices=[], required=True
    )

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, school=school, **kwargs)
        self.school = school

        # Populate student choices dynamically
        students = Student.objects.filter(school=school)
        self.fields["student_ids"].choices = [(s.id, s.full_name or str(s.id)) for s in students]

    def clean_date(self):
        value = self.cleaned_data["date"]
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Invalid date format. Use YYYY-MM-DD.")

    def clean(self):
        cleaned = super().clean()
        school = self.school

        try:
            cleaned["class_program"] = ClassProgram.objects.get(
                pk=cleaned["class_program_id"], school=school
            )
        except ClassProgram.DoesNotExist:
            raise ValidationError("Class program not found in this school.")

        # Validate student IDs belong to this school (and optionally to the class)
        student_ids = cleaned.get("student_ids") or []
        students = Student.objects.filter(id__in=student_ids, school=school)
        if len(student_ids) != students.count():
            raise ValidationError("One or more students are invalid for this school.")
        cleaned["students"] = list(students)

        cleaned["session"] = cleaned.get("session") or None
        return cleaned



class AttendanceFilterForm(BaseSchoolScopedForm):
    class_program = forms.IntegerField(required=False)
    date = forms.CharField(required=False)
    session = forms.CharField(required=False)
    status = forms.ChoiceField(choices=Attendance.Status.choices, required=False)

    def clean_date(self):
        value = self.cleaned_data.get("date")
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Invalid date format. Use YYYY-MM-DD.")

    def clean_class_program(self):
        value = self.cleaned_data.get("class_program")
        if not value:
            return None
        from classes_app.models import ClassProgram
        try:
            return ClassProgram.objects.get(pk=value, school=self.school)
        except ClassProgram.DoesNotExist:
            raise ValidationError("Class program not found in this school.")
