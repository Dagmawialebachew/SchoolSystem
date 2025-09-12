from django.urls import path
from .views import (
    SchoolSetupView, DivisionSetupView,
 FeeSetupView
)

app_name = "onboarding"

urlpatterns = [
    path("school/", SchoolSetupView.as_view(), name="school_setup"),
    path("division/", DivisionSetupView.as_view(), name="division_setup"),
    path("fees/", FeeSetupView.as_view(), name="fees_setup"),
]
