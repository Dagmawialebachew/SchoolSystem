from django.contrib import admin
from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('content', 'target', 'school', 'created_at')
    list_filter = ('school', 'target', 'created_at')
    search_fields = ('content',)
    date_hierarchy = 'created_at'