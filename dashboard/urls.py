from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('progress/', views.progress_dashboard_view, name='progress_dashboard'),
]