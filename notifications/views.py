# notifications/views.py
from django.views.generic import CreateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from core.mixins import RoleRequiredMixin, SchoolScopedMixin
from .models import Announcement
from .forms import AnnouncementForm

class AnnouncementCreateView(RoleRequiredMixin, SchoolScopedMixin, CreateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'notifications/create.html'
    success_url = '/dashboard/'
    allowed_roles = ['SCHOOL_ADMIN']

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class AnnouncementListView(RoleRequiredMixin, SchoolScopedMixin, ListView):
    model = Announcement
    template_name = 'notifications/list.html'
    context_object_name = 'announcements'
    allowed_roles = ['TEACHER', 'PARENT']

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        if u.role == 'TEACHER':
            return qs.filter(target__in=['ALL', 'TEACHERS'])
        if u.role == 'PARENT':
            return qs.filter(target__in=['ALL', 'PARENTS'])
        return qs.none()
