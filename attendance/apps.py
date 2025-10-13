# attendance_app/apps.py
from django.apps import AppConfig

class AttendanceAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "attendance"

    def ready(self):
        from . import signals  # noqa
