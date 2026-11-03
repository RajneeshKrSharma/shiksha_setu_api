from django.urls import path

from .views import (
    MyAccountView,
    PayeeListView,
    PaymentListCreateView,
    PersonAccountView,
    SalaryView,
)

urlpatterns = [
    path("payments/", PaymentListCreateView.as_view()),
    path("payments/me/", MyAccountView.as_view()),
    path("payments/people/", PayeeListView.as_view()),
    path("payments/people/<uuid:person_id>/", PersonAccountView.as_view()),
    path("payments/people/<uuid:person_id>/salary/", SalaryView.as_view()),
]
