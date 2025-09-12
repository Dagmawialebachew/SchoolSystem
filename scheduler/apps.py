from django.apps import AppConfig
from django.db.models.signals import post_migrate


def start_scheduler(sender, **kwargs):
    """
    Start the APScheduler after all migrations have been applied.
    """
    from .jobs import create_daily_scheduler
    create_daily_scheduler()


class SchedulerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scheduler'

    def ready(self):
        # Connect the scheduler start function to the post_migrate signal
        post_migrate.connect(start_scheduler, sender=self)
