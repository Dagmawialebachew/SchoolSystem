# teachers/models.py
from django.db import models
from django.conf import settings
from classes_app.models import ClassProgram
from core.models import SchoolOwnedModel
from django.core.validators import RegexValidator

ethiopian_phone_validator = RegexValidator(
    regex=r'^\+251\d{9}$',
    message="Phone number must start with 251 and be 11–12 digits long (e.g. 251960306801)."
)

class Teacher(SchoolOwnedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_profile",
        null=True,
        blank=True,
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=13, validators=[ethiopian_phone_validator], unique=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="teachers/", null=True, blank=True)

    employee_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    employment_status = models.CharField(max_length=20, choices=[("full_time","Full-time"),("part_time","Part-time"),("contract","Contract")], default="full_time")
    is_active = models.BooleanField(default=True)
    qualification = models.CharField(max_length=255, blank=True)
    specialization = models.CharField(max_length=255, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    is_homeroom_teacher = models.BooleanField(default=False)
    schedule = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "teachers_teacher"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def divisions(self):
        return set(
        ca.class_program.division
        for ca in self.class_assignments.select_related("class_program__division")
    )

    @property
    def all_classes(self):
        homeroom_classes = ClassProgram.objects.filter(
        teacher_assignments__teacher=self,
        teacher_assignments__is_homeroom_teacher=True
    )
        if homeroom_classes is None:
            homeroom_classes = []
        subject_classes = [ca.class_program for ca in self.subject_assignments.select_related("class_program")]
        return set(list(homeroom_classes) + subject_classes)

    @property
    def subjects(self):
        return set(assignment.subject for assignment in self.subject_assignments.select_related("subject"))
