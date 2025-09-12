from django.db import models
from core.models import SchoolOwnedModel
from teachers.models import Teacher


class ClassProgramQuerySet(models.QuerySet):
    def for_user(self, user):
        """Scope classes based on role"""
        if user.role == 'SUPER_ADMIN':
            return self.all()
        elif user.role == 'SCHOOL_ADMIN':
            return self.filter(school=user.school)
        elif user.role == 'TEACHER':
            teacher = getattr(user, "teacher_profile", None)
            return self.filter(teacher=teacher) if teacher else self.none()
        else:  # Parent/student
            return self.none()

class Division(SchoolOwnedModel):
    DIVISION_CHOICES = [
        ("KINDERGARTEN", "Kindergarten"),
        ("PRIMARY_1_4", "Primary (Grades 1–4)"),
        ("PRIMARY_5_8", "Primary (Grades 5–8)"),
        ("SECONDARY_9_12", "Secondary (Grades 9–12)"),
    ]

    name = models.CharField(max_length=50, choices=DIVISION_CHOICES)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    in_progress = models.BooleanField(default= True)
    class Meta:
        unique_together = ("school", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.school.name} - {self.get_name_display()}"


class Subject(SchoolOwnedModel):
    division = models.ForeignKey(
        Division,
        on_delete=models.CASCADE,
        related_name="subjects"
    )
    name = models.CharField(max_length=100)  
    code = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("school", "division", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.division})"


class ClassProgramQuerySet(models.QuerySet):
    def for_user(self, user):
        if user.role == 'SUPER_ADMIN':
            return self.all()
        elif user.role == 'SCHOOL_ADMIN':
            return self.filter(school=user.school)
        elif user.role == 'TEACHER':
            teacher = getattr(user, "teacher_profile", None)
            return self.filter(teacher=teacher) if teacher else self.none()
        else:
            return self.none()


class ClassProgram(SchoolOwnedModel):
    division = models.ForeignKey(
        Division,
        on_delete=models.CASCADE,
        related_name="classes"
    )
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    schedule = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ClassProgramQuerySet.as_manager()

    class Meta:
        unique_together = ("school", "division", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.division.get_name_display()})"

    @property
    def subjects(self):
        return self.division.subjects.all()


class ClassSubjectAssignment(SchoolOwnedModel):
    class_program = models.ForeignKey(
        ClassProgram,
        on_delete=models.CASCADE,
        related_name="subject_assignments"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="class_assignments"
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_subject_assignments"
    )

    class Meta:
        unique_together = ("class_program", "subject")

    def __str__(self):
        return f"{self.class_program} - {self.subject} ({self.teacher or 'Unassigned'})"
