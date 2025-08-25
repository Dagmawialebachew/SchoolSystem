from django.shortcuts import redirect
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.contrib import messages


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    
    def get_success_url(self):
        user = self.request.user
        if user.is_super_admin():
            return '/admin/'
        elif user.is_school_admin():
            return '/dashboard/'
        elif user.is_teacher():
            return '/teacher-dashboard/'
        elif user.is_parent():
            return '/parent-dashboard/'
        else:
            return '/dashboard/'


class CustomLogoutView(LogoutView):
    next_page = '/'
    
    def dispatch(self, request, *args, **kwargs):
        messages.success(request, 'You have been logged out successfully.')
        return super().dispatch(request, *args, **kwargs)


class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    success_url = reverse_lazy('accounts:password_reset_done')