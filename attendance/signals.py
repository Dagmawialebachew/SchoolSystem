# attendance_app/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Attendance, AttendanceLog

@receiver(pre_save, sender=Attendance)
def attendance_pre_save_log(sender, instance: Attendance, **kwargs):
    if not instance.pk:
        return
    try:
        prev = Attendance.objects.get(pk=instance.pk)
    except Attendance.DoesNotExist:
        return
    if prev.status != instance.status or prev.remarks != instance.remarks:
        AttendanceLog.objects.create(
            attendance=instance,
            school = instance.school,
            previous_status=prev.status,
            new_status=instance.status,
            changed_by=getattr(instance, "marked_by", None),
            note=("Updated remarks" if prev.remarks != instance.remarks else None),
        )

@receiver(post_save, sender=Attendance)
def attendance_post_save_create(sender, instance: Attendance, created, **kwargs):
    if created:
        AttendanceLog.objects.create(
            attendance=instance,
            school = instance.school,
            previous_status=None,
            new_status=instance.status,
            changed_by=getattr(instance, "marked_by", None),
            note="Initial mark",
        )


# attendance/signals.py

from datetime import timedelta
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.formats import date_format

from .models import Attendance
from notifications.models import Announcement

logger = logging.getLogger(__name__)

# configuration in settings.py (with these defaults)
SINGLE_TTL     = getattr(settings, 'ATTENDANCE_SINGLE_TTL', 1)   # days to keep single‐event alerts
CONSEC_TTL     = getattr(settings, 'ATTENDANCE_CONSECUTIVE_TTL', 3)  # days to keep consecutive alerts
CONSEC_DAILY   = True   # we want a new “X days absent” alert each calendar day once consec>1

def send_sms(phone_number: str, message: str):
    """
    Stub SMS sender. Swap with your real provider (AfroMessages, Twilio, etc.)
    """
    try:
        # AfroMessages.send_sms(phone=phone_number, message=message)
        logger.debug(f"[SMS] to {phone_number}: {message}")
    except Exception:
        logger.exception("Failed to send SMS to %s", phone_number)


@receiver(pre_save, sender=Attendance)
def _cache_old_status(sender, instance, **kwargs):
    """
    Load previous status to fire only on real changes.
    """
    if instance.pk:
        try:
            instance._old_status = Attendance.objects.values_list('status', flat=True).get(pk=instance.pk)
        except Attendance.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Attendance)
def handle_attendance_notifications(sender, instance, created, **kwargs):
    """
    - Single-event absence/late/half-day alerts.
    - Dynamic consecutive-absence alerts for every day >=2.
    - 24h dedupe for each distinct “N days absent” title.
    - Immediate send_mail & send_sms.
    - In-app Announcement with TTL, priority, channels.
    """
    old_status = getattr(instance, '_old_status', None)
    new_status = instance.status

    # only on create or actual status-change
    if not created and old_status == new_status:
        return

    student      = instance.student
    parent_email = getattr(student, 'parent_email', None)
    parent_phone = getattr(student, 'parent_phone', None)
    school       = instance.class_program.school
    actor        = instance.marked_by
    now          = timezone.now()
    when_str     = date_format(instance.date, "DATE_FORMAT")  # locale‐aware date

    def make_announcement(title, message, ttl_days, priority, channels):
        try:
            Announcement.objects.create(
                school=school,
                title=title,
                category = 'ATTENDANCE',
                message=message,
                target='PARENTS',
                created_by=actor,
                publish_at=now,
                expires_at=now + timedelta(days=ttl_days),
                pinned=False,
                priority=priority,
                delivery_channels=channels,
            )
        except Exception:
            logger.exception("Failed to create Announcement: %s", title)

    def already_sent(title):
        window = now - timedelta(hours=24)
        return Announcement.objects.filter(
            school=school,
            created_by=actor,
            title=title,
            publish_at__gte=window
        ).exists()

    # ――― Single-event alerts ―――
    if new_status in ('ABSENT', 'LATE', 'HALF_DAY'):
        key = f"{student.pk}-{new_status}-{instance.date}"
        title = f"{student.full_name} marked {new_status.lower().capitalize()}"
        if not already_sent(key):
            msg = (
                f"Dear Parent,\n\n"
                f"{student.full_name} was marked {new_status.lower()} on {when_str}.\n\n"
                "Please contact the school if you have any questions."
            )
            channels = ['DASH']  # always in-app
            if parent_email: channels.append('EMAIL')
            if parent_phone: channels.append('SMS')

            prio = 'INFO' if new_status == 'HALF_DAY' else 'IMPORTANT'
            make_announcement(title, msg, SINGLE_TTL, prio, channels)

            if parent_email:
                try:
                    send_mail(title, msg, settings.DEFAULT_FROM_EMAIL, [parent_email], fail_silently=False)
                except Exception:
                    logger.exception("Failed send_mail to %s", parent_email)

            if parent_phone:
                send_sms(parent_phone, msg)

    # ――― Consecutive-absence alerts ―――
    if new_status == 'ABSENT':
        # gather last N days of logs, where N is count of consecutive absences
        logs = (
            Attendance.objects
            .filter(student=student)
            .order_by('-date', '-id')
        )
        consec = 0
        for log in logs:
            if log.status == 'ABSENT':
                consec += 1
            else:
                break

        # for day ≥2, send a “X days absent” alert once per day
        if consec > 1:
            title = f"{student.full_name} absent {consec} days"
            if not already_sent(title):
                msg = (
                    f"Dear Parent,\n\n"
                    f"{student.full_name} has now been absent {consec} consecutive days "
                    f"(last on {when_str}).\n\n"
                    "Please reach out to the school if your child will not return."
                )
                channels = ['DASH']
                if parent_email: channels.append('EMAIL')
                if parent_phone: channels.append('SMS')

                make_announcement(title, msg, CONSEC_TTL, 'URGENT', channels)

                if parent_email:
                    try:
                        send_mail(title, msg, settings.DEFAULT_FROM_EMAIL, [parent_email], fail_silently=False)
                    except Exception:
                        logger.exception("Failed send_mail for consecutive alert to %s", parent_email)

                if parent_phone:
                    send_sms(parent_phone, msg)

    # ――― Debug / Audit log ―――
    logger.debug(
        "AttendanceSignal | %s | %s → %s | consec=%s",
        student.full_name,
        old_status,
        new_status,
        locals().get('consec', 0)
    )
