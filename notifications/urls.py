# notifications/urls.py
from django.urls import path
from . import views
from .views import AnnouncementCreateView, AnnouncementListView, AnnouncementAnalyticsView

app_name = "notifications"

urlpatterns = [
    path('create/', AnnouncementCreateView.as_view(), name='create'),
    path('list/', AnnouncementListView.as_view(), name='list'),
    path('analytiics', AnnouncementAnalyticsView.as_view(), name = 'analytics'),
    path("<int:pk>/read/", views.mark_read, name="mark_read"),
    path("<int:pk>/react/", views.toggle_reaction, name="toggle_reaction"),
    path("page/", views.announcements_page, name="page"),
    path("unread-count/", views.unread_count, name="unread_count"),  
     path("<int:pk>/edit/", views.AnnouncementUpdateView.as_view(), name="announcement_edit"),
    path("<int:pk>/delete/", views.AnnouncementDeleteView.as_view(), name="announcement_delete"),# 👈 AJAX endpoint
]
