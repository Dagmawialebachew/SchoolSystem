from django.contrib import admin
from .models import ClassProgram


@admin.register(ClassProgram)
class ClassProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'school')
    list_filter = ('school',)
    search_fields = ('name', 'description')
    filter_horizontal = ('teachers', 'students')