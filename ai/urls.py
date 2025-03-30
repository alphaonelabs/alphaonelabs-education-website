from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'ai'

urlpatterns = [
    # Main views
    path('chat/', views.chat_view, name='chat'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('progress/', views.progress_view, name='progress'),
    path('settings/', views.settings_view, name='settings'),
    path('tutor/', views.tutor_view, name='tutor'),
    
    # New AI-powered learning features
    path('study-planner/', views.study_planner_view, name='study_planner'),
    path('progress-dashboard/', views.progress_dashboard_view, name='progress_dashboard'),
    path('achievements/', views.achievements_view, name='achievements'),
    path('group-discussions/', views.group_discussions_view, name='group_discussions'),
    
    # Learning Style Identification
    path('learning-style/', views.learning_style_view, name='learning_style'),
    path('identify-learning-style/', views.identify_learning_style, name='identify_learning_style'),
    
    # Instant Feedback
    path('feedback/', views.feedback_view, name='feedback'),
    path('provide-feedback/', views.provide_feedback, name='provide_feedback'),
    path('rate-feedback/', views.rate_feedback, name='rate_feedback'),
    
    # Personalized Learning Paths
    path('learning-path/', views.learning_path_view, name='learning_path'),
    path('create-learning-path/', views.create_learning_path, name='create_learning_path'),
    path('learning-path/<int:path_id>/', views.get_learning_path, name='get_learning_path'),
    path('learning-path/<int:path_id>/details/', views.learning_path_details_view, name='learning_path_details'),
    
    # Student Progress Dashboard
    path('dashboard/', views.get_dashboard, name='get_dashboard'),
    path('update-dashboard-metrics/', views.update_dashboard_metrics, name='update_dashboard_metrics'),
    
    # API endpoints
    path('api/question/', views.tutor_completion, name='ask_question'),
    path('api/rate/<int:interaction_id>/', views.rate_interaction, name='rate_interaction'),
    path('api/save_chat/', views.save_chat, name='save_chat'),
    path('api/get_chat/', views.get_chat, name='get_chat'),
    path('api/tutor/', views.tutor_completion, name='ask_tutor'),
    path('api/send_message/', views.send_message, name='send_message'),
    path('api/clear_chat/', views.clear_chat, name='clear_chat'),
    
    # New API endpoints
    path('api/study-plan/create/', views.create_study_plan, name='create_study_plan'),
    path('api/study-plan/<int:plan_id>/', views.get_study_plan, name='get_study_plan'),
    path('api/study-plan/<int:plan_id>/update/', views.update_study_plan, name='update_study_plan'),
    path('api/study-plan/<int:plan_id>/delete/', views.delete_study_plan, name='delete_study_plan'),
    path('api/progress/update/', views.update_progress, name='update_progress'),
    path('api/achievements/unlock/', views.unlock_achievement, name='unlock_achievement'),
    path('api/group-discussion/create/', views.create_discussion, name='create_discussion'),
    path('api/group-discussion/<int:discussion_id>/', views.get_group_discussion, name='get_group_discussion'),
    path('api/group-discussion/<int:discussion_id>/reply/', views.create_discussion_reply, name='create_discussion_reply'),
    
    # Study Tasks URLs
    path('api/study-plan/<int:plan_id>/generate-tasks/', views.generate_study_tasks, name='generate_study_tasks'),
    path('api/study-task/<int:task_id>/toggle/', views.toggle_task_completion, name='toggle_task_completion'),
    path('api/study-plan/<int:plan_id>/tasks/', views.get_study_tasks, name='get_study_tasks'),
    
    # Redirects
    path('', RedirectView.as_view(pattern_name='ai:chat'), name='index'),
]
