from django.urls import path

from .views import (
    CheckInView,
    CheckOutView,
    ClassAttendanceView,
    ClassReportView,
    DayBoardView,
    MyAttendanceView,
    WorkRecordsView,
)

urlpatterns = [
    path("attendance/students/", ClassAttendanceView.as_view()),
    path("attendance/students/report/", ClassReportView.as_view()),
    path("attendance/check-in/", CheckInView.as_view()),
    path("attendance/check-out/", CheckOutView.as_view()),
    path("attendance/me/", MyAttendanceView.as_view()),
    path("attendance/people/", DayBoardView.as_view()),
    path("attendance/records/", WorkRecordsView.as_view()),
]
