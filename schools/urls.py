# schools/urls.py
from django.urls import path
from .views import (
    SchoolListView, SchoolCreateView, SchoolUpdateView,
    SchoolDeleteView, SchoolDetailView
)

app_name = "schools"

urlpatterns = [
    path("", SchoolListView.as_view(), name="list"),
    path("create/", SchoolCreateView.as_view(), name="create"),
    path("<int:pk>/", SchoolDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", SchoolUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", SchoolDeleteView.as_view(), name="delete"),
]
