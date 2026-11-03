from django.urls import path

from .views import (
    AllotmentDetailView,
    AllotmentListCreateView,
    LessonBoardView,
    LessonDetailView,
    LessonListCreateView,
    TeacherDetailView,
    TeacherListCreateView,
)

urlpatterns = [
    path("teachers/", TeacherListCreateView.as_view()),
    path("teachers/<uuid:teacher_id>/", TeacherDetailView.as_view()),
    path("teaching/allotments/", AllotmentListCreateView.as_view()),
    path("teaching/allotments/<uuid:allotment_id>/", AllotmentDetailView.as_view()),
    path("teaching/lessons/", LessonListCreateView.as_view()),
    path("teaching/lessons/board/", LessonBoardView.as_view()),
    path("teaching/lessons/<uuid:lesson_id>/", LessonDetailView.as_view()),
]
