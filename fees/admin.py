from django.contrib import admin
from .models import FeeType, Payment


@admin.register(FeeType)
class FeeTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'school')
    list_filter = ('school',)
    search_fields = ('name',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'fee_type', 'amount', 'status', 'due_date', 'school')
    list_filter = ('school', 'status', 'payment_method', 'due_date')
    search_fields = ('student__first_name', 'student__last_name', 'fee_type__name')
    date_hierarchy = 'due_date'