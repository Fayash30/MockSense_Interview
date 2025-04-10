from django.urls import path
from . import views

urlpatterns = [
    path('take-test/', views.quiz_view, name='take-mcq'),
    path('get-questions/', views.get_questions, name='get_questions'),
    path('submit-answers/', views.submit_answers, name='submit_answers'),
    path('mcq-result/', views.quiz_result_view, name='mcq_result'),
    path('', views.quiz_home, name='mcq-home'),
]
