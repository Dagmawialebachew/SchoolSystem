from django.core.exceptions import PermissionDenied


def user_is_super_admin(user):
    """Check if user is a super admin"""
    return user.is_authenticated and user.role == 'SUPER_ADMIN'


def user_is_school_admin(user):
    """Check if user is a school admin"""
    return user.is_authenticated and user.role == 'SCHOOL_ADMIN'


def user_is_teacher(user):
    """Check if user is a teacher"""
    return user.is_authenticated and user.role == 'TEACHER'


def user_is_parent(user):
    """Check if user is a parent"""
    return user.is_authenticated and user.role == 'PARENT'


def user_belongs_to_school(user, school):
    """Check if user belongs to the specified school"""
    if user_is_super_admin(user):
        return True
    return user.school == school


def require_super_admin(user):
    """Decorator helper to require super admin role"""
    if not user_is_super_admin(user):
        raise PermissionDenied("Super admin access required")


def require_school_admin(user):
    """Decorator helper to require school admin role"""
    if not (user_is_super_admin(user) or user_is_school_admin(user)):
        raise PermissionDenied("School admin access required")