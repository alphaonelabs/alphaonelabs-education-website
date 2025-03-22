from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    path('chat/', views.chat_view, name='chat'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('api/question/', views.chat_completion, name='ask_question'),
    path('api/rate/<int:interaction_id>/', views.rate_interaction, name='rate_interaction'),
    path('api/save_chat/', views.save_chat, name='save_chat'),
    path('api/get_chat/', views.get_chat, name='get_chat'),
    path('progress/', views.progress_view, name='progress'),
    path('settings/', views.settings_view, name='settings'),
    path('tutor/', views.tutor_view, name='tutor'),
    path('api/tutor/', views.tutor_completion, name='ask_tutor'),
]
