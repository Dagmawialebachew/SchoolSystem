from django.shortcuts import redirect
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
)
from django.views.generic.edit import CreateView
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.contrib import messages
from .models import User

from .forms import CustomLoginForm, CustomPasswordResetForm, CustomRegisterForm
from core.utilis import CleanUpOrphans
class CustomRegisterView(CreateView):
    model = User
    form_class = CustomRegisterForm
    template_name = "accounts/register.html"

    def form_valid(self, form):
        """Save user, log them in immediately, then redirect to onboarding."""
        user = form.save(commit=False)
        user.is_active = True       # ✅ allow login immediately
        user.is_verified = False       # ✅ still needs super admin approval
        user.save()

        login(self.request, user)      # ✅ auto-login after registration
        return redirect("onboarding:school_setup")  # ✅ go straight to onboarding

    def form_invalid(self, form):
        """Send validation errors as Django messages instead of just inline form errors."""
        for field, errors in form.errors.items():
            for error in errors:
                if field == "__all__":  
                    messages.error(self.request, error)  # general form errors
                else:
                    messages.error(self.request, f"{field.capitalize()}: {error}")
        return super().form_invalid(form)

class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = CustomLoginForm
    def form_valid(self, form):
        """Handle login based on verification and onboarding status."""
        user = form.get_user()

        # If user is not verified
        if not user.is_verified:
            if getattr(user, "has_completed_onboarding", False):
                messages.error(self.request, "Please first finish the onboarding process.")
            else:
                messages.error(self.request, "Your account is not yet verified by the Super Admin.")
            return redirect("accounts:pending_approval")
        
        login(self.request, user)
        messages.success(self.request, f"Welcome back, {user.username} 🎉")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        """Send validation errors as Django messages instead of just inline form errors."""
        for field, errors in form.errors.items():
            for error in errors:
                if field == "__all__":  
                    messages.error(self.request, error)  # general form errors
                else:
                    messages.error(self.request, f"{field.capitalize()}: {error}")

        return super().form_invalid(form)
        

    def get_success_url(self):
        """Role-based redirects."""
        user = self.request.user
        if hasattr(user, "is_super_admin") and user.is_super_admin():
            return reverse_lazy("admin:index")
        elif hasattr(user, "is_school_admin") and user.is_school_admin():
            return reverse_lazy("dashboard:dashboard")
        elif hasattr(user, "is_teacher") and user.is_teacher():
            return reverse_lazy("dashboard:teacher_dashboard")
        elif hasattr(user, "is_parent") and user.is_parent():
            return reverse_lazy("parents:dashboard")
        return reverse_lazy("dashboard")


class CustomLogoutView(LogoutView):
    """Allow logout via GET (not best practice, but user-friendly)."""
    next_page = reverse_lazy("dashboard:dashboard")

    def dispatch(self, request, *args, **kwargs):
        messages.success(request, "You have been logged out successfully 👋")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Override to allow GET requests for logout."""
        return self.post(request, *args, **kwargs)


class CustomPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.html"
    success_url = reverse_lazy("accounts:password_reset_done")
    form_class = CustomPasswordResetForm

    def form_valid(self, form):
        messages.info(
            self.request,
            "If that email is registered, you’ll receive reset instructions shortly 📩",
        )
        return super().form_valid(form)

from django.views.generic import TemplateView

class PendingApprovalView(TemplateView):
    template_name = "accounts/pending_approval.html"
