from django.db import models


class School(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'schools_school'
        ordering = ['name']
    
    def __str__(self):
        return self.name