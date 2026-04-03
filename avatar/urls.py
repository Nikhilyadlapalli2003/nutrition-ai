from django.urls import path
from . import views

app_name = 'avatar'

urlpatterns = [
    path('chat/', views.chat_api, name='chat_api'),
]
