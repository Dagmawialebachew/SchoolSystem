# classes_app/models.py
from django.db import models
from SchoolSystem import settings
from core.models import SchoolOwnedModel

class ClassProgramQuerySet(models.QuerySet):
    def for_user(self, user):
        if user.role == "SUPER_ADMIN":
            return self.all()
        elif user.role == "SCHOOL_ADMIN":
            return self.filter(school=user.school)
        elif user.role == "TEACHER":
            teacher = getattr(user, "teacher_profile", None)
            return self.filter(
                models.Q(teacher=teacher) | models.Q(subject_assignments__teacher=teacher)
            ).distinct() if teacher else self.none()
        else:
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
    in_progress = models.BooleanField(default=True)

    class Meta:
        unique_together = ("school", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name

class Subject(SchoolOwnedModel):
    division = models.ForeignKey("Division", on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("school", "division", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.division.get_name_display()})"

class ClassProgram(SchoolOwnedModel):
    division = models.ForeignKey("Division", on_delete=models.CASCADE, related_name="classes")
    name = models.CharField(max_length=100)
    teachers = models.ManyToManyField(
        "teachers.Teacher",
        through="ClassTeacherAssignment",
        related_name="assigned_classes",
        blank=True
    )
    teacher = models.ForeignKey(
        "teachers.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="optional_classes",
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

    @property
    def homeroom_teachers(self):
        return self.teacher_assignments.filter(is_homeroom_teacher=True)

    @property
    def homeroom_count(self):
        return self.homeroom_teachers.count()

class ClassTeacherAssignment(SchoolOwnedModel):
    class_program = models.ForeignKey("ClassProgram", on_delete=models.CASCADE, related_name="teacher_assignments")
    teacher = models.ForeignKey("teachers.Teacher", on_delete=models.CASCADE, related_name="class_assignments")
    is_homeroom_teacher = models.BooleanField(default=False)

    class Meta:
        unique_together = ("class_program", "teacher")
        ordering = ["class_program", "teacher"]

    def __str__(self):
        role = "Homeroom" if self.is_homeroom_teacher else "Teacher"
        return f"{self.teacher} - {self.class_program} ({role})"

class ClassSubjectAssignment(SchoolOwnedModel):
    class_program = models.ForeignKey("ClassProgram", on_delete=models.CASCADE, related_name="subject_assignments")
    subject = models.ForeignKey("Subject", on_delete=models.CASCADE, related_name="class_assignments")
    teacher = models.ForeignKey("teachers.Teacher", on_delete=models.SET_NULL, null=True, blank=True, related_name="subject_assignments")

    class Meta:
        unique_together = ("class_program", "subject")
        ordering = ["class_program", "subject"]

    def __str__(self):
        return f"{self.class_program} - {self.subject} ({self.teacher or 'Unassigned'})"



# classes_app/models.py
from django.db import models
from core.models import SchoolOwnedModel

class Session(SchoolOwnedModel):
    """
    Represents a period or session in a class timetable.
    E.g., "Period 1", "Math", "08:00 - 08:45"
    """
    class_program = models.ForeignKey(
        "ClassProgram",
        on_delete=models.CASCADE,
        related_name="sessions"
    )
    name = models.CharField(max_length=100, help_text="E.g., Period 1, Math, or 08:00 - 08:45")
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("class_program", "name")
        ordering = ["class_program", "start_time"]

    def __str__(self):
        return f"{self.class_program.name} - {self.name}"
    
    

class DivisionLog(models.Model):
    ACTION_CHOICES = [
        ("CREATE", "Created"),
        ("UPDATE", "Updated"),
        ("DELETE", "Deleted"),
    ]

    division = models.ForeignKey("Division", on_delete=models.CASCADE, related_name="logs")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="division_logs"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    changes = models.TextField(blank=True, null=True)  # JSON or plain text diff
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.division.name} - {self.action} by {self.actor or 'System'} at {self.timestamp:%Y-%m-%d %H:%M}"