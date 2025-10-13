from django import forms
from django.contrib.auth import get_user_model
from .models import ParentProfile # Assuming this is the correct path

User = get_user_model()

class CombinedParentProfileForm(forms.Form):
    """
    A single form class to collect data for both the User model 
    and the ParentProfile model.
    """
    # Fields for the User Model (Name and Email)
    first_name = forms.CharField(max_length=150, required=True, label="First Name")
    last_name = forms.CharField(max_length=150, required=True, label="Last Name")
    email = forms.EmailField(required=True, label="Email Address", help_text="Used for login and notifications.")

    # Fields for the ParentProfile Model
    phone_number = forms.CharField(
        max_length=20, 
        required=True, 
        label="Phone Number",
        help_text="Your primary contact number."
    )
    telegram_username = forms.CharField(
        max_length=64, 
        required=False, 
        label="Telegram Username",
        help_text="Example: @yourusername (for push notifications)"
    )
    # Assuming 'avatar' is an ImageField on ParentProfile
    avatar = forms.ImageField(required=False, label="Profile Picture", help_text="Upload a new profile image.")
    avatar_clear = forms.BooleanField(required=False, label="Clear Profile Picture")


    def clean_email(self):
        """Custom clean method to ensure email uniqueness if changed."""
        email = self.cleaned_data.get('email')
        
        # Check if the email is already in use by another user
        if User.objects.exclude(pk=self.initial.get('user_pk')).filter(email__iexact=email).exists():
            raise forms.ValidationError("This email address is already registered by another user.")
        
        return email

    def __init__(self, *args, **kwargs):
        """Pass the user's PK to the form for unique checks."""
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.initial['user_pk'] = self.user.pk
