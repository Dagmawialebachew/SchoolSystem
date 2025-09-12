# schools/views.py

from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib import messages
from core.mixins import RoleRequiredMixin
from .models import School
from .forms import SchoolForm


class SchoolListView(RoleRequiredMixin, ListView):
    model = School
    template_name = 'schools/list.html'
    context_object_name = 'schools'
    allowed_roles = ['SUPER_ADMIN']  # only super admins see all schools
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset.order_by("name")


class SchoolCreateView(RoleRequiredMixin, CreateView):
    model = School
    form_class = SchoolForm
    template_name = 'schools/form.html'
    success_url = reverse_lazy('schools:list')
    allowed_roles = ['SUPER_ADMIN']

    def form_valid(self, form):
        messages.success(self.request, "School created successfully!")
        return super().form_valid(form)


class SchoolUpdateView(RoleRequiredMixin, UpdateView):
    model = School
    form_class = SchoolForm
    template_name = 'schools/form.html'
    success_url = reverse_lazy('schools:list')
    allowed_roles = ['SUPER_ADMIN']

    def form_valid(self, form):
        messages.success(self.request, "School updated successfully!")
        return super().form_valid(form)


class SchoolDeleteView(RoleRequiredMixin, DeleteView):
    model = School
    template_name = 'schools/confirm_delete.html'
    success_url = reverse_lazy('schools:list')
    allowed_roles = ['SUPER_ADMIN']

    def delete(self, request, *args, **kwargs):
        messages.success(request, "School deleted successfully!")
        return super().delete(request, *args, **kwargs)


class SchoolDetailView(RoleRequiredMixin, DetailView):
    model = School
    template_name = 'schools/detail.html'
    context_object_name = 'school'
    allowed_roles = ['SUPER_ADMIN', 'SCHOOL_ADMIN']
