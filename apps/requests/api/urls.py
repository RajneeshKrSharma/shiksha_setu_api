from django.urls import path

from .views import (
    LeaveCreateView,
    MeetingCreateView,
    RequestApproveView,
    RequestDetailView,
    RequestListView,
    RequestRejectView,
)

urlpatterns = [
    path("requests/", RequestListView.as_view()),
    path("requests/leaves/", LeaveCreateView.as_view()),
    path("requests/meetings/", MeetingCreateView.as_view()),
    path("requests/<uuid:request_id>/", RequestDetailView.as_view()),
    path("requests/<uuid:request_id>/approve/", RequestApproveView.as_view()),
    path("requests/<uuid:request_id>/reject/", RequestRejectView.as_view()),
]
