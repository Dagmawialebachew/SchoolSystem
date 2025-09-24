from django.contrib import admin
from django.utils.html import format_html
from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    # Columns to show in the list view
    list_display = ('full_name', 'school', 'phone', 'employment_status_badge', 'is_active_badge')
    
    # Filters on the right sidebar
    list_filter = ('school', 'is_active', 'employment_status')
    
    # Searchable fields
    search_fields = ('first_name', 'last_name', 'phone', 'email')
    
    # Enable sorting by specific fields
    ordering = ('last_name', 'first_name')
    
    
    # Add some badges for better visibility
    def is_active_badge(self, obj):
        color = 'green' if obj.is_active else 'red'
        status = 'Active' if obj.is_active else 'Inactive'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status
        )
    is_active_badge.short_description = 'Active Status'
    is_active_badge.admin_order_field = 'is_active'

    def employment_status_badge(self, obj):
        color_map = {
            'FULL_TIME': 'green',
            'PART_TIME': 'orange',
            'CONTRACT': 'blue'
        }
        color = color_map.get(obj.employment_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_employment_status_display()
        )
    employment_status_badge.short_description = 'Employment Status'
    employment_status_badge.admin_order_field = 'employment_status'
