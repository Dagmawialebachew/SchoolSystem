from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.announcement_list, name='list'),
]