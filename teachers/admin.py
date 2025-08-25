from django.contrib import admin
from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'school', 'phone', 'is_active')
    list_filter = ('school', 'is_active')
    search_fields = ('first_name', 'last_name', 'phone')