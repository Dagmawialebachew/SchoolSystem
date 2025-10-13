from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('landing/', TemplateView.as_view(template_name="landing.html"), name="landing"),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('onboarding/', include('onboarding.urls')),
    path('schools/', include('schools.urls')),
    path('students/', include('students.urls')),
    path('teachers/', include('teachers.urls')),
    path('classes/', include('classes_app.urls')),
    path('attendance/', include('attendance.urls')),
    path('fees/', include('fees.urls')),
    path('parents/', include('parents.urls')),
    path('documents/', include('documents.urls')),
    path('notifications/', include('notifications.urls')),
    path("__reload__/", include("django_browser_reload.urls")),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)