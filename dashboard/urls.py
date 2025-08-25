from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('teacher-dashboard/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('parent-dashboard/', views.ParentDashboardView.as_view(), name='parent_dashboard'),
    
    # API endpoints for charts
    path('api/charts/fees-status/', views.fees_status_chart, name='fees_status_chart'),
    path('api/charts/monthly-collections/', views.monthly_collections_chart, name='monthly_collections_chart'),
    path('api/charts/students-by-class/', views.students_by_class_chart, name='students_by_class_chart'),
]