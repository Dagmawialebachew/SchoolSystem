from django.urls import path
from . import views, api
from .views import (
    ParentDashboardView,
    ChildDetailView,
    ChildAttendanceListView,
    KidsView, FeesView, ChildFeesDetailView, ParentReportsView, ParentProfileView, EditParentProfileView
)

app_name = "parents"

urlpatterns = [
    # /parents/dashboard/
    path("dashboard/", ParentDashboardView.as_view(), name="dashboard"),
    path("kids/", KidsView.as_view(), name="kids"),
    # /parents/child/123/ → detail page
    path("kids/<int:pk>/", ChildDetailView.as_view(), name="child_detail"),
        path("fees/", FeesView.as_view(), name="fees"),
    # /parents/child/123/attendance/
    path(
      "child/<int:pk>/attendance/",
      ChildAttendanceListView.as_view(),
      name="attendance_list"
    ),
        path("fees/child/<int:pk>/", ChildFeesDetailView.as_view(), name="child_fees_detail"),
    path('fees/<int:pk>/process-payment/', views.ProcessPaymentView.as_view(), name='process_payment'), 
        path("reports/", ParentReportsView.as_view(), name="parent-reports"),
 path("profile/", ParentProfileView.as_view(), name="profile"),
    path("profile/edit/", EditParentProfileView.as_view(), name="edit_profile"),
     path("api/save_chat_id/", api.save_chat_id, name="save_chat_id"),


]
