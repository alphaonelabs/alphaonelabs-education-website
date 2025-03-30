from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('<slug:slug>/', views.course_detail, name='course_detail'),
    path('<slug:slug>/enroll/', views.enroll_course, name='enroll_course'),
    path('<slug:slug>/sessions/', views.session_list, name='session_list'),
    path('sessions/<int:session_id>/', views.session_detail, name='session_detail'),
]
