from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, FormView, View
from django.forms import modelformset_factory
from django.http import JsonResponse

from core.mixins import RoleRequiredMixin, SchoolScopedMixin
from .models import Attendance
from classes_app.models import ClassProgram
from students.models import Student


class ClassSessionList(RoleRequiredMixin, ListView):
    """Shows today's classes for a teacher"""
    model = ClassProgram
    template_name = "attendance/class_session_list.html"
    allowed_roles = ["TEACHER"]

    def get_queryset(self):
        qs = super().get_queryset()
        # Only classes assigned to this teacher + same school
        return qs.filter(teachers=self.request.user.teacher, school=self.request.user.school)


class AttendanceMarkView(RoleRequiredMixin, FormView):
    """Mark attendance for students of a class"""
    template_name = "attendance/attendance_mark.html"
    allowed_roles = ["TEACHER"]

    def get_form_class(self):
        AttendanceFormSet = modelformset_factory(
            Attendance,
            fields=["status"],
            extra=0,
        )
        return AttendanceFormSet

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        class_id = self.kwargs["pk"]
        class_obj = get_object_or_404(ClassProgram, pk=class_id, school=self.request.user.school)

        today = timezone.now().date()
        students = class_obj.students.all()

        # Pre-fill or create attendance records for today
        qs = Attendance.objects.filter(
            school=self.request.user.school,
            student__in=students,
            date=today
        )
        existing_student_ids = [a.student_id for a in qs]

        missing_students = [s for s in students if s.id not in existing_student_ids]
        for s in missing_students:
            Attendance.objects.create(
                school=self.request.user.school,
                student=s,
                date=today,
                status="PRESENT",  # default
                marked_by=self.request.user,
            )
        kwargs["queryset"] = Attendance.objects.filter(
            school=self.request.user.school,
            student__in=students,
            date=today
        )
        return kwargs

    def form_valid(self, form):
        form.save()
        return redirect("attendance:class-sessions")


class AttendanceToggleView(RoleRequiredMixin, View):
    """Quick AJAX toggle present/absent"""
    allowed_roles = ["TEACHER"]

    def post(self, request, *args, **kwargs):
        attendance_id = kwargs.get("pk")
        att = get_object_or_404(Attendance, pk=attendance_id, school=request.user.school)
        att.status = "ABSENT" if att.status == "PRESENT" else "PRESENT"
        att.save()
        return JsonResponse({"status": att.status})


class AttendanceListView(RoleRequiredMixin, ListView):
    """Show attendance records for a school"""
    model = Attendance
    template_name = "attendance/attendance_list.html"
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN", "TEACHER"]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(school=self.request.user.school).select_related("student", "marked_by")
