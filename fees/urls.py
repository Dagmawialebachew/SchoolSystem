from django.urls import path
from . import views

app_name = 'fees'

urlpatterns = [
    path('', views.payment_list, name='list'),
]