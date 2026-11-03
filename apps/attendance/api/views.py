from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import CapabilityGate
from apps.accounts.domain.capabilities import (
    CORRECT_ATTENDANCE,
    MARK_STUDENT_ATTENDANCE,
    RECORD_OWN_ATTENDANCE,
    VIEW_ATTENDANCE,
)
from apps.accounts.domain.entities import Role
from apps.core.api.query import QueryParams
from apps.core.domain.errors import RuleViolation
from config.container import container

from ..domain.entities import StudentStatus
from .serializers import (
    ClassAttendanceInput,
    CorrectionInput,
    DayBoardOut,
    RosterLineOut,
    TallyOut,
    WorkRecordOut,
)


# --------------------------------------------------------------- students
class _StudentRights(APIView):
    permission_classes = [CapabilityGate.of(
        read=(VIEW_ATTENDANCE, MARK_STUDENT_ATTENDANCE), write=(MARK_STUDENT_ATTENDANCE,)
    )]


class ClassAttendanceView(_StudentRights):
    def get(self, request):
        query = QueryParams(request)
        class_id = query.uuid("class_id")
        if class_id is None:
            raise RuleViolation("Give the class_id.", errors={"class_id": ["Required."]})
        roster = container.get_class_attendance().call(
            container.actor(request.user), class_id=class_id, day=query.date("day")
        )
        return Response(RosterLineOut(roster, many=True).data)

    def put(self, request):
        data = ClassAttendanceInput(data=request.data)
        data.is_valid(raise_exception=True)
        marks = [(m["student_id"], StudentStatus(m["status"])) for m in data.validated_data["marks"]]
        roster = container.mark_student_attendance().call(
            container.actor(request.user), class_id=data.validated_data["class_id"],
            marks=marks, day=data.validated_data.get("day"),
        )
        return Response(RosterLineOut(roster, many=True).data)


class ClassReportView(_StudentRights):
    def get(self, request):
        query = QueryParams(request)
        class_id, from_date, to_date = query.uuid("class_id"), query.date("from"), query.date("to")
        if class_id is None or from_date is None or to_date is None:
            raise RuleViolation("Give class_id, from and to.",
                                errors={"class_id": ["Required."], "from": ["Required."], "to": ["Required."]})
        tallies = container.student_attendance_report().call(
            container.actor(request.user), class_id=class_id, from_date=from_date, to_date=to_date
        )
        return Response(TallyOut(tallies, many=True).data)


# ------------------------------------------------- teachers and staff: self
class _OwnRights(APIView):
    permission_classes = [CapabilityGate.of(
        read=(RECORD_OWN_ATTENDANCE,), write=(RECORD_OWN_ATTENDANCE,)
    )]


class CheckInView(_OwnRights):
    def post(self, request):
        record = container.check_in().call(container.actor(request.user))
        return Response(WorkRecordOut(record).data, status=201)


class CheckOutView(_OwnRights):
    def post(self, request):
        record = container.check_out().call(container.actor(request.user))
        return Response(WorkRecordOut(record).data)


class MyAttendanceView(_OwnRights):
    def get(self, request):
        query = QueryParams(request)
        records = container.list_my_attendance().call(
            container.actor(request.user), from_date=query.date("from"), to_date=query.date("to")
        )
        return Response(WorkRecordOut(records, many=True).data)


# ------------------------------------------------ teachers and staff: Principal
class _BoardRights(APIView):
    permission_classes = [CapabilityGate.of(
        read=(VIEW_ATTENDANCE,), write=(CORRECT_ATTENDANCE,)
    )]


class DayBoardView(_BoardRights):
    def get(self, request):
        query = QueryParams(request)
        board = container.get_day_board().call(
            container.actor(request.user), day=query.date("day"), role=query.choice("role", Role)
        )
        return Response(DayBoardOut(board).data)


class WorkRecordsView(_BoardRights):
    def get(self, request):
        query = QueryParams(request)
        records = container.list_work_records().call(
            container.actor(request.user), person_id=query.uuid("person_id"),
            from_date=query.date("from"), to_date=query.date("to"),
        )
        return Response(WorkRecordOut(records, many=True).data)

    def put(self, request):
        data = CorrectionInput(data=request.data)
        data.is_valid(raise_exception=True)
        record = container.correct_work_attendance().call(
            container.actor(request.user), **data.validated_data
        )
        return Response(WorkRecordOut(record).data)
