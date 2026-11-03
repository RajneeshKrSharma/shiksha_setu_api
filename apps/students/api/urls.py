from django.urls import path

from .views import (
    ClassDetailView,
    ClassListCreateView,
    FeeAccountListView,
    FeeAmountView,
    FeePaymentListCreateView,
    FeeStructureView,
    IssueListCreateView,
    ItemDetailView,
    ItemListCreateView,
    StudentDetailView,
    StudentFeesView,
    StudentListCreateView,
)

urlpatterns = [
    path("classes/", ClassListCreateView.as_view()),
    path("classes/<uuid:class_id>/", ClassDetailView.as_view()),
    path("students/", StudentListCreateView.as_view()),
    path("students/<uuid:student_id>/", StudentDetailView.as_view()),
    path("students/<uuid:student_id>/fees/", StudentFeesView.as_view()),
    path("accessories/items/", ItemListCreateView.as_view()),
    path("accessories/items/<uuid:item_id>/", ItemDetailView.as_view()),
    path("accessories/issues/", IssueListCreateView.as_view()),
    path("fees/structure/", FeeStructureView.as_view()),
    path("fees/structure/<uuid:class_id>/<str:head>/", FeeAmountView.as_view()),
    path("fees/accounts/", FeeAccountListView.as_view()),
    path("fees/payments/", FeePaymentListCreateView.as_view()),
]
