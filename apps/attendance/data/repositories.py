from datetime import date
from uuid import UUID

from django.db.models import Count

from ..domain.entities import StudentMark, StudentStatus, WorkAttendance, WorkStatus
from ..domain.repositories import StudentMarkRepository, WorkAttendanceRepository
from . import models as rows


class DjangoStudentMarkRepository(StudentMarkRepository):
    def save_many(self, marks: list[StudentMark]) -> None:
        for mark in marks:
            rows.StudentAttendance.objects.update_or_create(
                student_id=mark.student_id, day=mark.day,
                defaults={
                    "school_class_id": mark.class_id,
                    "status": mark.status.value,
                    "marked_by_id": mark.marked_by_id,
                },
            )

    def for_class_day(self, class_id: UUID, day: date) -> dict[UUID, StudentMark]:
        found = rows.StudentAttendance.objects.filter(school_class_id=class_id, day=day)
        return {row.student_id: self._entity(row) for row in found}

    def daily_counts(self, from_date: date, to_date: date, class_id: UUID | None = None
                     ) -> dict[date, dict[StudentStatus, int]]:
        found = rows.StudentAttendance.objects.filter(day__gte=from_date, day__lte=to_date)
        if class_id is not None:
            found = found.filter(school_class_id=class_id)
        counts: dict[date, dict[StudentStatus, int]] = {}
        for item in found.values("day", "status").annotate(total=Count("id")):
            counts.setdefault(item["day"], {})[StudentStatus(item["status"])] = item["total"]
        return counts

    def tally(self, class_id: UUID, from_date: date, to_date: date
              ) -> dict[UUID, dict[StudentStatus, int]]:
        found = (
            rows.StudentAttendance.objects
            .filter(school_class_id=class_id, day__gte=from_date, day__lte=to_date)
            .values("student_id", "status").annotate(days=Count("id"))
        )
        counts: dict[UUID, dict[StudentStatus, int]] = {}
        for item in found:
            counts.setdefault(item["student_id"], {})[StudentStatus(item["status"])] = item["days"]
        return counts

    @staticmethod
    def _entity(row: rows.StudentAttendance) -> StudentMark:
        return StudentMark(
            id=row.pk, student_id=row.student_id, class_id=row.school_class_id, day=row.day,
            status=StudentStatus(row.status), marked_by_id=row.marked_by_id,
        )


class DjangoWorkAttendanceRepository(WorkAttendanceRepository):
    def get(self, entity_id: UUID) -> WorkAttendance | None:
        row = self._rows().filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def add(self, record: WorkAttendance) -> WorkAttendance:
        row = rows.WorkAttendance.objects.create(
            person_id=record.person_id, day=record.day, checked_in_at=record.checked_in_at,
            checked_out_at=record.checked_out_at, status=record.status.value,
            corrected_by_id=record.corrected_by_id,
        )
        return self.get(row.pk)

    def update(self, record: WorkAttendance) -> WorkAttendance:
        row = rows.WorkAttendance.objects.get(pk=record.id)
        row.checked_in_at, row.checked_out_at = record.checked_in_at, record.checked_out_at
        row.status, row.corrected_by_id = record.status.value, record.corrected_by_id
        row.save(update_fields=[
            "checked_in_at", "checked_out_at", "status", "corrected_by", "updated_at",
        ])
        return self.get(row.pk)

    def find(self, person_id: UUID, day: date) -> WorkAttendance | None:
        row = self._rows().filter(person_id=person_id, day=day).first()
        return self._entity(row) if row else None

    def on_day(self, day: date) -> dict[UUID, WorkAttendance]:
        return {row.person_id: self._entity(row) for row in self._rows().filter(day=day)}

    def list(self, *, person_id: UUID | None = None, from_date: date | None = None,
             to_date: date | None = None) -> list[WorkAttendance]:
        found = self._rows()
        if person_id is not None:
            found = found.filter(person_id=person_id)
        if from_date is not None:
            found = found.filter(day__gte=from_date)
        if to_date is not None:
            found = found.filter(day__lte=to_date)
        return [self._entity(row) for row in found.order_by("-day", "person__name")]

    @staticmethod
    def _rows():
        return rows.WorkAttendance.objects.select_related("person")

    @staticmethod
    def _entity(row: rows.WorkAttendance) -> WorkAttendance:
        return WorkAttendance(
            id=row.pk, person_id=row.person_id, day=row.day, checked_in_at=row.checked_in_at,
            checked_out_at=row.checked_out_at, status=WorkStatus(row.status),
            corrected_by_id=row.corrected_by_id, person_name=row.person.name, role=row.person.role,
        )
