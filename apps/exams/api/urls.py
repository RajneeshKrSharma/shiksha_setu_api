from django.urls import path

from .views import (
    ExamDetailView,
    ExamListCreateView,
    ExamMarksView,
    ExamSettingsView,
    ExamPaperView,
    PaperApproveView,
    PaperListView,
    PaperRejectView,
    PaperSendView,
    QuestionDetailView,
    StudentResultsView,
    TimetableView,
    UnitDetailView,
    UnitListCreateView,
    UnitQuestionsView,
)

urlpatterns = [
    path("exams/", ExamListCreateView.as_view()),
    path("exams/papers/", PaperListView.as_view()),
    path("exams/settings/", ExamSettingsView.as_view()),
    path("exams/timetable/", TimetableView.as_view()),
    path("exams/<uuid:exam_id>/", ExamDetailView.as_view()),
    path("exams/<uuid:exam_id>/marks/", ExamMarksView.as_view()),
    path("exams/<uuid:exam_id>/paper/", ExamPaperView.as_view()),
    path("exams/<uuid:exam_id>/paper/send/", PaperSendView.as_view()),
    path("exams/<uuid:exam_id>/paper/approve/", PaperApproveView.as_view()),
    path("exams/<uuid:exam_id>/paper/reject/", PaperRejectView.as_view()),
    path("students/<uuid:student_id>/results/", StudentResultsView.as_view()),
    path("question-bank/units/", UnitListCreateView.as_view()),
    path("question-bank/units/<uuid:unit_id>/", UnitDetailView.as_view()),
    path("question-bank/units/<uuid:unit_id>/questions/", UnitQuestionsView.as_view()),
    path("question-bank/questions/<uuid:question_id>/", QuestionDetailView.as_view()),
]
