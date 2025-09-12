from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from .models import ClassProgram
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


class ClassDetailView(LoginRequiredMixin, DetailView):
    model = ClassProgram
    template_name = "classes_app/classes_app_detail.html"
    context_object_name = "class_program"


class ClassCreateView(LoginRequiredMixin, CreateView):
    model = ClassProgram
    form_class = ClassProgramForm
    template_name = "classes_app/classes_app_form.html"
    success_url = reverse_lazy("classes:list")

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.school = self.request.user.school  # if your user has a related school
        obj.save()
        messages.success(self.request, "Class created successfully.")
        return redirect(self.success_url)


class ClassUpdateView(LoginRequiredMixin, UpdateView):
    model = ClassProgram
    form_class = ClassProgramForm
    template_name = "classes_app/classes_app_form.html"
    success_url = reverse_lazy("classes:list")

    def form_valid(self, form):
        messages.success(self.request, "Class updated successfully.")
        return super().form_valid(form)


class ClassDeleteView(LoginRequiredMixin, DeleteView):
    model = ClassProgram
    template_name = "classes_app/confirm_delete.html"
    success_url = reverse_lazy("classes:list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Class deleted successfully.")
        return super().delete(request, *args, **kwargs)
