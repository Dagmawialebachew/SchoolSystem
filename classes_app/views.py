from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect

from teachers.models import Teacher
from .models import ClassProgram, ClassTeacherAssignment
from core.mixins import RoleRequiredMixin, SchoolScopedMixin
from .forms import ClassProgramForm


class ClassListView(LoginRequiredMixin, ListView):
    model = ClassProgram
    template_name = "classes_app/classes_app_list.html"
    context_object_name = "classes"
    paginate_by = 10  # ✅ 10 per page

    def get_queryset(self):
        qs = ClassProgram.objects.all().order_by("name")
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


# views.py
from django.views.generic import DetailView
from django.db.models import Prefetch
from classes_app.models import (
    ClassProgram,
    ClassTeacherAssignment,
    ClassSubjectAssignment,
)

class ClassDetailView(DetailView):
    model = ClassProgram
    template_name = "classes_app/classes_app_detail.html"
    context_object_name = "class_program"

    def get_queryset(self):
        return (
            ClassProgram.objects
            .select_related("division", "school", "teacher")
            .prefetch_related(
                Prefetch(
                    "teacher_assignments",
                    queryset=ClassTeacherAssignment.objects.select_related("teacher"),
                ),
                Prefetch(
                    "subject_assignments",
                    queryset=ClassSubjectAssignment.objects.select_related("subject", "teacher"),
                ),
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cp = ctx["class_program"]

        ctx["homerooms"] = [a for a in cp.teacher_assignments.all() if a.is_homeroom_teacher]
        ctx["subject_assignments"] = cp.subject_assignments.all()
        ctx["related_classes"] = (
            ClassProgram.objects.filter(school=cp.school, division=cp.division)
            .exclude(pk=cp.pk)
            .order_by("name")[:8]
        )
        return ctx

class ClassCreateView(RoleRequiredMixin, SchoolScopedMixin, CreateView):
    model = ClassProgram
    form_class = ClassProgramForm
    template_name = "classes_app/classes_app_form.html"
    success_url = reverse_lazy("classes:list")
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.school = self.request.user.school
        obj = form.save(commit=False)
        obj.school = self.request.user.school
        obj.save()

        # Handle homeroom teachers (up to 2)
        homeroom_teachers = form.cleaned_data.get("homeroom_teachers")
        if homeroom_teachers:
            for teacher in homeroom_teachers[:2]:
                ClassTeacherAssignment.objects.create(
                    school=form.instance.school,
                    class_program=obj,
                    teacher=teacher,
                    is_homeroom_teacher=True
                ),
                teacher.is_homeroom = True
        teacher.save(update_fields=["is_homeroom"])
                
                

        messages.success(self.request, "Class created successfully.")
        return redirect(self.success_url)


    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class ClassUpdateView(LoginRequiredMixin, SchoolScopedMixin, UpdateView):
    model = ClassProgram
    form_class = ClassProgramForm
    template_name = "classes_app/classes_app_form.html"
    success_url = reverse_lazy("classes_app:list")
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


    def form_valid(self, form):
        form.instance.school = self.request.user.school
        obj = form.save(commit=False)
        obj.school = self.request.user.school  # enforce school
        obj.save()

        # Handle homeroom teachers (up to 2)
        obj.teacher_assignments.filter(is_homeroom_teacher=True).delete()
        homeroom_teachers = form.cleaned_data.get("homeroom_teachers")
        if homeroom_teachers:
            for teacher in homeroom_teachers[:2]:
                ClassTeacherAssignment.objects.create(
                    class_program=obj,
                    teacher=teacher,
                    is_homeroom_teacher=True,
                    school = form.instance.school
                )

        messages.success(self.request, "Class updated successfully.")
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class ClassDeleteView(LoginRequiredMixin, DeleteView):
    model = ClassProgram
    template_name = "classes_app/confirm_delete.html"
    success_url = reverse_lazy("classes:list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Class deleted successfully.")
        return super().delete(request, *args, **kwargs)
