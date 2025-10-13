# parents/admin.py
from django.contrib import admin
from .models import ParentProfile
from students.models import Student

class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'telegram_username', 'children_list')
    search_fields = ('user__first_name', 'user__last_name', 'phone_number', 'telegram_username')
    filter_horizontal = ('children',)

    def children_list(self, obj):
        return ", ".join([child.full_name for child in obj.children.all()])
    children_list.short_description = "Children"

admin.site.register(ParentProfile, ParentProfileAdmin)
