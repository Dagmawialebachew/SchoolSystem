# attendance_app/views.py
from datetime import date as date_cls
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, View
from core.mixins import RoleRequiredMixin, UserScopedMixin
from .models import Attendance, AttendanceLog
from .forms import (
    AttendanceEditForm,
    AttendanceBulkStatusForm,
    AttendanceFilterForm,
)
from classes_app.models import ClassProgram
from students.models import Student
from django.db.models import Max, F, Subquery, OuterRef
from collections import defaultdict



class AttendanceListView(RoleRequiredMixin, UserScopedMixin, ListView):
    model = Attendance
    template_name = "attendance/attendance_list.html"
    context_object_name = "attendances"
    allowed_roles = ["SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER", "PARENT"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("student", "class_program")
        school = self.get_school()

        form = AttendanceFilterForm(self.request.GET or None, school=school)
        if form.is_valid():
            cd = form.cleaned_data
            if cd["class_program"]:
                qs = qs.filter(class_program=cd["class_program"])
            if cd["date"]:
                qs = qs.filter(date=cd["date"])
            if cd["session"]:
                qs = qs.filter(session=cd["session"])
            if cd["status"]:
                qs = qs.filter(status=cd["status"])
        return qs.order_by(
            "class_program__division__name", "class_program__name",
            "student__full_name", "student__parent_name"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.get_school()
        ctx["classes"] = ClassProgram.objects.filter(school=school).order_by("division__name", "name")
        ctx["today"] = date_cls.today()
        return ctx


class AttendanceEditView(RoleRequiredMixin, UserScopedMixin, View):
    allowed_roles = ["SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER"]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        form = AttendanceEditForm(request.POST, school=request.user.school)
        if not form.is_valid():
            return HttpResponseBadRequest("; ".join([f"{k}: {','.join(v)}" for k, v in form.errors.items()]))

        cd = form.cleaned_data
        att, created = Attendance.objects.select_for_update().get_or_create(
            school = self.get_school(),
            student=cd["student"],
            class_program=cd["class_program"],
            date=cd["date"],
            session=cd["session"],
            defaults={"status": cd["status"], "remarks": cd["remarks"], "marked_by": request.user},
        )

        if not created:
            if att.status != cd["status"] or att.remarks != cd["remarks"]:
                AttendanceLog.objects.create(
                    school = self.get_school(),
                    attendance=att,
                    previous_status=att.status,
                    new_status=cd["status"],
                    changed_by=request.user,
                    note=("Updated remarks" if att.remarks != cd["remarks"] else None),
                )
                att.status = cd["status"]
                att.remarks = cd["remarks"]
                att.marked_by = request.user
                att.save(update_fields=["status", "remarks", "marked_by"])

        messages.success(request, f"Attendance {'created' if created else 'updated'} for {cd['student']}.")
        return JsonResponse({"ok": True, "created": created, "attendance_id": att.id})


class AttendanceBulkMarkPresentView(RoleRequiredMixin, UserScopedMixin, View):
    allowed_roles = ["SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER"]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # Reuse the bulk form, pin status to PRESENT
        mutable = request.POST.copy()
        mutable["status"] = Attendance.Status.PRESENT
        form = AttendanceBulkStatusForm(mutable, school=request.user.school)
        print("POST data:", mutable)
        print("Form is valid?", form.is_valid())
        print("Form errors:", form.errors)

        if not form.is_valid():
            return HttpResponseBadRequest("; ".join([f"{k}: {','.join(v)}" for k, v in form.errors.items()]))

        cd = form.cleaned_data
        created_count = 0
        for stu in cd["students"]:
            att, created = Attendance.objects.get_or_create(
                school = self.get_school(),
                student=stu,
                class_program=cd["class_program"],
                date=cd["date"],
                session=cd["session"],
                defaults={"status": cd["status"], "marked_by": request.user},
            )
            if created:
                created_count += 1
            elif att.status != cd["status"]:
                AttendanceLog.objects.create(
                    school = self.get_school(),
                    attendance=att,
                    previous_status=att.status,
                    new_status=cd["status"],
                    changed_by=request.user,
                )
                att.status = cd["status"]
                att.marked_by = request.user
                att.save(update_fields=["status", "marked_by"])

        messages.success(request, f"Marked {created_count} new records as PRESENT.")
        return JsonResponse({"ok": True, "created": created_count})


class AttendanceBulkMarkStatusView(RoleRequiredMixin,UserScopedMixin, View):
    allowed_roles = ["SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER"]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        form = AttendanceBulkStatusForm(request.POST, school=request.user.school)
        if not form.is_valid():
            return HttpResponseBadRequest("; ".join([f"{k}: {','.join(v)}" for k, v in form.errors.items()]))

        cd = form.cleaned_data
        updates = 0
        for stu in cd["students"]:
            att, created = Attendance.objects.get_or_create(
                student=stu,
                school = self.get_school(),
                class_program=cd["class_program"],
                date=cd["date"],
                session=cd["session"],
                defaults={"status": cd["status"], "marked_by": request.user},
            )
            if not created and att.status != cd["status"]:
                AttendanceLog.objects.create(
                    school = self.get_school(),
                    attendance=att,
                    previous_status=att.status,
                    new_status=cd["status"],
                    changed_by=request.user,
                )
                att.status = cd["status"]
                att.marked_by = request.user
                att.save(update_fields=["status", "marked_by"])
                updates += 1

        messages.success(request, f"Updated {updates} records to {cd['status']}.")
        return JsonResponse({"ok": True, "updated": updates})


class AttendanceHistoryView(RoleRequiredMixin, UserScopedMixin, ListView):
    model = AttendanceLog
    template_name = "attendance/attendance_history.html"
    context_object_name = "logs"
    allowed_roles = ["SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER"]
    paginate_by = 100  # safe default for long histories

    def get_queryset(self):
        student_id = self.kwargs["student_id"]
        school = self.get_school()

        qs = AttendanceLog.objects.filter(
            attendance__student_id=student_id,
            school=school
        ).select_related(
            "attendance",
            "changed_by",
            "attendance__student",
            "attendance__class_program"
        ).order_by("-changed_at")

        # Filters from GET
        start = self.request.GET.get("start")
        end = self.request.GET.get("end")
        status = self.request.GET.get("status")

        if start:
            try:
                qs = qs.filter(changed_at__date__gte=start)
            except Exception:
                pass
        if end:
            try:
                qs = qs.filter(changed_at__date__lte=end)
            except Exception:
                pass
        if status:
            qs = qs.filter(new_status__iexact=status)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        daily_last_status = {}
        logs_qs = self.get_queryset()
        for log in logs_qs.order_by('changed_at'):
            day = log.changed_at.date()
            daily_last_status[day] = log.new_status  # overwrite previous, so latest stays

        # Count stats
        from collections import Counter
        stats_counter = Counter(daily_last_status.values())
        ctx["stats"] = {
            "present": stats_counter.get("PRESENT", 0),
            "absent": stats_counter.get("ABSENT", 0),
            "late": stats_counter.get("LATE", 0),
            "half_day": stats_counter.get("HALF_DAY", 0),
            "total": len(daily_last_status),
        }


        # Keep original GET filter values to re-populate the controls
        ctx["filter_start"] = self.request.GET.get("start", "")
        ctx["filter_end"] = self.request.GET.get("end", "")
        ctx["filter_status"] = self.request.GET.get("status", "")

        return ctx
    

class RosterApiView(RoleRequiredMixin, View):
    """Return roster for a class + date + session with current attendance statuses."""
    allowed_roles = ["SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER"]

    def get(self, request, *args, **kwargs):
        school = request.user.school
        class_id = request.GET.get("class_program_id")
        dt = request.GET.get("date")
        session = request.GET.get("session") or None
        if not (class_id and dt):
            return HttpResponseBadRequest("class_program_id and date are required.")

        class_program = get_object_or_404(ClassProgram, pk=class_id, school=school)
        students = Student.objects.filter(class_program=class_program, school=school).order_by("full_name")

        # Fetch existing attendance for this date/session
        att_map = {
            (a.student_id): a.status
            for a in Attendance.objects.filter(
                class_program=class_program, date=dt, session=session
            ).only("student_id", "status")
        }

        payload = [
            {"id": s.id, "name": f"{s.full_name}", "status": att_map.get(s.id)}
            for s in students
        ]
        return JsonResponse(payload, safe=False)


import json
from django.views.generic import TemplateView, View
from django.db.models import Count, Q, F
from django.http import JsonResponse
from .models import Attendance
from students.models import Student
from classes_app.models import ClassProgram, Division

class AttendanceAnalyticsView(RoleRequiredMixin, UserScopedMixin, TemplateView):
    template_name = "attendance/analytics_dashboard.html"

class AttendanceAnalyticsView(UserScopedMixin, TemplateView):
    template_name = "attendance/analytics_dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        school = self.get_school()  # from UserScopedMixin

        start = self.request.GET.get("start")
        end   = self.request.GET.get("end")
        cid   = self.request.GET.get("class_id")
        did   = self.request.GET.get("division_id")

        qs = Attendance.objects.all()
        if school:
            qs = qs.filter(school=school)

        # Apply GET filters
        if did:
            qs = qs.filter(class_program__division_id=did)
        if cid:
            qs = qs.filter(class_program_id=cid)
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)

        # --- Summary cards ---
        total_students = qs.values("student").distinct().count()
        attended = qs.filter(status="PRESENT").count()
        total_records = qs.count()
        avg_att = round((attended / total_records) * 100, 1) if total_records else 0
        absences = qs.filter(status="ABSENT").count()
        lates = qs.filter(status="LATE").count()
        half_days = qs.filter(status="HALF_DAY").count()

        # Only divisions and classes within the school
        allowed_divisions = Division.objects.filter(school=school) if school else Division.objects.all()
        allowed_classes   = ClassProgram.objects.filter(school=school) if school else ClassProgram.objects.all()

        ctx.update({
            "total_students": total_students,
            "avg_attendance": avg_att,
            "total_absences": absences,
            "late_count": lates,
            "half_day_count": half_days,
            "classes": allowed_classes,
            "divisions": allowed_divisions,
        })
        return ctx


class AttendanceAnalyticsDataView(View):
    """
    Returns JSON for:
      • summary: key counts for cards & pills
      • trend: daily attendance %
      • stacked: counts per status over time
      • top_absent: list of top‐5 absentees
    """
    def get(self, request):
        start = request.GET.get("start")
        end   = request.GET.get("end")
        cid   = request.GET.get("class_id")
        qs    = Attendance.objects.all()

        if cid:
            qs = qs.filter(class_program_id=cid)
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)

        # --- SUMMARY ---
        total_students = qs.values("student").distinct().count()
        present_count  = qs.filter(status="PRESENT").count()
        total_records  = qs.count()
        avg_att        = round((present_count / total_records) * 100, 1) if total_records else 0
        absences_count = qs.filter(status="ABSENT").count()
        late_count     = qs.filter(status="LATE").count()
        half_day_count = qs.filter(status="HALF_DAY").count()

        # --- TREND: daily attendance % ---
        daily = (
          qs.values("date")
            .annotate(
              present=Count("id", filter=Q(status="PRESENT")),
              total=Count("id")
            )
            .order_by("date")
        )
        trend_labels = [d["date"].isoformat() for d in daily]
        trend_values = [
          round(d["present"] / d["total"] * 100, 1) if d["total"] else 0
          for d in daily
        ]

        # --- STACKED: counts per status by date ---
        statuses = ["PRESENT","ABSENT","LATE","HALF_DAY"]
        stacked = {s: [] for s in statuses}
        for d in daily:
            for s in statuses:
                stacked[s].append(
                  qs.filter(date=d["date"], status=s).count()
                )

        # --- TOP ABSENT STUDENTS ---
        top_absent = (
          qs.filter(status="ABSENT")
            .values(name=F("student__full_name"))
            .annotate(absences=Count("id"))
            .order_by("-absences")[:5]
        )

        return JsonResponse({
          "summary": {
            "students":  total_students,
            "present":   present_count,
            "absences":  absences_count,
            "late":      late_count,
            "half_day":  half_day_count,
            "avg":       avg_att,
            "total":     total_records
          },
          "trend": {
            "labels": trend_labels,
            "values": trend_values
          },
          "stacked": {
            "labels":   trend_labels,
            "datasets": [
              {"label": s, "data": stacked[s]}
              for s in statuses
            ]
          },
          "top_absent": list(top_absent),
        })
class StudentAttendanceAnalyticsView(AttendanceAnalyticsView):
    """
    Same dashboard, filtered to one student
    """
    def get_context_data(self, **kwargs):
        self.student_id = kwargs["student_id"]
        ctx = super().get_context_data(**kwargs)
        ctx["student"] = Student.objects.get(pk=self.student_id)
        return ctx
