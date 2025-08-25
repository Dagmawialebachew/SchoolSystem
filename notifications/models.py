from django.db import models
from core.models import SchoolOwnedModel


class Announcement(SchoolOwnedModel):
    TARGET_CHOICES = [
        ('ALL', 'All'),
        ('TEACHERS', 'Teachers'),
        ('PARENTS', 'Parents'),
    ]
    
    content = models.TextField()
    target = models.CharField(max_length=20, choices=TARGET_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications_announcement'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.target} - {self.content[:50]}..."