from django.db import models
from django.conf import settings
from django.utils import timezone
from students.models import Student
from decimal import Decimal

class FeeStructure(models.Model):
    TUITION = "TUITION"
    TRANSPORT = "TRANSPORT"
    REGISTRATION = "REGISTRATION"
    OTHER = "OTHER"

    FEE_TYPES = [
    (TUITION, "Tuition"),
    (TRANSPORT, "Transport"),
    (REGISTRATION, "Registration"),
    (OTHER, "Other"),
]

    school = models.ForeignKey("schools.School", on_delete=models.CASCADE)
    name = models.CharField(max_length=20, choices=FEE_TYPES, default='TUITION')  # required
    division = models.ForeignKey(
        "classes_app.Division", on_delete=models.CASCADE, blank=True, null=True
    )  # optional, per-division fee
    class_program = models.ForeignKey(
        "classes_app.ClassProgram", on_delete=models.CASCADE, blank=True, null=True
    )  # optional, per-class fee
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)  # optional for OTHER
    in_progress = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("school", "name", "division", "class_program")

    def __str__(self):
        parts = [self.get_name_display()]
        if self.division:
            parts.append(str(self.division))
        if self.class_program:
            parts.append(str(self.class_program))
        return " - ".join(parts)
    
    def is_recurring(self) -> bool:
        return self.name != self.REGISTRATION


# ----------------------
#  INVOICE MANAGER
# ----------------------
class InvoiceQuerySet(models.QuerySet):
    def for_user(self, user):
        if user.is_superuser or getattr(user, "role", None) == "SUPER_ADMIN":
            return self
        if getattr(user, "role", None) == "SCHOOL_ADMIN":
            return self.filter(school=user.school)
        if getattr(user, "role", None) == "TEACHER":
            # teacher's invoices are linked via ClassProgram → Teacher → User
            return self.filter(student__classprogram__teacher__user=user)
        if getattr(user, "role", None) == "PARENT":
            # assuming Student has a `parent_phone` field you want to match
            return self.filter(student__parent_phone=user.phone)
        # If you add a "STUDENT" role later
        if getattr(user, "role", None) == "STUDENT":
            return self.filter(student__user=user)
        return self.none()


class InvoiceManager(models.Manager):
    def get_queryset(self):
        return InvoiceQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)


class Invoice(models.Model):
    STATUS_CHOICES = [
        ("UNPAID", "Unpaid"),
        ("PARTIAL", "Partial"),
        ("PAID", "Paid"),
    ]

    school = models.ForeignKey(
        "schools.School", on_delete=models.CASCADE, related_name="invoices"
    )
    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="invoices"
    )
    fee = models.ForeignKey(
        "fees.FeeStructure", on_delete=models.CASCADE, related_name="invoices",
    null=True, 
        blank = True
    )

    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="UNPAID"
    )

    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    # 🔥 Helps track billing cycles (e.g., "This invoice is for September 2025")
    billing_month = models.DateField(
        help_text="The month this invoice is for", null=True, blank=True
    )

    objects = InvoiceManager()  # Default manager

    class Meta:
        db_table = "invoices_invoice"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice #{self.id} - {self.student.full_name} - {self.status}"

    # -------------------
    # 🔥 PAY METHOD
    # -------------------
    def pay(self, amount: Decimal):
        """
        Register a payment for this invoice and update status.
        Also update the student's next payment date if fully paid.
        """
        self.amount_paid += Decimal(amount)

        if self.amount_paid >= self.amount_due:
            self.status = "PAID"
            # Update student payment details
            self.student.payment_status = "PAID"
            self.student.next_payment_date = self.student.calculate_next_payment_date()
            self.student.save()
        elif self.amount_paid > 0:
            self.status = "PARTIAL"
            self.student.payment_status = "PENDING"
            self.student.save()
        else:
            self.status = "UNPAID"
            self.student.payment_status = "OVERDUE"
            self.student.save()

        self.save()

    # -------------------
    # 🔥 UTILITY METHODS
    # -------------------
    @property
    def balance(self):
        """How much is left to pay."""
        return self.amount_due - self.amount_paid

    def is_overdue(self):
        """Check if the invoice is overdue."""
        return self.status != "PAID" and timezone.now().date() > self.due_date


# ----------------------
#  PAYMENT MANAGER
# ----------------------
class PaymentQuerySet(models.QuerySet):
    def for_user(self, user):
        if user.is_superuser or getattr(user, "role", None) == "admin":
            return self
        if getattr(user, "role", None) == "school_admin":
            return self.filter(school=user.school)
        if getattr(user, "role", None) == "teacher":
            return self.filter(invoice__student__classprogram__teacher__user=user)
        if getattr(user, "role", None) == "parent":
            return self.filter(invoice__student__parent_phone=user.phone)
        if getattr(user, "role", None) == "student":
            return self.filter(invoice__student__user=user)
        return self.none()


class PaymentManager(models.Manager):
    def get_queryset(self):
        return PaymentQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)


# payments/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone

class Payment(models.Model):
    STATUS_PENDING = "PENDING"       # sent to provider / awaiting provider confirmation
    STATUS_UNCONFIRMED = "UNCONFIRMED" # bank transfer uploaded, awaiting staff review
    STATUS_CONFIRMED = "CONFIRMED"   # verified / reconciled
    STATUS_REVERSED = "REVERSED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_UNCONFIRMED, "Unconfirmed"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_REVERSED, "Reversed"),
        (STATUS_REJECTED, "Rejected"),
    ]

    RECEIPT_CHOICES = [
        ('single', 'Single receipt for all invoices'),
        ('separate', 'Separate receipt for each invoice'),
        ('none', 'No receipt'),
    ]

    school = models.ForeignKey("schools.School", on_delete=models.CASCADE)
    invoice = models.ForeignKey("Invoice", on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_on = models.DateTimeField(default=timezone.now)
    method = models.CharField(max_length=50, default="Cash")
    provider = models.CharField(max_length=50, blank=True, null=True)  # e.g., TeleBirr, M-Pesa
    external_transaction_id = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    receipt_type = models.CharField(max_length=20, choices=RECEIPT_CHOICES, default='single')
    receipt_file = models.FileField(upload_to="payment_receipts/%Y/%m/%d/", blank=True, null=True)
    is_reversed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    received_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name="payments_received")
    paid_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name="payments_made")
    confirmed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name="payments_confirmed")
    confirmed_at = models.DateTimeField(blank=True, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True,
                                 help_text="Bank transfer ID, MPesa code, TeleBirr transaction ID, or internal ref")

    objects = PaymentManager()  # keep your manager

    def mark_confirmed(self, by_user=None):
        self.status = self.STATUS_CONFIRMED
        self.confirmed_by = by_user
        self.confirmed_at = timezone.now()
        self.save(update_fields=['status','confirmed_by','confirmed_at'])


class PaymentReversal(models.Model):
    payment = models.ForeignKey('Payment', on_delete=models.CASCADE, related_name='reversals')
    reversed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    reason = models.TextField(blank=True, null=True, default="Reversal requested by accountant")
    reversed_on = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Reversal of Payment #{self.payment.id} by {self.reversed_by}"
    
    

