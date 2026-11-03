"""Shapes for the graphs: a `period`, then the points to draw. Amounts and percentages are
strings with two decimals; days and months are ISO dates (a month is its first day)."""
from rest_framework import serializers

from ..domain.reports import (
    ExamAverages,
    FeeReport,
    FuelReport,
    LessonCoverage,
    PaymentsReport,
    StaffAttendanceTrend,
    StudentAttendanceTrend,
)


def _two(value) -> str | None:
    return None if value is None else f"{value:.2f}"


def _period(period) -> dict:
    return {"from": period.start.isoformat(), "to": period.end.isoformat()}


class StudentAttendanceOut(serializers.Serializer):
    def to_representation(self, report: StudentAttendanceTrend):
        return {
            "period": _period(report.period),
            "class_id": str(report.class_id) if report.class_id else None,
            "class_name": report.class_name,
            "points": [
                {"day": p.day.isoformat(), "marked": p.marked, "present": p.present,
                 "late": p.late, "absent": p.absent, "percent": _two(p.percent)}
                for p in report.points
            ],
        }


class FeeReportOut(serializers.Serializer):
    def to_representation(self, report: FeeReport):
        return {
            "period": _period(report.period),
            "collected": [
                {"month": m.month.isoformat(),
                 "by_head": {head: _two(amount) for head, amount in m.by_head.items()},
                 "total": _two(m.total)}
                for m in report.collected
            ],
            "collected_total": _two(report.collected_total),
            "by_class": [
                {"class_id": str(c.class_id), "class_name": c.class_name,
                 "students": c.students, "due": _two(c.due), "paid": _two(c.paid),
                 "balance": _two(c.balance)}
                for c in report.by_class
            ],
            "balance_total": _two(report.balance_total),
        }


class ExamAveragesOut(serializers.Serializer):
    def to_representation(self, report: ExamAverages):
        return {
            "period": _period(report.period),
            "points": [
                {"exam_id": str(p.exam_id), "held_on": p.held_on.isoformat(),
                 "exam_type": p.exam_type, "class_name": p.class_name, "subject": p.subject,
                 "max_marks": p.max_marks, "entered": p.entered, "absent": p.absent,
                 "average_marks": _two(p.average_marks),
                 "average_percent": _two(p.average_percent)}
                for p in report.points
            ],
        }


class StaffAttendanceOut(serializers.Serializer):
    def to_representation(self, report: StaffAttendanceTrend):
        return {
            "period": _period(report.period),
            "role": report.role,
            "points": [
                {"day": p.day.isoformat(), "is_holiday": p.is_holiday, "people": p.people,
                 "present": p.present, "late": p.late, "absent": p.absent, "leave": p.leave,
                 "not_in_yet": p.not_in_yet}
                for p in report.points
            ],
        }


class PaymentsOut(serializers.Serializer):
    def to_representation(self, report: PaymentsReport):
        return {
            "period": _period(report.period),
            "paid": [
                {"month": m.month.isoformat(), "salary": _two(m.salary), "fuel": _two(m.fuel),
                 "total": _two(m.total)}
                for m in report.paid
            ],
            "paid_total": _two(report.paid_total),
            "owed_salary": _two(report.owed_salary),
            "owed_fuel": _two(report.owed_fuel),
            "owed_total": _two(report.owed_salary + report.owed_fuel),
        }


class FuelOut(serializers.Serializer):
    def to_representation(self, report: FuelReport):
        return {
            "period": _period(report.period),
            "points": [
                {"month": p.month.isoformat(), "van_id": str(p.van_id), "van_name": p.van_name,
                 "bills": p.bills, "litres": _two(p.litres), "amount": _two(p.amount),
                 "distance_km": p.distance_km, "km_per_litre": _two(p.km_per_litre)}
                for p in report.points
            ],
        }


class LessonCoverageOut(serializers.Serializer):
    def to_representation(self, report: LessonCoverage):
        return {
            "period": _period(report.period),
            "points": [
                {"day": p.day.isoformat(), "is_holiday": p.is_holiday, "expected": p.expected,
                 "recorded": p.recorded, "percent": _two(p.percent)}
                for p in report.points
            ],
        }
