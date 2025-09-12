# notifications/urls.py
from django.urls import path
from .views import AnnouncementCreateView, AnnouncementListView

app_name = "notifications"

urlpatterns = [
    path('create/', AnnouncementCreateView.as_view(), name='create'),
    path('list/', AnnouncementListView.as_view(), name='list'),
]
