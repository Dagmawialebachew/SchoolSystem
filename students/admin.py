from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('school', 'parent_name', 'payment_status', 'registration_date')
    list_filter = ('school', 'payment_status', 'registration_date')
    search_fields = ('parent_name', 'parent_phone')
    date_hierarchy = 'registration_date'