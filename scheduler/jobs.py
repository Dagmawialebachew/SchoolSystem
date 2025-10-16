# scheduler/jobs.py
import logging
from datetime import datetime
from django.db import transaction
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore, register_events

from schools.models import School
from fees.utilis import generate_invoices_for_school

logger = logging.getLogger(__name__)

def scheduled_generate_invoices():
    """
    Loop through all schools and generate invoices for each.
    """
    logger.info(f"🚀 Running scheduled invoice generation at {datetime.utcnow()} UTC")

    for school in School.objects.all():
        try:
            with transaction.atomic():
                count = generate_invoices_for_school(school)
            logger.info(f"🏫 {school.name}: Generated {count} invoices successfully.")
        except Exception as e:
            logger.error(f"❌ Error generating invoices for {school.name}: {e}", exc_info=True)


def create_daily_scheduler(timezone="UTC"):
    """
    Initialize and start APScheduler to run every midnight UTC (or custom timezone).
    """
    scheduler = BackgroundScheduler(timezone=timezone)

    # Use DjangoJobStore to persist jobs across restarts
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # Add daily invoice generation job at midnight
    scheduler.add_job(
        scheduled_generate_invoices,
        trigger=CronTrigger(hour=0, minute=0),
        id="generate_invoices_job",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
        coalesce=True,    # Merge missed runs if server was down
    )

    # Register job events for logging
    register_events(scheduler)

    # Start the scheduler in background
    scheduler.start()
    logger.info("✅ APScheduler started: daily invoice generation active.")



from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore, register_events
from django.utils import timezone
from decimal import Decimal
import logging

from schools.models import School
from students.models import Student
from fees.models import Invoice
from bot.utils import send_telegram_message

logger = logging.getLogger(__name__)


# ----------------------
#  HELPER FUNCTIONS
# ----------------------

def get_parent_invoices(parent, include_due_soon=True):
    """Get unpaid/partial invoices for a parent."""
    today = timezone.now().date()
    invoices = Invoice.objects.filter(
        student__parent_phone=parent.phone,
        status__in=["UNPAID", "PARTIAL"]
    ).order_by('due_date')

    if include_due_soon:
        # include invoices due today or in the next 3 days
        invoices = invoices.filter(due_date__lte=today + timezone.timedelta(days=3))

    return invoices


def format_invoice_message(invoice, school):
    """Create Telegram-friendly message with inline 'Pay Now' link."""
    overdue = invoice.is_overdue()
    status_emoji = "🔴" if overdue else "🟡" if invoice.status == "PARTIAL" else "🟢"

    pay_url = f"https://schoolsys.pythonanywhere.com/fees/{invoice.id}/process-payment/"

    return (
        f"{status_emoji} Invoice #{invoice.id} | Student: {invoice.student.full_name}\n"
        f"Amount Due: {invoice.balance}₮ | Due: {invoice.due_date} | Status: {invoice.status}\n"
        f"💳 [Pay Now]({pay_url})\n"
    )


def notify_parent_fees(parent):
    """Send fee notifications via Telegram for all children."""
    invoices = get_parent_invoices(parent)
    if not invoices.exists():
        return

    message = f"📢 Fee Reminder for {parent.full_name}\n\n"
    for invoice in invoices:
        message += format_invoice_message(invoice, invoice.school) + "\n"

    chat_id = parent.telegram_chat_id
    if not chat_id:
        logger.warning(f"No Telegram chat_id for parent {parent.id}")
        return

    send_telegram_message(invoice.school, chat_id, message)
    logger.info(f"Fee notification sent to parent {parent.id} ({parent.full_name})")


# ----------------------
#  SCHEDULED JOB
# ----------------------

def scheduled_fee_notifications():
    """Loop through schools and parents to notify unpaid/partial invoices."""
    logger.info(f"🚀 Running scheduled fee notifications: {timezone.now()}")

    for school in School.objects.all():
        # Get all parents with a Telegram chat_id
        parents = school.parents.filter(telegram_chat_id__isnull=False)
        for parent in parents:
            try:
                notify_parent_fees(parent)
            except Exception as e:
                logger.exception(f"Error sending fee notification to parent {parent.id}: {e}")


# ----------------------
#  SCHEDULER INITIALIZATION
# ----------------------

def create_fee_scheduler():
    """Initialize APScheduler for fee notifications."""
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # Daily reminders at 8 AM UTC
    scheduler.add_job(
        scheduled_fee_notifications,
        trigger=CronTrigger(hour=8, minute=0),
        id="daily_fee_notifications",
        replace_existing=True,
    )

    # Optional: Midday reminder at 12 PM UTC
    scheduler.add_job(
        scheduled_fee_notifications,
        trigger=CronTrigger(hour=12, minute=0),
        id="midday_fee_notifications",
        replace_existing=True,
    )

    register_events(scheduler)
    scheduler.start()
    logger.info("✅ Fee notification scheduler started.")
