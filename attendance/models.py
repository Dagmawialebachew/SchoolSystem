from django.db import models
from core.models import SchoolOwnedModel


class Attendance(SchoolOwnedModel):
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        LATE = "LATE", "Late"
        HALF_DAY = "HALF_DAY", "Half Day"

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE)
    class_program = models.ForeignKey("classes_app.ClassProgram", on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    session = models.ForeignKey(
        "classes_app.Session",  # optional timetable/period model
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    status = models.CharField(max_length=15, choices=Status.choices)
    remarks = models.TextField(blank=True, null=True)

    marked_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)
    marked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    synced = models.BooleanField(default=True)
    offline_created = models.BooleanField(default=False)  # set true when marked offline

    class Meta:
        unique_together = ("student", "class_program", "date", "session")
        ordering = ["-date", "class_program", "student"]

    def __str__(self):
        return f"{self.student} - {self.class_program} ({self.status}) on {self.date}"



class AttendanceLog(SchoolOwnedModel):
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name="logs")
    previous_status = models.CharField(max_length=15, blank=True, null=True)
    new_status = models.CharField(max_length=15)
    changed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)


