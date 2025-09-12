from django.utils.deprecation import MiddlewareMixin

print('this is runnign just one ')
class SchoolTenancyMiddleware(MiddlewareMixin):
    """Middleware to attach current user to request and handle school filtering"""
    
    def process_request(self, request):
        # Attach current user for easy access in views
        request.current_user = getattr(request, 'user', None)
        
        # Add helper methods to request
        request.user_is_super_admin = lambda: (
            request.user.is_authenticated and request.user.role == 'SUPER_ADMIN'
        )
        request.user_is_school_admin = lambda: (
            request.user.is_authenticated and request.user.role == 'SCHOOL_ADMIN'
        )
        request.user_is_teacher = lambda: (
            request.user.is_authenticated and request.user.role == 'TEACHER'
        )
        request.user_is_parent = lambda: (
            request.user.is_authenticated and request.user.role == 'PARENT'
        )
        
        return None