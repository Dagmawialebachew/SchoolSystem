from django.contrib import admin
from .models import FeeStructure, Invoice, Payment
from django.utils.html import format_html



@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'division_display',
        'amount',
        'school',
        'in_progress',
        'created_at'
    )
    list_filter = ('school', 'division', 'in_progress')
    search_fields = ('name', 'division__name', 'school__name')
    ordering = ('school', 'division', 'name')
    list_editable = ('amount',)
    list_per_page = 20

    fieldsets = (
        ("Fee Details", {
            "fields": ("school", "division", "name", "amount", "description")
        }),
        ("Status", {
            "fields": ("in_progress", "created_at"),
        }),
    )
    readonly_fields = ('created_at',)

    def division_display(self, obj):
        return obj.division.name if obj.division else "-"
    division_display.short_description = "Division"

    def amount_display(self, obj):
        return f"${obj.amount:,.2f}" if obj.amount is not None else "-"
    amount_display.short_description = "Amount"

    def in_progress_display(self, obj):
        color = "red" if obj.in_progress else "green"
        status = "Pending" if obj.in_progress else "Complete"
        return format_html('<span style="color: {};">{}</span>', color, status)
    in_progress_display.short_description = "Status"


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('student', 'fee', 'amount_due', 'amount_paid', 'status', 'due_date', 'school')
    list_filter = ('school', 'status', 'due_date')
    search_fields = ('student__first_name', 'student__last_name', 'fee__name')
    date_hierarchy = 'due_date'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "method", "reference", "paid_on")
    search_fields = ("invoice__student__first_name", "invoice__student__last_name", "reference")
