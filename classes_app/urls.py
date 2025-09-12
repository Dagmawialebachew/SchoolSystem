from django.urls import path
from .views import (
    ClassListView,
    ClassDetailView,
    ClassCreateView,
    ClassUpdateView,
    ClassDeleteView,
)

app_name = "classes_app"

urlpatterns = [
    path("", ClassListView.as_view(), name="list"),
    path("<int:pk>/", ClassDetailView.as_view(), name="detail"),
    path("create/", ClassCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", ClassUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", ClassDeleteView.as_view(), name="delete"),
]
