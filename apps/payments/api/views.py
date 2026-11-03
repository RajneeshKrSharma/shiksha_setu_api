from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import CapabilityGate
from apps.accounts.domain.capabilities import (
    MANAGE_STAFF_PAYMENTS,
    MANAGE_TEACHER_PAYMENTS,
    VIEW_OWN_PAYMENTS,
)
from apps.accounts.domain.entities import Role
from apps.core.api.query import QueryParams
from config.container import container

from ..domain.entities import PayMonth, PaymentKind, PaymentMode
from .serializers import (
    AccountOut,
    PayeeOut,
    PaymentInput,
    PaymentOut,
    SalaryInput,
    SalaryRateOut,
)

_MANAGERS = (MANAGE_TEACHER_PAYMENTS, MANAGE_STAFF_PAYMENTS)
_VIEWERS = (*_MANAGERS, VIEW_OWN_PAYMENTS)


def _actor(request):
    return container.actor(request.user)


class PayeeListView(APIView):
    """The teachers and staff the Principal may pay, with what each is owed."""

    permission_classes = [CapabilityGate.of(read=_MANAGERS, write=())]

    def get(self, request):
        query = QueryParams(request)
        payees = container.list_payees().call(
            _actor(request), role=query.choice("role", Role), query=query.text("query"),
            active=query.active(),
        )
        return Response(PayeeOut(payees, many=True).data)


class PersonAccountView(APIView):
    permission_classes = [CapabilityGate.of(read=_VIEWERS, write=())]

    def get(self, request, person_id):
        return Response(AccountOut(container.get_person_account().call(_actor(request), person_id)).data)


class SalaryView(APIView):
    permission_classes = [CapabilityGate.of(read=_VIEWERS, write=_MANAGERS)]

    def get(self, request, person_id):
        history = container.get_salary_history().call(_actor(request), person_id)
        return Response(SalaryRateOut(history, many=True).data)

    def put(self, request, person_id):
        data = SalaryInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.set_salary().call(
            _actor(request), person_id, amount=data.validated_data["amount"],
            effective_from=PayMonth.parse(data.validated_data["effective_from"]),
        )
        return Response(SalaryRateOut(saved).data)


class PaymentListCreateView(APIView):
    permission_classes = [CapabilityGate.of(read=_VIEWERS, write=_MANAGERS)]

    def get(self, request):
        query = QueryParams(request)
        payments = container.list_payments().call(
            _actor(request), person_id=query.uuid("person_id"), from_date=query.date("from"),
            to_date=query.date("to"),
        )
        return Response(PaymentOut(payments, many=True).data)

    def post(self, request):
        data = PaymentInput(data=request.data)
        data.is_valid(raise_exception=True)
        fields = dict(data.validated_data)
        month = fields.pop("month")
        saved = container.record_payment().call(
            _actor(request), fields.pop("person_id"), kind=PaymentKind(fields.pop("kind")),
            mode=PaymentMode(fields.pop("mode")),
            month=PayMonth.parse(month) if month else None, **fields,
        )
        return Response(PaymentOut(saved).data, status=201)


class MyAccountView(APIView):
    """A teacher's or staff member's own salary, dues and payments."""

    permission_classes = [CapabilityGate.of(read=(VIEW_OWN_PAYMENTS,), write=())]

    def get(self, request):
        return Response(AccountOut(container.get_my_account().call(_actor(request))).data)
