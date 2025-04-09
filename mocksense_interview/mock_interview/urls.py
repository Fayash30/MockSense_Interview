from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="mock_interview_index"),
    path('start/', views.start_interview, name='start_interview'),
    path('quiz/', views.quiz_view, name='mock_interview_quiz'),
    path('video_feed/', views.video_feed, name='mock_interview_video_feed'),
     path("save_answer/", views.save_answer, name="save_answer"),
    path('listen/', views.listen_answer, name='mock_interview_listen'),
    path('result/', views.mock_interview_result, name='mock_interview_result'),  # Add this line
    path("upload_resume/", views.upload_resume, name="upload_resume"),
    path("resume_uploading/", views.resume_uploading, name="resume_uploading"),
    path("limit-exceeded/", views.limit_exceeded, name="limit_exceeded"),
    path("process_frame/", views.process_frame, name="process_frame"),
    path("detect_emotion/", views.detect_emotion, name="detect_emotion"),
]
