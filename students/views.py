from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from core.mixins import RoleRequiredMixin, SchoolScopedMixin, ParentScopedMixin
from .models import Student
from .forms import StudentForm


class StudentCreateView(RoleRequiredMixin, SchoolScopedMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/form.html'
    success_url = reverse_lazy('students:list')
    allowed_roles = ['SCHOOL_ADMIN']
    
    def form_valid(self, form):
        messages.success(self.request, 'Student created successfully!')
        return super().form_valid(form)
class StudentListView(RoleRequiredMixin, SchoolScopedMixin, ParentScopedMixin, ListView):
    model = Student
class StudentUpdateView(RoleRequiredMixin, SchoolScopedMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/form.html'
    success_url = reverse_lazy('students:list')
    allowed_roles = ['SCHOOL_ADMIN']
    
    def form_valid(self, form):
        messages.success(self.request, 'Student updated successfully!')
        return super().form_valid(form)
    template_name = 'students/list.html'
    context_object_name = 'students'
class StudentDeleteView(RoleRequiredMixin, SchoolScopedMixin, DeleteView):
    model = Student
    template_name = 'students/confirm_delete.html'
    success_url = reverse_lazy('students:list')
    allowed_roles = ['SCHOOL_ADMIN']
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Student deleted successfully!')
        return super().delete(request, *args, **kwargs)
    paginate_by = 20
    allowed_roles = ['SCHOOL_ADMIN', 'TEACHER', 'PARENT']
    
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