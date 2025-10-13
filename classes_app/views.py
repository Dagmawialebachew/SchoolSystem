from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Sum, Count, Q, Max, F, Value, Prefetch
from django.db.models.functions import Coalesce
from students.models import Student
from teachers.models import Teacher
from .models import ClassProgram, ClassTeacherAssignment, Division, DivisionLog, ClassSubjectAssignment
from core.mixins import RoleRequiredMixin, UserScopedMixin
from .forms import ClassProgramForm, DivisionForm


class ClassListView(LoginRequiredMixin, ListView):
    model = ClassProgram
    template_name = "classes_app/classes_app_list.html"
    context_object_name = "classes"
    paginate_by = 10  # ✅ 10 per page

    def get_queryset(self):
        
        qs = ClassProgram.objects.filter(school=self.request.user.school).all().order_by("name")
        search = self.request.GET.get("search")
        if search:
            qs = ClassProgram.objects.filter(
                Q(name__icontains=search) |
                Q(division__name__icontains=search)
            )     
            
        return qs



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

        # Homeroom teachers
        ctx["homerooms"] = [a for a in cp.teacher_assignments.all() if a.is_homeroom_teacher]

        # Subject assignments
        ctx["subject_assignments"] = cp.subject_assignments.all()

        # Related classes in the same division
        ctx["related_classes"] = (
            ClassProgram.objects.filter(school=cp.school, division=cp.division)
            .exclude(pk=cp.pk)
            .order_by("name")[:8]
        )

        # --- New: All teachers with role flags ---
        teacher_ids = set()
        for ta in cp.teacher_assignments.all():
            if ta.teacher_id:
                teacher_ids.add(ta.teacher_id)
        for sa in cp.subject_assignments.all():
            if sa.teacher_id:
                teacher_ids.add(sa.teacher_id)

        teachers = []
        if teacher_ids:
            base_teachers = Teacher.objects.filter(pk__in=teacher_ids)
            homeroom_ids = {ta.teacher_id for ta in cp.teacher_assignments.all() if ta.is_homeroom_teacher}
            subject_ids = {sa.teacher_id for sa in cp.subject_assignments.all() if sa.teacher_id}

            for t in base_teachers:
                t.is_homeroom = t.pk in homeroom_ids
                t.is_subject = t.pk in subject_ids
                teachers.append(t)

        ctx["teachers"] = teachers
        ctx["num_teachers"] = len(teachers)


        return ctx
class ClassCreateView(RoleRequiredMixin, UserScopedMixin, CreateView):
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
        else:
            teacher = None
                
        teacher.save(update_fields=["is_homeroom_teacher"])
                
                

        messages.success(self.request, "Class created successfully.")
        return redirect(self.success_url)


    def form_invalid(self, form):
    # Loop through all field errors
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    # Non-field errors
                    messages.error(self.request, error)
                else:
                    # Field-specific errors
                    messages.error(self.request, f"{form.fields[field].label}: {error}")
        
        return super().form_invalid(form)


class ClassUpdateView(LoginRequiredMixin, UserScopedMixin, UpdateView):
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
    template_name = "classes_app/classes_app_confirm_delete.html"
    success_url = reverse_lazy("classes_app:list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Class deleted successfully.")
        return super().delete(request, *args, **kwargs)

class DivisionListView(RoleRequiredMixin, UserScopedMixin, ListView):
    role_required = ["SCHOOL_ADMIN"]
    model = Division
    template_name = "classes_app/division_list.html"
    context_object_name = "divisions"
    paginate_by = 12

    GENERAL_DIVISIONS = [
        ("KINDERGARTEN", "Kindergarten"),
        ("PRIMARY_1_4", "Primary (Grades 1–4)"),
        ("PRIMARY_5_8", "Primary (Grades 5–8)"),
        ("SECONDARY_9_12", "Secondary (Grades 9–12)"),
    ]

    def get_queryset(self):
        qs = Division.objects.filter(school=self.request.user.school)

        # Annotate counts
        qs = qs.annotate(
            num_classes=Count("classes", distinct=True),
            num_homeroom_teachers=Count(
                "classes__teacher_assignments",
                filter=Q(classes__teacher_assignments__is_homeroom_teacher=True),
                distinct=True,
            ),
            num_subject_teachers=Count(
                "classes__subject_assignments__teacher",
                distinct=True,
            ),
        ).annotate(
            num_teachers=Coalesce(F("num_homeroom_teachers"), Value(0)) +
                         Coalesce(F("num_subject_teachers"), Value(0))
        )

        # Search
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

        # Sorting
        sort = self.request.GET.get("sort", "name")
        sort_map = {
            "name": "name",
            "-name": "-name",
            "classes": "num_classes",
            "-classes": "-num_classes",
            "teachers": "num_teachers",
            "-teachers": "-num_teachers",
            "in_progress": "in_progress",
            "-in_progress": "-in_progress",
        }
        if sort in sort_map:
            qs = qs.order_by(sort_map[sort])

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["general_keys"] = [key for key, _ in self.GENERAL_DIVISIONS]
        ctx["current_search"] = self.request.GET.get("search", "")
        ctx["current_sort"] = self.request.GET.get("sort", "name")
        return ctx
class DivisionCreateView(RoleRequiredMixin, UserScopedMixin, View):
    """
    Create divisions for a school:
    - General divisions checkboxes
    - Custom division rows (name + description)
    - On submit: create new divisions or update existing ones
    """
    role_required = ["SCHOOL_ADMIN"]
    template_name = "classes_app/division_form.html"

    GENERAL_DIVISIONS = [
        ("KINDERGARTEN", "Kindergarten"),
        ("PRIMARY_1_4", "Primary (Grades 1–4)"),
        ("PRIMARY_5_8", "Primary (Grades 5–8)"),
        ("SECONDARY_9_12", "Secondary (Grades 9–12)"),
    ]

    def get(self, request):
        school = request.user.school
        existing_divisions = Division.objects.filter(school=school).order_by("name")
        existing_names = set(existing_divisions.values_list("name", flat=True))
        form = DivisionForm(user=request.user)

        # Preselect general divisions already existing in the school
        preselected_general = [
            div.name for div in existing_divisions if div.name in dict(self.GENERAL_DIVISIONS)
        ]

        return render(request, self.template_name, {
            "form": form,
            "object": None,
            "general_divisions": self.GENERAL_DIVISIONS,
            "existing_divisions": existing_divisions,
            "existing_names": existing_names,
            "preselected_general": preselected_general,
        })

    def post(self, request):
        school = request.user.school
        selected_general = set(request.POST.getlist("general_divisions"))

        # Collect custom divisions
        custom_divisions = []
        for key in request.POST:
            if key.startswith("custom_name_"):
                idx = key.split("_")[-1]
                name = (request.POST.get(f"custom_name_{idx}", "") or "").strip()
                description = (request.POST.get(f"custom_description_{idx}", "") or "").strip()
                if name:
                    custom_divisions.append((name, description))
                    selected_general.add(name)  # include custom as valid choice

        created_count = 0
        updated_count = 0

        # Create or update general divisions
        for value, _label in self.GENERAL_DIVISIONS:
            if value in selected_general:
                obj, created = Division.objects.get_or_create(
                    school=school,
                    name=value,
                    defaults={"in_progress": True},
                )
                obj._actor = request.user
                if not created:
                    obj.save(update_fields=["in_progress"])  # triggers post_save with actor
                else:
                    created_count += 1

        # Create or update custom divisions
        for name, description in custom_divisions:
            obj, created = Division.objects.update_or_create(
                school=school,
                name=name,
                defaults={"description": description, "in_progress": False},
            )
            obj._actor = request.user
            if not created:
                obj.save(update_fields=["description", "in_progress"])
                updated_count += 1
            else:
                created_count += 1

        if created_count or updated_count:
            messages.success(request, f"Divisions saved. Created {created_count} and updated {updated_count}.")
        else:
            messages.info(request, "No changes made.")

        return redirect("classes_app:division_list")


class DivisionUpdateView(RoleRequiredMixin, UserScopedMixin, UpdateView):
    role_required = ["SCHOOL_ADMIN"]
    model = Division
    form_class = DivisionForm
    template_name = "classes_app/division_form.html"
    success_url = reverse_lazy("classes_app:division_list")

    GENERAL_DIVISIONS = [
        ("KINDERGARTEN", "Kindergarten"),
        ("PRIMARY_1_4", "Primary (Grades 1–4)"),
        ("PRIMARY_5_8", "Primary (Grades 5–8)"),
        ("SECONDARY_9_12", "Secondary (Grades 9–12)"),
    ]

    def get_queryset(self):
        return Division.objects.filter(school=self.request.user.school)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Dynamically populate 'name' choices with all school divisions
        school_divisions = Division.objects.filter(school=self.request.user.school)
        choices = [(d.name, d.name) for d in school_divisions]

        # Include current instance if custom
        if self.object.name not in dict(choices):
            choices.append((self.object.name, self.object.name))
        form.fields["name"].choices = choices
        return form

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Ensure uniqueness per school
        school = self.request.user.school
        new_name = form.cleaned_data["name"]
        if Division.objects.filter(school=school, name=new_name).exclude(pk=self.object.pk).exists():
            form.add_error("name", "A division with this name already exists for this school.")
            return self.form_invalid(form)
        messages.success(self.request, "Division updated successfully.")
        return super().form_valid(form)

class DivisionDeleteView(RoleRequiredMixin, UserScopedMixin, DeleteView):
    role_required = ["SCHOOL_ADMIN"]
    model = Division
    template_name = "classes_app/division_confirm_delete.html"
    success_url = reverse_lazy("classes_app:division_list")

    def get_queryset(self):
        return Division.objects.filter(school=self.request.user.school)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Division deleted successfully.")
        return super().delete(request, *args, **kwargs)
    
    
class DivisionDetailView(RoleRequiredMixin, UserScopedMixin, DetailView):
    role_required = ["SCHOOL_ADMIN"]
    model = Division
    template_name = "classes_app/division_detail.html"
    context_object_name = "division"

    GENERAL_DIVISIONS = [
        ("KINDERGARTEN", "Kindergarten"),
        ("PRIMARY_1_4", "Primary (Grades 1–4)"),
        ("PRIMARY_5_8", "Primary (Grades 5–8)"),
        ("SECONDARY_9_12", "Secondary (Grades 9–12)"),
    ]

    def get_queryset(self):
        return Division.objects.filter(school=self.request.user.school)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        division = self.object

        # Classes with prefetch for assignments and student count
        classes = division.classes.prefetch_related(
            "teacher_assignments__teacher",
            "subject_assignments__teacher",
        ).annotate(
            students_count=Count('students', distinct=True)  # assumes your Class model has a related_name 'students' for Student
        ).order_by("name")

        # Counts
        num_classes = classes.count()
        num_students = Student.objects.filter(school=division.school).count()
        num_homeroom = ClassTeacherAssignment.objects.filter(
            class_program__division=division, is_homeroom_teacher=True
        ).values("teacher").distinct().count()
        num_subject = ClassSubjectAssignment.objects.filter(
            class_program__division=division
        ).values("teacher").exclude(teacher__isnull=True).distinct().count()
        num_teachers = num_homeroom + num_subject

        # Unique teachers list with role flags
        teacher_ids = set()
        teachers = []
        for ta in ClassTeacherAssignment.objects.filter(class_program__division=division).select_related("teacher"):
            if ta.teacher_id:
                teacher_ids.add(ta.teacher_id)
        for sa in ClassSubjectAssignment.objects.filter(class_program__division=division).select_related("teacher"):
            if sa.teacher_id:
                teacher_ids.add(sa.teacher_id)
        if teacher_ids:
            base_teachers = Teacher.objects.filter(pk__in=teacher_ids)
            homeroom_ids = set(
                ClassTeacherAssignment.objects.filter(
                    class_program__division=division, is_homeroom_teacher=True
                ).values_list("teacher_id", flat=True)
            )
            subject_ids = set(
                ClassSubjectAssignment.objects.filter(
                    class_program__division=division
                ).exclude(teacher__isnull=True).values_list("teacher_id", flat=True)
            )
            for t in base_teachers:
                t.is_homeroom = t.pk in homeroom_ids
                t.is_subject = t.pk in subject_ids
                teachers.append(t)

        logs = []
        related_divisions = Division.objects.filter(
            school=division.school
        ).exclude(pk=division.pk).order_by("name")[:6]

        ctx.update({
            "general_keys": [k for k, _ in self.GENERAL_DIVISIONS],
            "classes": classes,
            "num_classes": num_classes,
            "num_students": num_students,
            "num_teachers": num_teachers,
            "teachers": teachers,
            "logs": logs,
            "related_divisions": related_divisions,
        })
        return ctx
    
    

# views.py
class DivisionAuditView(RoleRequiredMixin, UserScopedMixin, DetailView):
    role_required = ["SCHOOL_ADMIN"]
    model = Division
    template_name = "classes_app/division_audit.html"
    context_object_name = "division"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["logs"] = DivisionLog.objects.filter(division=self.object)
        return ctx
    
    

class AssignTeachersView(RoleRequiredMixin, UserScopedMixin, View):
    role_required = ["SCHOOL_ADMIN"]
    template_name = "classes_app/assign_teachers.html"

    def get(self, request, pk):
        class_program = get_object_or_404(ClassProgram, pk=pk, school=request.user.school)
        teachers = Teacher.objects.filter(school=request.user.school).order_by("first_name")

        # Preselect existing assignments from both ClassTeacherAssignment and ClassSubjectAssignment
        selected_ids = set()
        homeroom_ids = set()

        # ClassTeacherAssignment
        for ta in class_program.teacher_assignments.all():
            selected_ids.add(ta.teacher_id)
            if ta.is_homeroom_teacher:
                homeroom_ids.add(ta.teacher_id)

        # Subject teachers (non-null only)
        for sa in class_program.subject_assignments.filter(teacher__isnull=False):
            selected_ids.add(sa.teacher_id)

        return render(request, self.template_name, {
            "class_program": class_program,
            "teachers": teachers,
            "selected_ids": selected_ids,
            "homeroom_ids": homeroom_ids,
        })

    def post(self, request, pk):
        class_program = get_object_or_404(ClassProgram, pk=pk, school=request.user.school)

        teacher_ids = set(request.POST.getlist("teachers"))
        homeroom_ids = set(request.POST.getlist("homeroom_teachers"))

        # Existing ClassTeacherAssignments
        existing_assignments = ClassTeacherAssignment.objects.filter(class_program=class_program)
        existing_teacher_ids = set(existing_assignments.values_list("teacher_id", flat=True))

        # Update homeroom flags on existing assignments
        for assignment in existing_assignments:
            is_homeroom = assignment.teacher_id in homeroom_ids
            if assignment.is_homeroom_teacher != is_homeroom:
                assignment.is_homeroom_teacher = is_homeroom
                assignment.save(update_fields=["is_homeroom_teacher"])

        # Only create assignments for teachers who do NOT already have a ClassTeacherAssignment
        new_teacher_ids = teacher_ids - existing_teacher_ids
        for tid in teacher_ids:
            ClassTeacherAssignment.objects.update_or_create(
                class_program=class_program,
                teacher_id=tid,
                defaults={
                    "is_homeroom_teacher": tid in homeroom_ids,
                    "school": class_program.school
                }
            )

        # Remove assignments for teachers no longer selected
        

        messages.success(request, "Teachers updated successfully.")
        return redirect("classes_app:detail", pk=class_program.pk)
