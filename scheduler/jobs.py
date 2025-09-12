from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore, register_events

from schools.models import School
from fees.utilis import generate_invoices_for_school


def scheduled_generate_invoices():
    """
    Loop through all schools and generate invoices for each.
    """
    from datetime import datetime
    print(f"🚀 Running scheduled invoice generation: {datetime.now()}")

    for school in School.objects.all():
        count = generate_invoices_for_school(school)
        print(f"🏫 {school.name}: Generated {count} invoices.")


def create_daily_scheduler():
    """
    Initialize and start APScheduler to run every midnight UTC.
    """
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_jobstore(DjangoJobStore(), "default")

    scheduler.add_job(
        scheduled_generate_invoices,
        trigger=CronTrigger(hour=0, minute=0),  # Midnight daily
        id="generate_invoices_job",
        replace_existing=True,
    )

    register_events(scheduler)
    scheduler.start()
    print("✅ Scheduler started and running.")
