from django.urls import path

from .views import (
    ExamAveragesView,
    FeeReportView,
    FuelView,
    LessonCoverageView,
    PaymentsView,
    StaffAttendanceView,
    StudentAttendanceView,
)

urlpatterns = [
    path("analytics/students/attendance/", StudentAttendanceView.as_view()),
    path("analytics/students/fees/", FeeReportView.as_view()),
    path("analytics/students/exams/", ExamAveragesView.as_view()),
    path("analytics/staff/attendance/", StaffAttendanceView.as_view()),
    path("analytics/staff/payments/", PaymentsView.as_view()),
    path("analytics/staff/fuel/", FuelView.as_view()),
    path("analytics/teachers/lessons/", LessonCoverageView.as_view()),
]
