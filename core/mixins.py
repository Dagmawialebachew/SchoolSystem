from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.db.models import Q


class RoleRequiredMixin(LoginRequiredMixin):
    """Mixin to require specific user roles"""
    allowed_roles = []
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not self.allowed_roles:
            return super().dispatch(request, *args, **kwargs)
        
        user_role = request.user.role
        if user_role not in self.allowed_roles and not request.user.is_super_admin():
            raise PermissionDenied("You don't have permission to access this page.")
        
        return super().dispatch(request, *args, **kwargs)


class SchoolScopedMixin:
    """Mixin to automatically scope querysets by user's school"""
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Super admins see everything
        if self.request.user.is_super_admin():
            return queryset
        
        # Filter by user's school
        if hasattr(queryset.model, 'school'):
            return queryset.filter(school=self.request.user.school)
        
        return queryset
    
    def form_valid(self, form):
        """Automatically set school for new objects"""
        if hasattr(form.instance, 'school') and not form.instance.school:
            if not self.request.user.is_super_admin():
                form.instance.school = self.request.user.school
        return super().form_valid(form)


class ParentScopedMixin:
    """Mixin for parent users to see only their children's data"""
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        if self.request.user.is_parent():
            # Parents see only their children's data
            # This assumes a relationship between User and Student via parent_name/parent_phone
            return queryset.filter(
                Q(parent_name__icontains=self.request.user.get_full_name()) |
                Q(parent_phone=self.request.user.phone)
            )
        
        return queryset