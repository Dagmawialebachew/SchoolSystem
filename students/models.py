from django.db import models
from core.models import SchoolOwnedModel


class Student(SchoolOwnedModel):
    PAYMENT_STATUS_CHOICES = [
        ('PAID', 'Paid'),
        ('PENDING', 'Pending'),
        ('OVERDUE', 'Overdue'),
    ]
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    parent_name = models.CharField(max_length=200)
    parent_phone = models.CharField(max_length=20)
    registration_date = models.DateField(auto_now_add=True)
    next_payment_date = models.DateField(null=True, blank=True)
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING'
    )
    
    class Meta:
        db_table = 'students_student'
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"