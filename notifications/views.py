from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Announcement


@login_required
def announcement_list(request):
    announcements = Announcement.objects.for_user(request.user)
    return render(request, 'notifications/list.html', {'announcements': announcements})