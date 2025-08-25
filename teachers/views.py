from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from core.mixins import RoleRequiredMixin, SchoolScopedMixin
from .models import Teacher
from .forms import TeacherForm


class TeacherCreateView(RoleRequiredMixin, SchoolScopedMixin, CreateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'teachers/form.html'
    success_url = reverse_lazy('teachers:list')
    allowed_roles = ['SCHOOL_ADMIN']
    
    def form_valid(self, form):
        messages.success(self.request, 'Teacher created successfully!')
        return super().form_valid(form)
class TeacherListView(RoleRequiredMixin, SchoolScopedMixin, ListView):
    model = Teacher
class TeacherUpdateView(RoleRequiredMixin, SchoolScopedMixin, UpdateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'teachers/form.html'
    success_url = reverse_lazy('teachers:list')
    allowed_roles = ['SCHOOL_ADMIN']
    
    def form_valid(self, form):
        messages.success(self.request, 'Teacher updated successfully!')
        return super().form_valid(form)
    template_name = 'teachers/list.html'
    context_object_name = 'teachers'
class TeacherDeleteView(RoleRequiredMixin, SchoolScopedMixin, DeleteView):
    model = Teacher
    template_name = 'teachers/confirm_delete.html'
    success_url = reverse_lazy('teachers:list')
    allowed_roles = ['SCHOOL_ADMIN']
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Teacher deleted successfully!')
        return super().delete(request, *args, **kwargs)
    paginate_by = 20
    allowed_roles = ['SCHOOL_ADMIN', 'TEACHER']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                first_name__icontains=search
            ) | queryset.filter(
                last_name__icontains=search
            )
        return queryset.order_by('last_name', 'first_name')