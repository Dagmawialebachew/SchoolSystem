from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserCreationForm,
    PasswordResetForm,
    SetPasswordForm,
)
from .models import User


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your username",
                "class": "w-full pl-10 pr-3 py-2 border border-neutral-300 rounded-lg "
                         "focus:ring-2 focus:ring-primary-500 focus:border-primary-500 "
                         "text-neutral-900 placeholder-neutral-400 text-sm"
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter your password",
                "class": "w-full pl-10 pr-3 py-2 border border-neutral-300 rounded-lg "
                         "focus:ring-2 focus:ring-primary-500 focus:border-primary-500 "
                         "text-neutral-900 placeholder-neutral-400 text-sm"
            }
        )
    )


class CustomRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email", "phone", "role", "password1", "password2"]

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "w-full pl-10 pr-3 py-2 border border-neutral-300 rounded-lg "
                             "focus:ring-2 focus:ring-primary-500 focus:border-primary-500 "
                             "text-neutral-900 placeholder-neutral-400 text-sm",
                    "placeholder": "Choose a username",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full pl-10 pr-3 py-2 border border-neutral-300 rounded-lg "
                             "focus:ring-2 focus:ring-primary-500 focus:border-primary-500 "
                             "text-neutral-900 placeholder-neutral-400 text-sm",
                    "placeholder": "Enter your email",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "w-full pl-10 pr-3 py-2 border border-neutral-300 rounded-lg "
                             "focus:ring-2 focus:ring-primary-500 focus:border-primary-500 "
                             "text-neutral-900 placeholder-neutral-400 text-sm",
                    "placeholder": "Enter your phone number",
                }
            ),
            "role": forms.Select(
                attrs={
                    "class": "w-full pl-10 pr-3 py-2 border border-neutral-300 rounded-lg "
                             "focus:ring-2 focus:ring-primary-500 focus:border-primary-500 "
                             "text-neutral-900 text-sm appearance-none",
                }
            ),
            
        }

    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full pl-10 pr-3 py-2 border border-neutral-300 rounded-lg "
                         "focus:ring-2 focus:ring-primary-500 focus:border-primary-500 "
                         "text-neutral-900 placeholder-neutral-400 text-sm",
                "placeholder": "Create a password",
            }
        )
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full pl-10 pr-3 py-2 border border-neutral-300 rounded-lg "
                         "focus:ring-2 focus:ring-primary-500 focus:border-primary-500 "
                         "text-neutral-900 placeholder-neutral-400 text-sm",
                "placeholder": "Confirm your password",
            }
        )
    )
    def clean_role(self):
        role = self.cleaned_data.get("role")
        if role == "SUPER_ADMIN":
            raise forms.ValidationError("You cannot register as Super Admin.")
        return role

class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Enter your account email",
                "class": "w-full px-3 py-2 border border-neutral-300 rounded-lg "
                         "focus:ring-2 focus:ring-primary-500 focus:border-primary-500 "
                         "text-neutral-900 placeholder-neutral-400 text-sm"
            }
        )
    )


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter new password",
                "class": "w-full px-3 py-2 border border-neutral-300 rounded-lg "
                         "focus:ring-2 focus:ring-primary-500 focus:border-primary-500 "
                         "text-neutral-900 placeholder-neutral-400 text-sm"
            }
        )
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm new password",
                "class": "w-full px-3 py-2 border border-neutral-300 rounded-lg "
                         "focus:ring-2 focus:ring-primary-500 focus:border-primary-500 "
                         "text-neutral-900 placeholder-neutral-400 text-sm"
            }
        )
    )
