from django.urls import path

from .views import (
    HolidayDetailView,
    HolidayListCreateView,
    NoticeDetailView,
    NoticeListCreateView,
    SchoolView,
    SeasonScheduleView,
    TimingsView,
)

urlpatterns = [
    path("school/", SchoolView.as_view()),
    path("school/timings/", TimingsView.as_view()),
    path("school/timings/<str:season>/", SeasonScheduleView.as_view()),
    path("school/holidays/", HolidayListCreateView.as_view()),
    path("school/holidays/<uuid:holiday_id>/", HolidayDetailView.as_view()),
    path("notices/", NoticeListCreateView.as_view()),
    path("notices/<uuid:notice_id>/", NoticeDetailView.as_view()),
]
