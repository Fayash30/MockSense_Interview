from django.urls import path
from . import views

urlpatterns = [
    path("quiz-view/", views.quiz_view, name="quiz_view"),
    path("quiz-questions/", views.quiz_questions, name="quiz_questions"),
    path("get-questions/", views.get_questions, name="get_questions"),           
    path("submit-answers/", views.submit_answers, name="submit_answers"),        
    path("quiz-result/", views.quiz_result, name="quiz_result"),
    path("api/store-screenshot/", views.store_violation_screenshot, name="store_screenshot"),
]