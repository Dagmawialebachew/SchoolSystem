from django.db import models
from django.conf import settings
from students.models import Student # Assuming you have a Student model in a students app

class ParentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="parent_profile"
    )
    
    # Core contact fields
    # Use max_length=15 for phone number and enforce uniqueness
    phone_number = models.CharField(max_length=15, unique=True) 
    
    # Avatar/Image field
    # Requires Pillow library: pip install Pillow
    avatar = models.ImageField(
        upload_to='parents/avatars/', 
        null=True, 
        blank=True,
        verbose_name="Profile Picture"
    )

    # Telegram Notification Fields
    # The username field is usually just stored for display/reference, not unique.
    telegram_username = models.CharField(
        max_length=64, 
        blank=True, 
        null=True,
        help_text="Telegram @username for reference (e.g., @yourname)"
    )
    # The chat_id is the unique identifier used by the bot for notifications.
    telegram_chat_id = models.CharField(
        max_length=64, 
        blank=True, 
        null=True,
        unique=True, # Make this unique as it links one profile to one bot session
        help_text="Stores the unique Telegram chat ID once user connects."
    )
    
    # Relationship to Children
    children = models.ManyToManyField(
        "students.Student",
        related_name="parents",
        blank=True
    )

    class Meta:
        verbose_name = "Parent Profile"
        verbose_name_plural = "Parent Profiles"

    def __str__(self):
        return f"Profile for {self.user.get_full_name()} ({self.phone_number})"
