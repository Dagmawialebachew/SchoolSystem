# notifications/models.py
from django.db import models
from django.conf import settings
from schools.models import School
from accounts.models import User


class AnnouncementQuerySet(models.QuerySet):
    def for_user(self, user):
        if user.role == "SUPER_ADMIN":
            return self.all()
        elif user.role == "SCHOOL_ADMIN":
            return self.filter(school=user.school)
        elif user.role == "TEACHER":
            return self.filter(school=user.school, target__in=["ALL", "TEACHERS"])
        elif user.role == "PARENT":
            return self.filter(school=user.school, target__in=["ALL", "PARENTS"])
        else:
            return self.none()
        
    


# notifications/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone

class AnnouncementQuerySet(models.QuerySet):
    def active(self):
        now = timezone.now()
        return self.filter(
            publish_at__lte=now
        ).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now) | models.Q(pinned=True)
        )

    def targeted_to(self, user):
        qs = self
        if user.is_super_admin():
            return qs

        if user.is_teacher():
            qs = qs.filter(
                models.Q(target='ALL') |
                models.Q(target='TEACHERS') |
                models.Q(target='CLASS') |
                models.Q(target='DIVISION')
            )
        elif user.is_parent():
            qs = qs.filter(
                models.Q(target='ALL') |
                models.Q(target='PARENTS') |
                models.Q(target='DIVISION')
            )
        elif user.role == 'SCHOOL_ADMIN':
            qs = qs.filter(
                models.Q(target='ALL') |
                models.Q(target='TEACHERS') |
                models.Q(target='PARENTS') |
                models.Q(target='DIVISION')
            )

        # Scope by school
        if hasattr(user, 'school') and user.school_id:
            qs = qs.filter(school=user.school)

        # Scope by division
        if hasattr(user, 'division') and user.division_id:
            qs = qs.filter(
                models.Q(target__in=['ALL', 'TEACHERS', 'PARENTS']) |
                models.Q(target='DIVISION', division=user.division)
            )

        # Scope by class
        if hasattr(user, 'classprogram') and user.classprogram_id:
            qs = qs.filter(
                models.Q(target__in=['ALL', 'TEACHERS', 'PARENTS']) |
                models.Q(target='CLASS', classes=user.classprogram)
            )

        return qs
    
    def unread_for(self, user):
        """Announcements targeted to user that they haven’t read yet."""
        return self.active().targeted_to(user).exclude(
            reads__user=user
        )

PRIORITY_CHOICES = [
    ('INFO', 'Info'),
    ('IMPORTANT', 'Important'),
    ('URGENT', 'Urgent'),
]

TARGET_CHOICES = [
    ('ALL', 'All Users'),
    ('TEACHERS', 'Teachers'),
    ('PARENTS', 'Parents'),
    ('CLASS', 'Specific Classes'),
    ('DIVISION', 'Specific Division'),   # 👈 new
]


DELIVERY_CHOICES = [
    ('DASH', 'In-app'),
    ('PUSH', 'Push'),
    ('EMAIL', 'Email'),
    ('SMS', 'SMS'),
]

CATEGORY_CHOICES = [
    ('GENERAL', 'General'),
    ('ATTENDANCE', 'Attendance'),
    ('EVENT', 'Event'),
    ('ACADEMIC', 'Academic'),
]



class Announcement(models.Model):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE)
    division = models.ManyToManyField(
    'classes_app.Division',
    blank=True,
    help_text="Used when target=DIVISION"
)
    title = models.CharField(max_length=255)
    message = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='GENERAL'
    )

    # Rich content (optional)
    links = models.JSONField(blank=True, null=True, help_text="List of {label, url} objects.")
    videos = models.JSONField(blank=True, null=True, help_text="List of video URLs (YouTube/Vimeo).")

    # Targeting
    target = models.CharField(max_length=20, choices=TARGET_CHOICES, default='ALL')
    classes = models.ManyToManyField('classes_app.ClassProgram', blank=True, help_text="Used when target=CLASS")

    # Publishing controls
    publish_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(blank=True, null=True)
    pinned = models.BooleanField(default=False)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='INFO')

    # Delivery channels
    delivery_channels = models.JSONField(
        default=list,
        help_text="e.g. ['DASH','EMAIL','SMS']"
    )

    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AnnouncementQuerySet.as_manager()

    class Meta:
        ordering = ['-pinned', '-publish_at', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.school.name})"

class AnnouncementAttachment(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='announcements/')
    label = models.CharField(max_length=255, blank=True)
    

    def __str__(self):
        return self.label or self.file.name

REACTION_CHOICES = [
    ('LIKE', 'Like'),
    ('LOVE', 'Love'),
    ('ACK', 'Acknowledged'),
]

class AnnouncementReaction(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('announcement', 'user', 'reaction')

class AnnouncementRead(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='reads')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('announcement', 'user')

