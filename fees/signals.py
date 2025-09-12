# fees/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from fees.models import Invoice
from students.models import Student
from datetime import date

@receiver(post_save, sender=Student)
def create_opening_balance_invoice(sender, instance, created, **kwargs):
    
    pass
