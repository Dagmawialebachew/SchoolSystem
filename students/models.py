from django.db import models
from core.models import SchoolOwnedModel
from classes_app.models import ClassProgram
from datetime import date
from dateutil.relativedelta import relativedelta
from accounts.models import User


class Student(SchoolOwnedModel):
    PAYMENT_STATUS_CHOICES = [
        ('PAID', 'Paid'),
        ('PENDING', 'Pending'),
        ('OVERDUE', 'Overdue'),
    ]

    BILLING_CYCLE_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('HALF_YEARLY', 'Half-Yearly'),
        ('YEARLY', 'Yearly'),
        ('CUSTOM', 'Custom'),
    ]

    full_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    parent_name = models.CharField(max_length=200)
    parent_phone = models.CharField(max_length=20)
    registration_date = models.DateField(auto_now_add=True)

    billing_cycle = models.CharField(
        max_length=20,
        choices=BILLING_CYCLE_CHOICES,
        default='MONTHLY'
    )
    custom_months = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="If CUSTOM is selected, enter number of months"
    )

    # 🔹 Late Enrollment Support
    starting_billing_month = models.DateField(
        null=True, blank=True,
        help_text="Month from which this system should start billing this student"
    )
    opening_balance = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0.00,
        help_text="Outstanding balance before joining the system"
    )

    next_payment_date = models.DateField(null=True, blank=True)
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING'
    )

    class_program = models.ForeignKey(
        "classes_app.ClassProgram",
        related_name="students",
        on_delete=models.PROTECT,
        null=True, blank=True
    )
    division = models.ForeignKey(
        "classes_app.Division",
        on_delete=models.PROTECT,
        related_name="students"
    )
    fee_structures = models.ManyToManyField(
        "fees.FeeStructure",
        blank=True,
        help_text="Select one or more fee structures for this student"
    )

    class Meta:
        db_table = "students_student"
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name

    def calculate_next_payment_date(self, from_date=None):
        """
        Calculate next_payment_date based on billing cycle or custom months.
        """
        months = 1
        if self.billing_cycle == "MONTHLY":
            months = 1
        elif self.billing_cycle == "QUARTERLY":
            months = 3
        elif self.billing_cycle == "HALF_YEARLY":
            months = 6
        elif self.billing_cycle == "YEARLY":
            months = 12
        elif self.billing_cycle == "CUSTOM":
            if not self.custom_months:
                raise ValueError("Custom months must be set when billing cycle is CUSTOM.")
            months = self.custom_months

        base_date = from_date or self.next_payment_date or date.today()
        return base_date + relativedelta(months=months)

    def save(self, *args, **kwargs):
        """
        Smart initialization:
        - Always use starting_billing_month as anchor if set.
        - Ensure next_payment_date is correctly initialized.
        """
        if not self.next_payment_date:
            if self.starting_billing_month:
                self.next_payment_date = self.starting_billing_month
            else:
                # Start billing from today instead of skipping a cycle
                self.next_payment_date = date.today()
        super().save(*args, **kwargs)

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    model_name = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    changes = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)
