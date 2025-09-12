from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from schools.models import School

class Command(BaseCommand):
    help = "Deletes orphaned schools created during onboarding more than 2 minutes ago."

    def handle(self, *args, **kwargs):
        cutoff = timezone.now() - timedelta(minutes=2)
        orphaned_schools = School.objects.filter(in_progress=True, created_at__lt=cutoff)

        if orphaned_schools.exists():
            self.stdout.write(f"Deleting {orphaned_schools.count()} orphaned schools:")
            for school in orphaned_schools:
                self.stdout.write(f" - ID: {school.id}, Name: {school.name}, Created: {school.created_at}")
            orphaned_schools.delete()
        else:
            self.stdout.write("No orphaned schools found.")
