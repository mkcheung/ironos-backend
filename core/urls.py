from django.urls import include, path

from . import views

urlpatterns = [
    path('health/', views.health_check),
    path('', include('training.urls')),
    path('', include('training.urls_health')),
]
