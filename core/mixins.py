# mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Q
from .utilis import CleanUpOrphans


class RoleRequiredMixin(LoginRequiredMixin):
    """
    Restrict access to users with specific roles.
    Example usage in view:
        allowed_roles = ["SUPER_ADMIN", "SCHOOL_ADMIN", "ACCOUNTANT"]
    """
    allowed_roles = []
    CleanUpOrphans()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission("You must be logged in to access this page.")

        # If no allowed_roles specified, allow all authenticated users
        if not self.allowed_roles:
            return super().dispatch(request, *args, **kwargs)

        # Check role helpers
        user = request.user
        if user.is_super_admin() or user.role in self.allowed_roles:
            return super().dispatch(request, *args, **kwargs)

        return self.handle_no_permission("Access denied. You don't have permission to view this page.")

    def handle_no_permission(self, message=None):
        if message:
            messages.error(self.request, message)
        return redirect(self.request.META.get('HTTP_REFERER', '/'))


class UserScopedMixin:
    """
    Combined scoping for querysets based on user roles.
    - Super admins: see all records
    - School-based users: see only their school
    - Parents: see only their children
    Also automatically sets school on form save for school-based users.
    """
    def get_school(self):
        if self.request.user.is_super_admin():
            return None
        return getattr(self.request.user, "school", None)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Super admin sees all
        if user.is_super_admin():
            return queryset

        # Parent sees only their children
        # if user.is_parent():
        #     return queryset.filter(
        #         Q(student__parent_name__icontains=user.get_full_name()) |
        #         Q(student__parent_phone=user.phone) | Q()
        #     )

        # School-based users filter by their school
        if hasattr(queryset.model, 'school'):
            return queryset.filter(school=self.get_school())

        return queryset

    def form_valid(self, form):
        """
        Automatically assign school on creation/update if model has school field.
        """
        if hasattr(form, "instance") and hasattr(form.instance, "school"):
            if not form.instance.school and not self.request.user.is_super_admin():
                form.instance.school = self.get_school()
        return super().form_valid(form)

