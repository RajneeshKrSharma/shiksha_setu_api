from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import CapabilityGate
from apps.accounts.domain.capabilities import (
    MANAGE_ACCESSORIES,
    MANAGE_CLASSES,
    MANAGE_FEES,
    MANAGE_STUDENTS,
    VIEW_STUDENTS,
)
from apps.core.api.query import QueryParams
from apps.core.domain.errors import NotFound
from config.container import container

from ..domain.accessories import AccessoryKind
from ..domain.entities import ClassLevel
from ..domain.fees import FeeHead
from .serializers import (
    ClassInput,
    ClassOut,
    ClassPatchInput,
    FeeAmountInput,
    IssueInput,
    IssueOut,
    ItemInput,
    ItemOut,
    ItemPatchInput,
    PaymentInput,
    PaymentOut,
    StatementOut,
    StructureOut,
    StudentFeesOut,
    StudentInput,
    StudentOut,
    StudentPatchInput,
)


def _actor(request):
    return container.actor(request.user)


# ---------------------------------------------------------------- classes
class _ClassRights(APIView):
    permission_classes = [CapabilityGate.of(
        read=(VIEW_STUDENTS, MANAGE_STUDENTS, MANAGE_CLASSES), write=(MANAGE_CLASSES,)
    )]


class ClassListCreateView(_ClassRights):
    def get(self, request):
        classes = container.list_classes().call(_actor(request), active=QueryParams(request).active())
        return Response(ClassOut(classes, many=True).data)

    def post(self, request):
        data = ClassInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.add_class().call(
            _actor(request), level=ClassLevel(data.validated_data["level"]),
            section=data.validated_data["section"] or "",
        )
        return Response(ClassOut(saved).data, status=201)


class ClassDetailView(_ClassRights):
    def get(self, request, class_id):
        return Response(ClassOut(container.get_class().call(_actor(request), class_id)).data)

    def patch(self, request, class_id):
        data = ClassPatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        level = data.validated_data.get("level")
        saved = container.update_class().call(
            _actor(request), class_id,
            level=ClassLevel(level) if level else None,
            # Leaving the section out keeps it; sending "" or null clears it.
            section=(data.validated_data["section"] or "") if "section" in data.validated_data else None,
        )
        return Response(ClassOut(saved).data)

    def delete(self, request, class_id):
        container.remove_class().call(_actor(request), class_id)
        return Response(status=204)


# --------------------------------------------------------------- students
class _StudentRights(APIView):
    permission_classes = [CapabilityGate.of(
        read=(VIEW_STUDENTS, MANAGE_STUDENTS), write=(MANAGE_STUDENTS,)
    )]


class StudentListCreateView(_StudentRights):
    def get(self, request):
        query = QueryParams(request)
        students = container.list_students().call(
            _actor(request), query=query.text("query"), active=query.active(),
            class_id=query.uuid("class_id"),
        )
        return Response(StudentOut(students, many=True).data)

    def post(self, request):
        data = StudentInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.add_student().call(_actor(request), **data.validated_data)
        return Response(StudentOut(saved).data, status=201)


class StudentDetailView(_StudentRights):
    def get(self, request, student_id):
        return Response(StudentOut(container.get_student().call(_actor(request), student_id)).data)

    def patch(self, request, student_id):
        data = StudentPatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.update_student().call(
            _actor(request), student_id, **data.validated_data
        )
        return Response(StudentOut(saved).data)

    def delete(self, request, student_id):
        container.remove_student().call(_actor(request), student_id)
        return Response(status=204)


class StudentFeesView(APIView):
    permission_classes = [CapabilityGate.of(read=(MANAGE_FEES,), write=(MANAGE_FEES,))]

    def get(self, request, student_id):
        return Response(
            StudentFeesOut(container.get_student_fees().call(_actor(request), student_id)).data
        )


# ------------------------------------------------------------ dress, books
class _AccessoryRights(APIView):
    permission_classes = [CapabilityGate.of(read=(MANAGE_ACCESSORIES,), write=(MANAGE_ACCESSORIES,))]


class ItemListCreateView(_AccessoryRights):
    def get(self, request):
        query = QueryParams(request)
        items = container.list_accessory_items().call(
            _actor(request), kind=query.choice("kind", AccessoryKind),
            class_id=query.uuid("class_id"),
        )
        return Response(ItemOut(items, many=True).data)

    def post(self, request):
        data = ItemInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.add_accessory_item().call(
            _actor(request), kind=AccessoryKind(data.validated_data["kind"]),
            name=data.validated_data["name"], price=data.validated_data["price"],
            class_id=data.validated_data["class_id"],
        )
        return Response(ItemOut(saved).data, status=201)


class ItemDetailView(_AccessoryRights):
    def patch(self, request, item_id):
        data = ItemPatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.update_accessory_item().call(
            _actor(request), item_id, **data.validated_data
        )
        return Response(ItemOut(saved).data)

    def delete(self, request, item_id):
        container.remove_accessory_item().call(_actor(request), item_id)
        return Response(status=204)


class IssueListCreateView(_AccessoryRights):
    def get(self, request):
        query = QueryParams(request)
        issues = container.list_accessory_issues().call(
            _actor(request), student_id=query.uuid("student_id"),
            kind=query.choice("kind", AccessoryKind),
        )
        return Response(IssueOut(issues, many=True).data)

    def post(self, request):
        data = IssueInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.issue_accessory().call(
            _actor(request), student_id=data.validated_data["student_id"],
            item_id=data.validated_data["item_id"], quantity=data.validated_data["quantity"],
            issued_on=data.validated_data.get("issued_on"),
        )
        return Response(IssueOut(saved).data, status=201)


# ------------------------------------------------------------------- fees
class _FeeRights(APIView):
    permission_classes = [CapabilityGate.of(read=(MANAGE_FEES,), write=(MANAGE_FEES,))]

    @staticmethod
    def head(value: str) -> FeeHead:
        try:
            return FeeHead(value)
        except ValueError:
            raise NotFound("There is no such fee.")


class FeeStructureView(_FeeRights):
    def get(self, request):
        class_id = QueryParams(request).uuid("class_id")
        if class_id is None:
            raise NotFound("Give the class_id to see its fees.")
        lines = container.get_fee_structure().call(_actor(request), class_id)
        return Response(StructureOut(lines, many=True).data)


class FeeAmountView(_FeeRights):
    def put(self, request, class_id, head):
        data = FeeAmountInput(data=request.data)
        data.is_valid(raise_exception=True)
        amount = container.set_fee_amount().call(
            _actor(request), class_id, self.head(head), data.validated_data["amount"]
        )
        return Response({"head": head, "amount": f"{amount:.2f}"})


class FeeAccountListView(_FeeRights):
    def get(self, request):
        query = QueryParams(request)
        statements = container.list_fee_accounts().call(
            _actor(request), class_id=query.uuid("class_id"), query=query.text("query"),
            only_due=query.flag("only_due", default=False),
        )
        return Response(StatementOut(statements, many=True).data)


class FeePaymentListCreateView(_FeeRights):
    def get(self, request):
        query = QueryParams(request)
        payments = container.list_fee_payments().call(
            _actor(request), student_id=query.uuid("student_id"),
            from_date=query.date("from"), to_date=query.date("to"),
        )
        return Response(PaymentOut(payments, many=True).data)

    def post(self, request):
        data = PaymentInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.receive_fee_payment().call(
            _actor(request), student_id=data.validated_data["student_id"],
            head=FeeHead(data.validated_data["head"]), amount=data.validated_data["amount"],
            paid_on=data.validated_data.get("paid_on"), note=data.validated_data["note"],
        )
        return Response(PaymentOut(saved).data, status=201)
