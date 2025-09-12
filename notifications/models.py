# notifications/models.py
from django.db import models
from django.conf import settings
from schools.models import School


class AnnouncementQuerySet(models.QuerySet):
    def for_user(self, user):
        if user.role == "SUPER_ADMIN":
            return self.all()
        elif user.role == "SCHOOL_ADMIN":
            return self.filter(school=user.school)
        elif user.role == "TEACHER":
            return self.filter(school=user.school, target__in=["ALL", "TEACHERS"])
        elif user.role == "PARENT":
            return self.filter(school=user.school, target__in=["ALL", "PARENTS"])
        else:
            return self.none()


class Announcement(models.Model):
    TARGET_CHOICES = [
        ('ALL', 'All Users'),
        ('TEACHERS', 'Teachers'),
        ('PARENTS', 'Parents'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    target = models.CharField(max_length=20, choices=TARGET_CHOICES, default='ALL')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AnnouncementQuerySet.as_manager()  # 👈 attach custom manager

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.school.name})"
