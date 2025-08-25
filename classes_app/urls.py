from django.urls import path
from . import views

app_name = 'classes_app'

urlpatterns = [
    path('', views.class_list, name='list'),
]