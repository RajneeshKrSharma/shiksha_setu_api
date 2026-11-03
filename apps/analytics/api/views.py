from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import CapabilityGate
from apps.accounts.domain.capabilities import VIEW_ANALYTICS
from apps.accounts.domain.entities import Role
from apps.core.api.query import QueryParams
from apps.exams.domain.entities import ExamType
from config.container import container

from .serializers import (
    ExamAveragesOut,
    FeeReportOut,
    FuelOut,
    LessonCoverageOut,
    PaymentsOut,
    StaffAttendanceOut,
    StudentAttendanceOut,
)


class _GraphView(APIView):
    """Every graph is read-only and needs the right to see analytics."""

    permission_classes = [CapabilityGate.of(read=(VIEW_ANALYTICS,), write=())]

    @staticmethod
    def actor(request):
        return container.actor(request.user)


class StudentAttendanceView(_GraphView):
    def get(self, request):
        query = QueryParams(request)
        report = container.get_student_attendance().call(
            self.actor(request), from_date=query.date("from"), to_date=query.date("to"),
            class_id=query.uuid("class_id"),
        )
        return Response(StudentAttendanceOut(report).data)


class FeeReportView(_GraphView):
    def get(self, request):
        query = QueryParams(request)
        report = container.get_fee_report().call(
            self.actor(request), from_date=query.date("from"), to_date=query.date("to")
        )
        return Response(FeeReportOut(report).data)


class ExamAveragesView(_GraphView):
    def get(self, request):
        query = QueryParams(request)
        report = container.get_exam_averages().call(
            self.actor(request), from_date=query.date("from"), to_date=query.date("to"),
            class_id=query.uuid("class_id"), exam_type=query.choice("type", ExamType),
        )
        return Response(ExamAveragesOut(report).data)


class StaffAttendanceView(_GraphView):
    def get(self, request):
        query = QueryParams(request)
        report = container.get_staff_attendance().call(
            self.actor(request), from_date=query.date("from"), to_date=query.date("to"),
            role=query.choice("role", Role),
        )
        return Response(StaffAttendanceOut(report).data)


class PaymentsView(_GraphView):
    def get(self, request):
        query = QueryParams(request)
        report = container.get_payments_report().call(
            self.actor(request), from_date=query.date("from"), to_date=query.date("to")
        )
        return Response(PaymentsOut(report).data)


class FuelView(_GraphView):
    def get(self, request):
        query = QueryParams(request)
        report = container.get_fuel_report().call(
            self.actor(request), from_date=query.date("from"), to_date=query.date("to"),
            van_id=query.uuid("van_id"),
        )
        return Response(FuelOut(report).data)


class LessonCoverageView(_GraphView):
    def get(self, request):
        query = QueryParams(request)
        report = container.get_lesson_coverage().call(
            self.actor(request), from_date=query.date("from"), to_date=query.date("to")
        )
        return Response(LessonCoverageOut(report).data)
