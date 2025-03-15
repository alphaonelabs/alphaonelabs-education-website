from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    path('chat/', views.chat_view, name='chat'),
    path('chat/completion/', views.chat_completion, name='chat_completion'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('progress/', views.progress_view, name='progress'),
    path('settings/', views.settings_view, name='settings'),
]
