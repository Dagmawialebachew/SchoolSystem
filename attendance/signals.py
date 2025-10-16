# attendance/signals.py

from datetime import timedelta
import logging
import requests

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.formats import date_format

from .models import Attendance
from notifications.models import Announcement
from schools.models import School

logger = logging.getLogger(__name__)

# Config (override in settings.py if needed)
SINGLE_TTL   = getattr(settings, 'ATTENDANCE_SINGLE_TTL', 1)   # days for single-event alerts
CONSEC_TTL   = getattr(settings, 'ATTENDANCE_CONSECUTIVE_TTL', 3)  # days for consecutive alerts

def send_sms(phone_number: str, message: str):
    """Stub SMS sender. Replace with your provider (AfroMessages, Twilio, etc.)."""
    try:
        logger.debug(f"[SMS] to {phone_number}: {message}")
    except Exception:
        logger.exception("Failed to send SMS to %s", phone_number)

@receiver(pre_save, sender=Attendance)
def _cache_old_status(sender, instance, **kwargs):
    """Cache previous status so we can detect real changes on save."""
    if instance.pk:
        try:
            instance._old_status = Attendance.objects.values_list("status", flat=True).get(pk=instance.pk)
        except Attendance.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Attendance)
def handle_attendance_notifications(sender, instance, created, **kwargs):
    """
    - Single-event alerts: ABSENT, LATE, HALF_DAY (personalized per parent).
    - Correction alerts when status changes (old_status != new_status).
    - Consecutive-absence alerts (2+ ABSENT in a row).
    - 24h dedupe by announcement title.
    - Immediate EMAIL, SMS, Telegram, and in-app Announcement.
    """
    old_status = getattr(instance, "_old_status", None)
    new_status = instance.status

    student   = instance.student
    school    = instance.class_program.school
    actor     = instance.marked_by
    now       = timezone.now()
    when_str  = date_format(instance.date, "DATE_FORMAT")

    parent_email = getattr(student, "parent_email", None)
    parent_phone = getattr(student, "parent_phone", None)

    # Pull parent chat IDs safely (no formatting issues in Telegram)
    telegram_chat_ids = student.parents.filter(
        telegram_chat_id__isnull=False
    ).values_list("telegram_chat_id", flat=True).distinct()

    def make_announcement(title, message, ttl_days, priority, channels):
        try:
            Announcement.objects.create(
                school=school,
                title=title,
                category="ATTENDANCE",
                message=message,
                target="PARENTS",
                created_by=actor,
                publish_at=now,
                expires_at=now + timedelta(days=ttl_days),
                pinned=False,
                priority=priority,
                delivery_channels=channels,
            )
        except Exception:
            logger.exception("Failed to create Announcement: %s", title)

    def already_sent(title: str) -> bool:
        """Dedupe by announcement title within the last 24h."""
        window = now - timedelta(hours=24)
        return Announcement.objects.filter(
            school=school,
            created_by=actor,
            title=title,
            publish_at__gte=window,
        ).exists()

    # ――― Correction/update alert (e.g., ABSENT → PRESENT) ―――
    if not created and old_status is not None and old_status != new_status:
        title = f"{student.full_name} attendance updated"
        msg = (
            f"Dear Parent,\n\n"
            f"{student.full_name}'s attendance status for {when_str} "
            f"was updated from {old_status.lower()} to {new_status.lower()}.\n\n"
            "Please note this correction."
        )
        # Send to Telegram (all parents), Email, and SMS
        for chat_id in telegram_chat_ids:
            send_telegram_message(school, chat_id, msg)
        if parent_email:
            try:
                send_mail(title, msg, settings.DEFAULT_FROM_EMAIL, [parent_email], fail_silently=False)
            except Exception:
                logger.exception("Failed send_mail to %s", parent_email)
        if parent_phone:
            send_sms(parent_phone, msg)

        # In-app announcement (no dedupe necessary for corrections)
        make_announcement(title, msg, SINGLE_TTL, "IMPORTANT", ["DASH"])

    # ――― Single-event alerts: ABSENT, LATE, HALF_DAY ―――
    if new_status in ("ABSENT", "LATE", "HALF_DAY"):
        title = f"{student.full_name} marked {new_status.lower().capitalize()}"
        if not already_sent(title):
            prio = "INFO" if new_status == "HALF_DAY" else "IMPORTANT"
            # Personalized per parent
            for parent in student.parents.all():
                parent_name = parent.user.get_full_name()
                msg = (
                    f"Dear Parent {parent_name},\n\n"
                    f"{student.full_name} was marked {new_status.lower()} on {when_str}.\n\n"
                    "Please contact the school if you have any questions."
                )
                channels = ["DASH"]
                if parent_email: channels.append("EMAIL")
                if parent_phone: channels.append("SMS")

                make_announcement(title, msg, SINGLE_TTL, prio, channels)

                if getattr(parent, "telegram_chat_id", None):
                    send_telegram_message(school, parent.telegram_chat_id, msg)
                if parent_email:
                    try:
                        send_mail(title, msg, settings.DEFAULT_FROM_EMAIL, [parent_email], fail_silently=False)
                    except Exception:
                        logger.exception("Failed send_mail to %s", parent_email)
                if parent_phone:
                    send_sms(parent_phone, msg)

    # ――― Consecutive-absence escalation (2+ days ABSENT) ―――
    if new_status == "ABSENT":
        logs = Attendance.objects.filter(student=student).order_by("-date", "-id")
        consec = 0
        for log in logs:
            if log.status == "ABSENT":
                consec += 1
            else:
                break

        if consec > 1:
            title = f"{student.full_name} absent {consec} days"
            if not already_sent(title):
                msg = (
                    f"Dear Parent,\n\n"
                    f"{student.full_name} has now been absent {consec} consecutive days "
                    f"(last on {when_str}).\n\n"
                    "Please reach out to the school if your child will not return."
                )
                channels = ["DASH"]
                if parent_email: channels.append("EMAIL")
                if parent_phone: channels.append("SMS")

                make_announcement(title, msg, CONSEC_TTL, "URGENT", channels)

                for chat_id in telegram_chat_ids:
                    send_telegram_message(school, chat_id, msg)
                if parent_email:
                    try:
                        send_mail(title, msg, settings.DEFAULT_FROM_EMAIL, [parent_email], fail_silently=False)
                    except Exception:
                        logger.exception("Failed send_mail for consecutive alert to %s", parent_email)
                if parent_phone:
                    send_sms(parent_phone, msg)

    logger.debug(
        "AttendanceSignal | %s | %s → %s | consec=%s",
        student.full_name,
        old_status,
        new_status,
        locals().get("consec", 0),
    )

def send_telegram_message(school: School, chat_id: str, message: str):
    """Send a Telegram message to a specific chat_id using the school's bot token.
    Uses plain text (no parse_mode) to avoid Markdown/HTML parsing errors.
    """
    token = school.telegram_bot_token
    if not token:
        logger.warning(
            f"School '{school.name}' is missing a Telegram Bot Token. Message not sent to {chat_id}."
        )
        return

    TELEGRAM_API_URL = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        # Avoid parse_mode entirely to prevent "can't parse entities" errors.
        response = requests.post(
            TELEGRAM_API_URL,
            json={"chat_id": chat_id, "text": message},
            timeout=5,
        )
        if response.status_code != 200:
            logger.error(
                f"Failed to send Telegram message to {chat_id} (School: {school.name}). "
                f"Status: {response.status_code}, Response: {response.text}"
            )
        else:
            logger.debug(f"[TELEGRAM] Message sent to {chat_id} (School: {school.name}).")
    except requests.exceptions.RequestException:
        logger.exception("Failed to send Telegram message due to network error.")
