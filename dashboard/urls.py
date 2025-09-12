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
    path('api/charts/students-by-division/', views.students_by_division_chart, name='students_by_division_chart'),
    path('api/revenue-trend/', views.revenue_trend_chart, name='revenue_trend_chart'),
    path('api/invoice-status/', views.invoice_status_chart, name='invoice_status_chart'),
    path('api/summary/', views.fees_summary_api, name = 'summary_api')
]