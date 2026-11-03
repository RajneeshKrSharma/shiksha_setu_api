from django.urls import path

from .views import (
    FuelBillApproveView,
    FuelBillDetailView,
    FuelBillListCreateView,
    FuelBillRejectView,
    StaffDetailView,
    StaffListCreateView,
    VanDetailView,
    VanListCreateView,
)

urlpatterns = [
    path("staff/", StaffListCreateView.as_view()),
    path("staff/<uuid:staff_id>/", StaffDetailView.as_view()),
    path("vans/", VanListCreateView.as_view()),
    path("vans/<uuid:van_id>/", VanDetailView.as_view()),
    path("fuel-bills/", FuelBillListCreateView.as_view()),
    path("fuel-bills/<uuid:bill_id>/", FuelBillDetailView.as_view()),
    path("fuel-bills/<uuid:bill_id>/approve/", FuelBillApproveView.as_view()),
    path("fuel-bills/<uuid:bill_id>/reject/", FuelBillRejectView.as_view()),
]
