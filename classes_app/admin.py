from django.contrib import admin
from .models import ClassProgram, Division, Subject, ClassSubjectAssignment

admin.site.register(Division)
admin.site.register(Subject)
admin.site.register(ClassSubjectAssignment)
@admin.register(ClassProgram)
class ClassProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "division", "teacher", "schedule")
    list_filter = ("division", "teacher")
    search_fields = ("name", "division__name", "teacher__user__first_name", "teacher__user__last_name")
