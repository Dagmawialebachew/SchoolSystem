from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Sum, Q, F
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from students.models import Student
from schools.models import School
from teachers.models import Teacher
from classes_app.models import ClassProgram, Division
from fees.models import Payment, Invoice
from attendance.models import Attendance
from notifications.models import Announcement
from core.mixins import RoleRequiredMixin
from django.views.generic import TemplateView
from django.utils.timezone import now
from accounts.models import User
from fees.models import Invoice, Payment
from django.db.models.functions import TruncMonth

class TeacherDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboard/teacher.html'
    allowed_roles = ['TEACHER']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Today's classes (no need to filter again by user.id)
        context['todays_classes'] = ClassProgram.objects.for_user(user)[:5]
        
        # Recent announcements
        context['announcements'] = Announcement.objects.for_user(user).filter(
            target__in=['ALL', 'TEACHERS']
        )[:5]

        return context

class SchoolAdminDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboard/school_admin.html'
    allowed_roles = ['SCHOOL_ADMIN']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['total_students'] = Student.objects.for_user(user).count()
        context['total_teachers'] = Teacher.objects.for_user(user).count()
        context['total_classes'] = ClassProgram.objects.for_user(user).count()

        # Fees due this month
        today = timezone.now().date()
        month_start = today.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        context['fees_due_this_month'] = Invoice.objects.for_user(user).filter(
    due_date__month=today.month,
    due_date__year=today.year).aggregate(total=Sum('amount_due'))['total'] or 0

        return context


class ParentDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboard/parent.html'
    allowed_roles = ['PARENT']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        children = Student.objects.for_user(user).filter(
            parent_name__icontains=user.get_full_name()
        )
        context['children'] = children

        if children.exists():
            child = children.first()
            context['recent_attendance'] = Attendance.objects.for_user(user).filter(
                student=child
            ).order_by('-date')[:5]

            context['next_payment'] = Payment.objects.for_user(user).filter(
                student=child,
                status='PENDING'
            ).order_by('due_date').first()
        return context


class AdminDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "dashboard/admin_home.html"
    allowed_roles = ["SUPER_ADMIN"]   # or "OWNER" depending on your roles

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # All schools overview
        ctx["schools_count"] = School.objects.count()
        ctx["teachers_count"] = Teacher.objects.count()
        ctx["students_count"] = Student.objects.count()
        ctx["classes_count"] = ClassProgram.objects.count()

        # Finance overview
        invoices = Invoice.objects.all()
        payments = Payment.objects.all()

        ctx["total_due"] = invoices.aggregate(total=Sum("amount_due"))["total"] or 0
        ctx["total_paid"] = invoices.aggregate(total=Sum("amount_paid"))["total"] or 0
        ctx["overdue"] = invoices.filter(due_date__lt=now().date()).exclude(status="PAID").count()

        # Users by role
        ctx["users_by_role"] = User.objects.values("role").annotate(count=Count("id"))

        # Announcements
        ctx["recent_announcements"] = Announcement.objects.all()[:5]

        return ctx

@login_required
def dashboard(request):
    """Redirect to appropriate dashboard based on user role"""
    if request.user.is_school_admin():
        return SchoolAdminDashboardView.as_view()(request)
    elif request.user.is_teacher():
        return TeacherDashboardView.as_view()(request)
    elif request.user.is_parent():
        return redirect('parents:dashboard')
    elif request.user.role == "SUPER_ADMIN":
        return AdminDashboardView.as_view()(request)
    

# ------------------ API Endpoints ------------------ #

@login_required
def fees_status_chart(request):
    # if not request.user.is_school_admin():
    #     return JsonResponse({'error': 'Unauthorized'}, status=403)

    data = Invoice.objects.for_user(request.user).values('status').annotate(
        count=Count('id')
    )
    chart_data = {
        'labels': [item['status'] for item in data],
        'data': [item['count'] for item in data]
    }
    
    if not chart_data['data']:
        chart_data = {
            'labels': ['No Data'],
            'data': [0]
        }
    return JsonResponse(chart_data)

from datetime import date
@login_required
def monthly_collections_chart(request):
    # if not request.user.is_school_admin():
    #     return JsonResponse({'error': 'Unauthorized'}, status=403)

    today = timezone.now().date()
    months_data = []
    for i in range(8):
        month_start = (today.replace(day=1) - timedelta(days=30 * i))
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        total = Payment.objects.filter(
            invoice__school=request.user.school,
            paid_on__date__range=[month_start, month_end], status = 'CONFIRMED'
        ).aggregate(total=Sum('amount'))['total'] or 0
                

        months_data.append({
            'month': month_start.strftime('%b %Y'),
            'total': float(total)
        })

    months_data.reverse()
    chart_data = {
        'labels': [item['month'] for item in months_data],
        'data': [item['total'] for item in months_data]
    }
    

    return JsonResponse(chart_data)


@login_required
def students_by_division_chart(request):
    # if not request.user.is_school_admin():
    #     return JsonResponse({'error': 'Unauthorized'}, status=403)

    data = Division.objects.for_user(request.user).annotate(
        student_count=Count('students')
    ).values('name', 'student_count')

    chart_data = {
        'labels': [item['name'] for item in data],
        'data': [item['student_count'] for item in data]
    }
    return JsonResponse(chart_data)




@login_required
def revenue_trend_chart(request):
    # if not request.user.is_school_admin():
    #     return JsonResponse({'error': 'Unauthorized'}, status=403)

    payments = (
        Payment.objects.filter(school=request.user.school, status = 'CONFIRMED')
        .annotate(month=TruncMonth('paid_on'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )

    chart_data = {
        'labels': [p['month'].strftime("%b %Y") for p in payments],
        'data': [p['total'] for p in payments]
    }
    if not chart_data['data']:
        chart_data = {
            'labels': ['No Data'],
            'data': [0]
        }
    return JsonResponse(chart_data)


@login_required
def invoice_status_chart(request):
    # if not request.user.is_school_admin():
    #     return JsonResponse({'error': 'Unauthorized'}, status=403)

    total_paid = Invoice.objects.filter(status='PAID', school=request.user.school).count()
    total_unpaid = Invoice.objects.filter(status='UNPAID', school=request.user.school).count()
    total_opening_balance = Invoice.objects.filter(status='OPENING_BALANCE', school=request.user.school).count()
    chart_data = {
        'labels': ['Paid', 'Unpaid', 'Opening Balance'],
        'data': [total_paid, total_unpaid, total_opening_balance]
    }
    
    if not chart_data['data']:
        chart_data = {
            'labels': ['No Data'],
            'data': [0]
        }
    return JsonResponse(chart_data)


#For the Summary


@login_required
def fees_summary_api(request):
    """Return summary metrics for dashboard cards."""
    # if not request.user.is_school_admin():
    #     return JsonResponse({'error': 'Unauthorized'}, status=403)

    total_revenue = Payment.objects.filter(school = request.user.school, status = 'CONFIRMED').aggregate(total=Sum('amount'))['total'] or 0
    paid_invoices = Invoice.objects.filter(payments__status='CONFIRMED', school = request.user.school).count()
    unconfirmed_invoices = Invoice.objects.filter(
        school=request.user.school, status = 'PAID'
    ).exclude(
        payments__status='CONFIRMED'
    ).distinct().count()    
    pending_invoices = Invoice.objects.filter(status='UNPAID', school = request.user.school).count()
    total_unpaid = Invoice.objects.filter(status='UNPAID', school = request.user.school).aggregate(total = Sum('amount_due'))['total'] or 0
    # total_unpaid = Invoice.objects.filter(~Q(status='UNPAID'), school = request.user.school).aggregate(
    #     total=Sum('amount_due'))['total'] or 0

    data = {
        "total_revenue": total_revenue,
        "paid_invoices": paid_invoices,
        "unconfirmed_invoices": unconfirmed_invoices,
        "pending_invoices": pending_invoices,
        "total_unpaid": total_unpaid
    }
    return JsonResponse(data)

