from django.db import models
from core.models import SchoolOwnedModel


class Teacher(SchoolOwnedModel):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=20)
    schedule = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'teachers_teacher'
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"