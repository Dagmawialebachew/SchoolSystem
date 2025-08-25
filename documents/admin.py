from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('file', 'doc_type', 'assigned_student', 'assigned_class', 'uploaded_by', 'school')
    list_filter = ('school', 'doc_type', 'uploaded_at')
    search_fields = ('file', 'assigned_student__first_name', 'assigned_student__last_name')
    date_hierarchy = 'uploaded_at'