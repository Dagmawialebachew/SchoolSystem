from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from students.models import Student
from teachers.models import Teacher
from classes_app.models import ClassProgram
from fees.models import Payment
from attendance.models import Attendance
from notifications.models import Announcement
from core.mixins import RoleRequiredMixin
from django.views.generic import TemplateView


class TeacherDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboard/teacher.html'
    allowed_roles = ['TEACHER']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Today's classes
        context['todays_classes'] = ClassProgram.objects.for_user(user).filter(
            teachers=user.id
        )[:5]
        
        # Recent announcements
        context['announcements'] = Announcement.objects.for_user(user).filter(
            target__in=['ALL', 'TEACHERS']
        )[:5]
        
        return context
class SchoolAdminDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboard/school_admin.html'
class ParentDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboard/parent.html'
    allowed_roles = ['PARENT']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get children (assuming parent_name matches user's full name)
        children = Student.objects.for_user(user).filter(
            parent_name__icontains=user.get_full_name()
        )
        context['children'] = children
        
        if children.exists():
            child = children.first()
            # Last 5 attendance records
            context['recent_attendance'] = Attendance.objects.for_user(user).filter(
                student=child
            ).order_by('-date')[:5]
            
            # Next payment
            context['next_payment'] = Payment.objects.for_user(user).filter(
                student=child,
                status='PENDING'
            ).order_by('due_date').first()
        
        return context
    allowed_roles = ['SCHOOL_ADMIN']
    
@login_required
def dashboard(request):
    """Redirect to appropriate dashboard based on user role"""
    if request.user.is_school_admin():
        return SchoolAdminDashboardView.as_view()(request)
    elif request.user.is_teacher():
        return TeacherDashboardView.as_view()(request)
    elif request.user.is_parent():
        return ParentDashboardView.as_view()(request)
    else:
        context = {'user': request.user}
        return render(request, 'dashboard/dashboard.html', context)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
# API endpoints for charts
@login_required
def fees_status_chart(request):
    """JSON endpoint for fees status donut chart"""
    if not request.user.is_school_admin():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    data = Payment.objects.for_user(request.user).values('status').annotate(
        count=Count('id')
    )
    
    chart_data = {
        'labels': [item['status'] for item in data],
        'data': [item['count'] for item in data]
    }
    
    return JsonResponse(chart_data)
        user = self.request.user
        
@login_required
def monthly_collections_chart(request):
    """JSON endpoint for monthly collections line chart"""
    if not request.user.is_school_admin():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Get last 6 months data
    today = timezone.now().date()
    months_data = []
    
    for i in range(6):
        month_start = (today.replace(day=1) - timedelta(days=30*i))
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        total = Payment.objects.for_user(request.user).filter(
            paid_at__date__range=[month_start, month_end],
            status='PAID'
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
        # KPIs
        context['total_students'] = Student.objects.for_user(user).count()
@login_required
def students_by_class_chart(request):
    """JSON endpoint for students by class bar chart"""
    if not request.user.is_school_admin():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    data = ClassProgram.objects.for_user(request.user).annotate(
        student_count=Count('students')
    ).values('name', 'student_count')
    
    chart_data = {
        'labels': [item['name'] for item in data],
        'data': [item['student_count'] for item in data]
    }
    
    return JsonResponse(chart_data)
        context['total_teachers'] = Teacher.objects.for_user(user).count()
        context['total_classes'] = ClassProgram.objects.for_user(user).count()
        
        # Fees due this month
        today = timezone.now().date()
        month_start = today.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        context['fees_due_this_month'] = Payment.objects.for_user(user).filter(
            due_date__range=[month_start, month_end],
            status='PENDING'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return context