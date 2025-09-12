# schools/models.py
from django.db import models

class School(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    in_progress = models.BooleanField(default= True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
