from django.utils import timezone
from datetime import timedelta
from schools.models import School

def CleanUpOrphans():
    cutoff = timezone.now() - timedelta(hours=2)
    try:
        orphaned_schools = School.objects.filter(in_progress=True, created_at__lt=cutoff)
        if orphaned_schools.exists():
            print(f"Deleting {orphaned_schools.count()} orphaned schools:")
            for school in orphaned_schools:
                print(f" - ID: {school.id}, Name: {school.name}, Created: {school.created_at}")
            orphaned_schools.delete()
        else:
            pass
    except Exception as e:
        print(f"Error in CleanUpOrphans: {e}")
        return False
    return True

  