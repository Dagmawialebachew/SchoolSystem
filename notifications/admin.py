from django.contrib import admin
from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'school', 'message', 'created_at')
    list_filter = ('school', 'created_at')
    search_fields = ('title', 'school__name')
    date_hierarchy = 'created_at'