
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from core.mixins import RoleRequiredMixin, SchoolScopedMixin, ParentScopedMixin
from .models import Student
from .forms import StudentForm
from fees.models import FeeStructure
from django.db.models import Q


class StudentCreateView(RoleRequiredMixin, SchoolScopedMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'
    success_url = reverse_lazy('students:list')
    allowed_roles = ['SCHOOL_ADMIN']

    def get_form_kwargs(self):
        """Pass the logged-in user to the form for scoping dropdowns."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  
        return kwargs

    def get_context_data(self, **kwargs):
        """Add fee structures list and selected fees to the template context."""
        context = super().get_context_data(**kwargs)
        school = self.request.user.school
        
        # Only active fees for this school
        fee_structures = FeeStructure.objects.filter(school=school, in_progress=True)
        
        selected_fees = []
        if self.request.method == "POST":
            selected_fees = [int(f) for f in self.request.POST.getlist("fee_structures")]
        
        context.update({
            "fee_structures": fee_structures,
            "selected_fees": selected_fees
        })
        return context

    def form_valid(self, form):
        """Handle saving multiple fee structures for a student."""
        form.instance.school = self.request.user.school  
        response = super().form_valid(form)
        
        # Save selected fees
        selected_fees = self.request.POST.getlist("fee_structures")
        self.object.fee_structures.set(selected_fees)
        
        messages.success(self.request, '✅ Student created successfully!')
        return response

    
    
class StudentListView(RoleRequiredMixin, SchoolScopedMixin, ParentScopedMixin, ListView):
    model = Student
    template_name = 'students/student_list.html'
    context_object_name = 'students'
    paginate_by = 25

    

    def get_queryset(self):
        queryset = Student.objects.filter(school = self.request.user.school).all()
        search_query = self.request.GET.get("search")
        if search_query:
            queryset = queryset.filter(
                Q(full_name__icontains=search_query) |
                Q(parent_phone__icontains=search_query)
            )
        print(queryset)
        return queryset
    
    
class StudentUpdateView(RoleRequiredMixin, SchoolScopedMixin, UpdateView):
    """
    Update an existing student record.
    Supports multiple fee structures selection.
    Accessible only to SCHOOL_ADMIN.
    """
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'
    success_url = reverse_lazy('students:list')
    allowed_roles = ['SCHOOL_ADMIN']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = self.request.user.school
        fee_structures = FeeStructure.objects.filter(school=school, in_progress=True)

        if self.request.method == "POST":
            selected_fees = [int(f) for f in self.request.POST.getlist("fee_structures")]
        else:
            student = self.object  # This is the student being edited
            selected_fees = list(student.fee_structures.values_list("id", flat=True))
            print("Selected fees:", selected_fees)

        context.update({
            "fee_structures": fee_structures,
            "selected_fees": selected_fees
        })
        return context


    def get_form_kwargs(self):
        """
        Pass user to form to filter querysets (e.g., limit FeeStructures to their school).
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """
        Save student and their related fee structures.
        """
        messages.success(self.request, f"✅ {form.instance.full_name} updated successfully!")
        return super().form_valid(form)


class StudentDeleteView(RoleRequiredMixin, SchoolScopedMixin, DeleteView):
    model = Student
    success_url = reverse_lazy("students:list")
    allowed_roles = ["SCHOOL_ADMIN"]

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Student deleted successfully!")
        return super().delete(request, *args, **kwargs)