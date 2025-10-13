from django.urls import path
from .views import (
    ClassListView,
    ClassDetailView,
    ClassCreateView,
    ClassUpdateView,
    ClassDeleteView,
    DivisionListView,
    DivisionDetailView,
    DivisionCreateView,
    DivisionUpdateView,
    DivisionDeleteView,
    DivisionAuditView,
    AssignTeachersView
)

app_name = "classes_app"

urlpatterns = [
    path("", ClassListView.as_view(), name="list"),
    path("<int:pk>/", ClassDetailView.as_view(), name="detail"),
    path("create/", ClassCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", ClassUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", ClassDeleteView.as_view(), name="delete"),
    path("classes/<int:pk>/assign-teachers/", AssignTeachersView.as_view(), name="assign_teachers"),
    path("divisions/", DivisionListView.as_view(), name="division_list"),
    path("divisions/create/", DivisionCreateView.as_view(), name="division_create"),
    path("divisions/<int:pk>/", DivisionDetailView.as_view(), name="division_detail"),
    path("divisions/<int:pk>/edit/", DivisionUpdateView.as_view(), name="division_edit"),
    path("divisions/<int:pk>/delete/", DivisionDeleteView.as_view(), name="division_delete"),
    path("divisions/<int:pk>/audit/", DivisionAuditView.as_view(), name="division_audit"),
]
