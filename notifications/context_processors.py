# notifications/context_processors.py
from .models import Announcement

def unread_announcements(request):
    if request.user.is_authenticated:
        count = Announcement.objects.unread_for(request.user).count()
    else:
        count = 0
    return {"unread_announcements_count": count}
