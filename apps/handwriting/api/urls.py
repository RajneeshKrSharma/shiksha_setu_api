from django.urls import path

from .views import ReadHandwritingTestView, ReadHandwritingView, TestPageView

urlpatterns = [
    path("handwriting/read/", ReadHandwritingView.as_view()),
    path("handwriting/test/", TestPageView.as_view()),
    path("handwriting/read-test/", ReadHandwritingTestView.as_view()),
]
