from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('<int:course_id>/', views.course_detail, name='course_detail'),
    path('<int:course_id>/enroll/', views.course_enroll, name='course_enroll'),
    path('<int:course_id>/lessons/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
] 