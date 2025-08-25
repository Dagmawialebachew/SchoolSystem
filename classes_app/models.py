from django.db import models
from core.models import SchoolOwnedModel


class ClassProgram(SchoolOwnedModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    teachers = models.ManyToManyField('teachers.Teacher', blank=True)
    students = models.ManyToManyField('students.Student', blank=True)
    
    class Meta:
        db_table = 'classes_classProgram'
        ordering = ['name']
    
    def __str__(self):
        return self.name