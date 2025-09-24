from django.urls import path
from . import views

app_name = 'teachers'

urlpatterns = [
    path('', views.TeacherListView.as_view(), name='list'),
    path('add/', views.TeacherCreateView.as_view(), name='add'),
    path("<int:pk>/", views.TeacherDetailView.as_view(), name="detail"),
    path('<int:pk>/edit/', views.TeacherUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.TeacherDeleteView.as_view(), name='delete'),
]