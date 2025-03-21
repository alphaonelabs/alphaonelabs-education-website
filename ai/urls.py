from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    path('chat/', views.chat_view, name='chat'),
    path('chat/completion/', views.chat_completion, name='ask_question'),  # Change this path
    path('dashboard/', views.dashboard, name='dashboard'),
    path('progress/', views.progress_view, name='progress'),
    path('settings/', views.settings_view, name='settings'),
    path('tutor/', views.tutor_view, name='tutor'),
    path('api/tutor/', views.tutor_completion, name='ask_tutor'),
]
