from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import CapabilityGate
from apps.accounts.domain.capabilities import (
    ALLOT_VANS,
    APPROVE_FUEL_BILLS,
    MANAGE_STAFF,
    SUBMIT_FUEL_BILL,
)
from apps.core.api.query import QueryParams
from config.container import container

from ..domain.fuel import BillStatus, FuelType
from .serializers import (
    FuelBillInput,
    FuelBillOut,
    RejectInput,
    StaffInput,
    StaffOut,
    StaffPatchInput,
    VanInput,
    VanOut,
    VanPatchInput,
)


# ------------------------------------------------------------------ staff
class _StaffRights(APIView):
    permission_classes = [CapabilityGate.of(read=(MANAGE_STAFF, ALLOT_VANS), write=(MANAGE_STAFF,))]


class StaffListCreateView(_StaffRights):
    def get(self, request):
        query = QueryParams(request)
        staff = container.list_staff().call(
            container.actor(request.user), query=query.text("query"), active=query.active()
        )
        return Response(StaffOut(staff, many=True).data)

    def post(self, request):
        data = StaffInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.add_staff().call(container.actor(request.user), **data.validated_data)
        return Response(StaffOut(saved).data, status=201)


class StaffDetailView(_StaffRights):
    def get(self, request, staff_id):
        staff = container.get_staff().call(container.actor(request.user), staff_id)
        return Response(StaffOut(staff).data)

    def patch(self, request, staff_id):
        data = StaffPatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.update_staff().call(
            container.actor(request.user), staff_id, **data.validated_data
        )
        return Response(StaffOut(saved).data)

    def delete(self, request, staff_id):
        container.remove_staff().call(container.actor(request.user), staff_id)
        return Response(status=204)


# ------------------------------------------------------------------- vans
class _VanRights(APIView):
    permission_classes = [CapabilityGate.of(
        read=(ALLOT_VANS, MANAGE_STAFF, APPROVE_FUEL_BILLS, SUBMIT_FUEL_BILL),
        write=(ALLOT_VANS,),
    )]


class VanListCreateView(_VanRights):
    def get(self, request):
        vans = container.list_vans().call(container.actor(request.user))
        return Response(VanOut(vans, many=True).data)

    def post(self, request):
        data = VanInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.add_van().call(container.actor(request.user), **data.validated_data)
        return Response(VanOut(saved).data, status=201)


class VanDetailView(_VanRights):
    def patch(self, request, van_id):
        data = VanPatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.update_van().call(
            container.actor(request.user), van_id, **data.validated_data
        )
        return Response(VanOut(saved).data)

    def delete(self, request, van_id):
        container.remove_van().call(container.actor(request.user), van_id)
        return Response(status=204)


# ------------------------------------------------------------- fuel bills
class _BillRights(APIView):
    permission_classes = [CapabilityGate.of(
        read=(APPROVE_FUEL_BILLS, SUBMIT_FUEL_BILL), write=(SUBMIT_FUEL_BILL,)
    )]


class FuelBillListCreateView(_BillRights):
    def get(self, request):
        query = QueryParams(request)
        reports = container.list_fuel_bills().call(
            container.actor(request.user), van_id=query.uuid("van_id"),
            status=query.choice("status", BillStatus), from_date=query.date("from"),
            to_date=query.date("to"),
        )
        return Response(FuelBillOut(reports, many=True).data)

    def post(self, request):
        data = FuelBillInput(data=request.data)
        data.is_valid(raise_exception=True)
        fields = dict(data.validated_data, fuel=FuelType(data.validated_data["fuel"]))
        report = container.submit_fuel_bill().call(container.actor(request.user), **fields)
        return Response(FuelBillOut(report).data, status=201)


class FuelBillDetailView(_BillRights):
    def delete(self, request, bill_id):
        container.withdraw_fuel_bill().call(container.actor(request.user), bill_id)
        return Response(status=204)


class _DecisionRights(APIView):
    permission_classes = [CapabilityGate.of(read=(APPROVE_FUEL_BILLS,), write=(APPROVE_FUEL_BILLS,))]


class FuelBillApproveView(_DecisionRights):
    def post(self, request, bill_id):
        report = container.approve_fuel_bill().call(container.actor(request.user), bill_id)
        return Response(FuelBillOut(report).data)


class FuelBillRejectView(_DecisionRights):
    def post(self, request, bill_id):
        data = RejectInput(data=request.data)
        data.is_valid(raise_exception=True)
        report = container.reject_fuel_bill().call(
            container.actor(request.user), bill_id, reason=data.validated_data["reason"]
        )
        return Response(FuelBillOut(report).data)
