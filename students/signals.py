import re
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from parents.models import ParentProfile
from .models import Student
from parents.services import send_parent_credentials

User = get_user_model()

def normalize_phone(phone: str) -> str:
    cleaned = re.sub(r"[^\d+]", "", phone or "")
    if cleaned.startswith("0"):
        cleaned = "+251" + cleaned[1:]
    return cleaned

@receiver(post_save, sender=Student)
def ensure_parent_account(sender, instance, created, **kwargs):
    if not created or not instance.parent_phone:
        return

    phone = normalize_phone(instance.parent_phone)
    name = (instance.parent_name or "").strip()
    # Link to existing
    profile = ParentProfile.objects.filter(phone_number=phone).first()
    if profile:
        profile.children.add(instance)
        return

    # Create new parent user
    parts = name.split()
    first_name = parts[0] if parts else ""
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    user = User.objects.create_user(
        username=phone,
        password="1234",
        role="PARENT",
        first_name=first_name,
        last_name=last_name,
        school=instance.school,
    )
    profile = ParentProfile.objects.create(user=user, phone_number=phone)
    profile.children.add(instance)
    bot_token = instance.school.telegram_bot_tokeny

    # Send credentials via QR/Telegram
    try:
        from parents.services import send_parent_credentials
        send_parent_credentials(profile, login_url="/accounts/login/", bot_token = bot_token )
    except ImportError:
        pass
