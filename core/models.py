from django.db import models
from django.core.exceptions import ValidationError


class SchoolOwnedQuerySet(models.QuerySet):
    def for_user(self, user):
        """Filter queryset by user's school unless user is super admin"""
        if user.is_super_admin():
            return self
        elif user.school:
            return self.filter(school=user.school)
        else:
            return self.none()


class SchoolOwnedManager(models.Manager):
    def get_queryset(self):
        return SchoolOwnedQuerySet(self.model, using=self._db)
    
    def for_user(self, user):
        return self.get_queryset().for_user(user)


class SchoolOwnedModel(models.Model):
    """Abstract base class for models that belong to a specific school"""
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='%(class)s_set'
    )
    
    objects = SchoolOwnedManager()
    
    class Meta:
        abstract = True
    
    def clean(self):
        super().clean()
        # Add validation logic if needed
        pass