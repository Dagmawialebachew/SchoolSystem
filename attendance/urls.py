# attendance_app/urls.py
from django.urls import path
from .views import (
    AttendanceListView,
    AttendanceEditView,
    AttendanceBulkMarkPresentView,
    AttendanceBulkMarkStatusView,
    AttendanceHistoryView,
    RosterApiView,
    AttendanceAnalyticsView,
    AttendanceAnalyticsDataView,
    StudentAttendanceAnalyticsView,
)

app_name = "attendance"

urlpatterns = [
    path("", AttendanceListView.as_view(), name="list"),
    path("edit/", AttendanceEditView.as_view(), name="edit"),
    path("bulk/present/", AttendanceBulkMarkPresentView.as_view(), name="bulk_present"),
    path("bulk/status/", AttendanceBulkMarkStatusView.as_view(), name="bulk_status"),
    path("history/<int:student_id>/", AttendanceHistoryView.as_view(), name="history"),
    path("api/roster/", RosterApiView.as_view(), name="roster_api"), 
    
    path(
        "analytics/",
        AttendanceAnalyticsView.as_view(),
        name="attendance_analytics"
    ),
    path(
        "analytics/data/",
        AttendanceAnalyticsDataView.as_view(),
        name="attendance_analytics_data"
    ),
    path(
        "analytics/student/<int:student_id>/",
        StudentAttendanceAnalyticsView.as_view(),
        name="student_attendance_analytics"
    ),# class/date/session → students + current status
]
