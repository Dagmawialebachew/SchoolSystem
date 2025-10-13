import json
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib import messages
from classes_app.models import ClassProgram
from core.mixins import RoleRequiredMixin, UserScopedMixin
from .models import Teacher
from .forms import TeacherForm


class TeacherListView(RoleRequiredMixin, UserScopedMixin, ListView):
    model = Teacher
    template_name = 'teachers/teacher_list.html'
    context_object_name = 'teachers'
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

class TeacherCreateView(RoleRequiredMixin, UserScopedMixin, CreateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'teachers/teacher_form.html'
    success_url = reverse_lazy('teachers:list')
    allowed_roles = ['SCHOOL_ADMIN']

    def form_valid(self, form):
        form.instance.school = self.request.user.school
        response = super().form_valid(form)

        # Save class assignments
        selected_classes = form.cleaned_data.get('classes', [])
        teacher = self.object

        # Remove any assignments not in selected_classes
        teacher.class_assignments.exclude(class_program__in=selected_classes).delete()
        
        # Add new assignments
        for cls in selected_classes:
            teacher.class_assignments.get_or_create(
                class_program=cls,
                defaults={"teacher": teacher, "is_homeroom_teacher": False, "school": self.request.user.school}
            )
        messages.success(self.request, 'Teacher is updated succefully')

        return response

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        # Scope classes to this school
        form.fields['classes'].queryset = ClassProgram.objects.filter(
            school=self.request.user.school
        ).select_related('division').order_by('division__name', 'name')
        return form
    
    def form_invalid(self, form):
        # Loop through all field errors
        for field, errors in form.errors.items():
            for error in errors:
                if field == "__all__":
                    # Non-field errors
                    messages.error(self.request, error)
                else:
                    messages.error(self.request, f"{form.fields[field].label}: {error}")

        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # JSON for JS picker
        classes = ClassProgram.objects.filter(
            school=self.request.user.school
        ).select_related('division').order_by('division__name', 'name')
        context['classes_json'] = json.dumps([
    {"id": c.id, "name": c.name, "division": c.division.get_name_display()}
    for c in classes
])
        print('here is the contenxt', context['classes_json'])
        return context

class TeacherUpdateView(RoleRequiredMixin, UserScopedMixin, UpdateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'teachers/teacher_form.html'
    success_url = reverse_lazy('teachers:list')
    allowed_roles = ['SCHOOL_ADMIN']

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.fields['classes'].queryset = ClassProgram.objects.filter(
            school=self.request.user.school
        ).select_related('division').order_by('division__name', 'name')
        return form

    def form_valid(self, form):
        form.instance.school = self.request.user.school
        response = super().form_valid(form)

        # Save class assignments
        selected_classes = form.cleaned_data.get('classes', [])
        teacher = self.object

        # Remove any assignments not in selected_classes
        teacher.class_assignments.exclude(class_program__in=selected_classes).delete()
        
        # Add new assignments
        for cls in selected_classes:
            teacher.class_assignments.get_or_create(
                class_program=cls,
                defaults={"teacher": teacher, "is_homeroom_teacher": False, "school": self.request.user.school}
            )
        messages.success(self.request, 'Teacher is updated succefully')

        return response

    
    def form_invalid(self, form):
        # Loop through all field errors
        for field, errors in form.errors.items():
            for error in errors:
                if field == "__all__":
                    # Non-field errors
                    messages.error(self.request, error)
                else:
                    messages.error(self.request, f"{form.fields[field].label}: {error}")

        return super().form_invalid(form)
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        classes = ClassProgram.objects.filter(
            school=self.request.user.school
        ).select_related('division').order_by('division__name', 'name')
        context['classes_json'] = json.dumps([
            {"id": c.id, "name": c.name, "division": c.division.get_name_display()}
            for c in classes
        ])
        return context


class TeacherDetailView(UserScopedMixin, DetailView):
    model = Teacher
    template_name = "teachers/teacher_detail.html"
    context_object_name = "teacher"

    def get_queryset(self):
        return Teacher.objects.filter(school=self.request.user.school)


class TeacherDeleteView(RoleRequiredMixin, UserScopedMixin, DeleteView):
    model = Teacher
    template_name = 'teachers/teacher_confirm_delete.html'
    success_url = reverse_lazy('teachers:list')
    allowed_roles = ['SCHOOL_ADMIN']

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Teacher deleted successfully!')
        return super().delete(request, *args, **kwargs)
