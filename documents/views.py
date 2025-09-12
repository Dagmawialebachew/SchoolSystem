# documents/views.py
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from core.mixins import RoleRequiredMixin
from .models import Document
from .forms import DocumentForm


class DocumentListView(RoleRequiredMixin, ListView):
    model = Document
    template_name = "documents/document_list.html"
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN", "TEACHER"]


class DocumentDetailView(RoleRequiredMixin, DetailView):
    model = Document
    template_name = "documents/document_detail.html"
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN", "TEACHER"]


class DocumentCreateView(RoleRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = "documents/document_form.html"
    success_url = reverse_lazy("documents:list")
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN"]

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        return super().form_valid(form)


class DocumentUpdateView(RoleRequiredMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = "documents/document_form.html"
    success_url = reverse_lazy("documents:list")
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN"]


class DocumentDeleteView(RoleRequiredMixin, DeleteView):
    model = Document
    template_name = "documents/document_confirm_delete.html"
    success_url = reverse_lazy("documents:list")
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN"]
