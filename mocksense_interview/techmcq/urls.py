from django.urls import path
from . import views

urlpatterns = [
    path('', views.quiz_view, name='mcq-home'),
    path('get-questions/', views.get_questions, name='get_questions'),
    path('submit-answers/', views.submit_answers, name='submit_answers'),
    path('mcq-result/', views.quiz_result_view, name='mcq_result'),
]
