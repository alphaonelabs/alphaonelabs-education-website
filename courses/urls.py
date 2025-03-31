from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('<slug:slug>/', views.course_detail, name='course_detail'),
    path('<slug:slug>/enroll/', views.enroll_course, name='enroll_course'),
    path('<slug:slug>/unenroll/', views.unenroll_course, name='unenroll_course'),
    path('<slug:slug>/edit/', views.edit_course, name='edit_course'),
    path('<slug:slug>/delete/', views.delete_course, name='delete_course'),
    path('<slug:slug>/add-session/', views.add_session, name='add_session'),
    path('<slug:slug>/sessions/<int:session_id>/', views.session_detail, name='session_detail'),
    path('<slug:slug>/sessions/<int:session_id>/edit/', views.edit_session, name='edit_session'),
    path('<slug:slug>/sessions/<int:session_id>/delete/', views.delete_session, name='delete_session'),
    path('<slug:slug>/students/', views.course_students, name='course_students'),
    path('<slug:slug>/students/<int:student_id>/', views.student_detail, name='student_detail'),
    path('<slug:slug>/students/<int:student_id>/progress/', views.student_progress, name='student_progress'),
    path('<slug:slug>/materials/', views.course_materials, name='course_materials'),
    path('<slug:slug>/materials/upload/', views.upload_material, name='upload_material'),
    path('<slug:slug>/materials/<int:material_id>/delete/', views.delete_material, name='delete_material'),
    path('<slug:slug>/materials/<int:material_id>/download/', views.download_material, name='download_material'),
    path('<slug:slug>/reviews/', views.course_reviews, name='course_reviews'),
    path('<slug:slug>/reviews/add/', views.add_review, name='add_review'),
    path('<slug:slug>/reviews/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('<slug:slug>/reviews/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    path('<slug:slug>/analytics/', views.course_analytics, name='course_analytics'),
    path('<slug:slug>/marketing/', views.course_marketing, name='course_marketing'),
] 