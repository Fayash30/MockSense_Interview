from django.urls import path
from . import views

urlpatterns = [
    path("quiz-view/", views.quiz_view, name="quiz_view"),
    path("quiz-questions/", views.quiz_questions, name="quiz_questions"),
    path("quiz-result/", views.quiz_result, name="quiz_result"),
]
