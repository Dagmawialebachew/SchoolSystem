# scheduler/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def start_scheduler(sender, **kwargs):
    """
    Start APScheduler after all migrations have been applied.
    Ensures single instance per process.
    """
    # Prevent duplicate scheduler start in same process
    if getattr(start_scheduler, "already_started", False):
        return
    start_scheduler.already_started = True

    # Optionally skip scheduler in development
    if settings.DEBUG:
        logger.info("⚠️ APScheduler skipped in DEBUG mode.")
        return

    try:
        from .jobs import create_daily_scheduler
        create_daily_scheduler()  # Starts the background scheduler
        logger.info("✅ APScheduler started: daily invoice generation active.")
    except Exception as e:
        logger.error(f"❌ Failed to start APScheduler: {e}", exc_info=True)

class SchedulerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scheduler'

    def ready(self):
        # Connect scheduler start to post_migrate signal
        post_migrate.connect(start_scheduler, sender=self)
