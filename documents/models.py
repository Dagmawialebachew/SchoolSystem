from django.db import models
from core.models import SchoolOwnedModel


class Document(SchoolOwnedModel):
    DOC_TYPE_CHOICES = [
        ('CERTIFICATE', 'Certificate'),
        ('REPORT', 'Report'),
        ('POLICY', 'Policy'),
        ('OTHER', 'Other'),
    ]
    
    file = models.FileField(upload_to='documents/')
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    assigned_student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    assigned_class = models.ForeignKey(
        'classes_app.ClassProgram',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'documents_document'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.doc_type} - {self.file.name}"