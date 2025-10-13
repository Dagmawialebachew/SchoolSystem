# classes_app/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import Division, DivisionLog

@receiver(post_save, sender=Division)
def log_division_save(sender, instance, created, **kwargs):
    if created:
        DivisionLog.objects.create(
            division=instance,
            actor=getattr(instance, "_actor", None),
            action="CREATE",
            changes=f"Division {instance.name} created."
        )
    else:
        DivisionLog.objects.create(
            division=instance,
            actor=getattr(instance, "_actor", None),
            action="UPDATE",
            changes=f"Division {instance.name} updated."
        )

@receiver(post_delete, sender=Division)
def log_division_delete(sender, instance, **kwargs):
    DivisionLog.objects.create(
        division=instance,
        actor=getattr(instance, "_actor", None),
        action="DELETE",
        changes=f"Division {instance.name} deleted."
    )
