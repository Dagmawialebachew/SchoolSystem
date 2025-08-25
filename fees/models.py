from django.db import models
from core.models import SchoolOwnedModel


class FeeType(SchoolOwnedModel):
    name = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'fees_feetype'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Payment(SchoolOwnedModel):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank Transfer'),
        ('MOBILE', 'Mobile Money'),
    ]
    
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    fee_type = models.ForeignKey(FeeType, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'fees_payment'
        ordering = ['-due_date']
    
    def __str__(self):
        return f"{self.student} - {self.fee_type} - {self.amount}"