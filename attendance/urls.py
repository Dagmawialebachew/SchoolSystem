# attendance/urls.py
from django.urls import path
from .views import (
    ClassSessionList,
    AttendanceMarkView,
    AttendanceToggleView,
    AttendanceListView
)

app_name = "attendance"

urlpatterns = [
    path("", AttendanceListView.as_view(), name="list"),  
    path("class-sessions/", ClassSessionList.as_view(), name="class-sessions"),
    path("mark/<int:pk>/", AttendanceMarkView.as_view(), name="mark"),
    path("toggle/<int:pk>/", AttendanceToggleView.as_view(), name="toggle"),

]
