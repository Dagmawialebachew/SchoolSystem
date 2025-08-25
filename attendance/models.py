from django.db import models
from core.models import SchoolOwnedModel


class Attendance(SchoolOwnedModel):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
    ]
    
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    marked_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'attendance_attendance'
        unique_together = ('student', 'date')
        ordering = ['-date', 'student']
    
    def __str__(self):
        return f"{self.student} - {self.date} ({self.status})"