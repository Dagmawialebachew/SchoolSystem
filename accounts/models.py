from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('SUPER_ADMIN', 'Super Admin'),
        ('SCHOOL_ADMIN', 'School Admin'),
        ('TEACHER', 'Teacher'),
        ('PARENT', 'Parent'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PARENT')
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Leave blank for Super Admins"
    )
    phone = models.CharField(max_length=20, blank=True)
    
    class Meta:
        db_table = 'accounts_user'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_super_admin(self):
        return self.role == 'SUPER_ADMIN'
    
    def is_school_admin(self):
        return self.role == 'SCHOOL_ADMIN'
    
    def is_teacher(self):
        return self.role == 'TEACHER'
    
    def is_parent(self):
        return self.role == 'PARENT'