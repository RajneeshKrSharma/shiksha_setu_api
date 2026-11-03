from __future__ import annotations

from datetime import date
from uuid import UUID

from apps.accounts.domain.entities import Role, UserAccount
from apps.accounts.domain.repositories import UserRepository
from apps.students.domain.entities import ClassLevel, SchoolClass

from ..domain.entities import Allotment, Lesson, Teacher
from ..domain.repositories import AllotmentRepository, LessonRepository, TeacherRepository
from . import models as rows


def _class_name(row) -> str:
    return SchoolClass(level=ClassLevel(row.level), section=row.section).name


class DjangoTeacherRepository(TeacherRepository):
    """A teacher is a sign-in account with the teacher role, so this works through
    the accounts module's repository."""

    def __init__(self, users: UserRepository):
        self._users = users

    def get(self, entity_id: UUID) -> Teacher | None:
        account = self._users.get(entity_id)
        if account is None or account.role != Role.TEACHER:
            return None
        return Teacher.from_account(account)

    def add(self, teacher: Teacher, password: str | None = None) -> Teacher:
        account = UserAccount.register(name=teacher.name, email=teacher.email, role=Role.TEACHER)
        return Teacher.from_account(self._users.add(account, password))

    def update(self, teacher: Teacher) -> Teacher:
        account = self._users.get(teacher.id)
        account.name, account.is_active = teacher.name, teacher.is_active
        return Teacher.from_account(self._users.update(account))

    def list(self, *, query: str = "", active: bool | None = None) -> list[Teacher]:
        accounts = self._users.list(role=Role.TEACHER, query=query, active=active)
        return [Teacher.from_account(account) for account in accounts]


class DjangoAllotmentRepository(AllotmentRepository):
    def get(self, entity_id: UUID) -> Allotment | None:
        row = self._rows().filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def add(self, allotment: Allotment) -> Allotment:
        row = rows.Allotment.objects.create(
            teacher_id=allotment.teacher_id, school_class_id=allotment.class_id,
            subject=allotment.subject,
        )
        return self.get(row.pk)

    def update(self, allotment: Allotment) -> Allotment:
        row = rows.Allotment.objects.get(pk=allotment.id)
        row.is_active = allotment.is_active
        row.save(update_fields=["is_active", "updated_at"])
        return self.get(row.pk)

    def list(self, *, teacher_id: UUID | None = None, class_id: UUID | None = None,
             active: bool = True, teacher_active: bool | None = None) -> list[Allotment]:
        found = self._rows().filter(is_active=active)
        if teacher_id is not None:
            found = found.filter(teacher_id=teacher_id)
        if class_id is not None:
            found = found.filter(school_class_id=class_id)
        if teacher_active is not None:
            found = found.filter(teacher__is_active=teacher_active)
        ordered = sorted(found, key=lambda r: (
            ClassLevel(r.school_class.level).order, r.school_class.section, r.subject.lower(),
        ))
        return [self._entity(row) for row in ordered]

    def find_active(self, class_id: UUID, subject: str) -> Allotment | None:
        row = self._rows().filter(
            school_class_id=class_id, subject__iexact=subject, is_active=True
        ).first()
        return self._entity(row) if row else None

    @staticmethod
    def _rows():
        return rows.Allotment.objects.select_related("teacher", "school_class")

    @staticmethod
    def _entity(row: rows.Allotment) -> Allotment:
        return Allotment(
            id=row.pk, teacher_id=row.teacher_id, class_id=row.school_class_id,
            subject=row.subject, is_active=row.is_active, teacher_name=row.teacher.name,
            class_name=_class_name(row.school_class),
        )


class DjangoLessonRepository(LessonRepository):
    def get(self, entity_id: UUID) -> Lesson | None:
        row = self._rows().filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def add(self, lesson: Lesson) -> Lesson:
        row = rows.Lesson.objects.create(
            allotment_id=lesson.allotment_id, subject=lesson.subject,
            taught_on=lesson.taught_on, topic=lesson.topic,
        )
        return self.get(row.pk)

    def update(self, lesson: Lesson) -> Lesson:
        row = rows.Lesson.objects.get(pk=lesson.id)
        row.topic = lesson.topic
        row.save(update_fields=["topic", "updated_at"])
        return self.get(row.pk)

    def find(self, allotment_id: UUID, taught_on: date) -> Lesson | None:
        row = self._rows().filter(allotment_id=allotment_id, taught_on=taught_on).first()
        return self._entity(row) if row else None

    def list(self, *, teacher_id: UUID | None = None, class_id: UUID | None = None,
             from_date: date | None = None, to_date: date | None = None) -> list[Lesson]:
        found = self._rows()
        if teacher_id is not None:
            found = found.filter(allotment__teacher_id=teacher_id)
        if class_id is not None:
            found = found.filter(allotment__school_class_id=class_id)
        if from_date is not None:
            found = found.filter(taught_on__gte=from_date)
        if to_date is not None:
            found = found.filter(taught_on__lte=to_date)
        return [self._entity(row) for row in found]

    def on_day(self, day: date) -> dict[UUID, Lesson]:
        return {row.allotment_id: self._entity(row) for row in self._rows().filter(taught_on=day)}

    @staticmethod
    def _rows():
        return rows.Lesson.objects.select_related("allotment__teacher", "allotment__school_class")

    @staticmethod
    def _entity(row: rows.Lesson) -> Lesson:
        allotment = row.allotment
        return Lesson(
            id=row.pk, allotment_id=row.allotment_id, teacher_id=allotment.teacher_id,
            class_id=allotment.school_class_id, subject=row.subject, taught_on=row.taught_on,
            topic=row.topic, recorded_at=row.created_at, teacher_name=allotment.teacher.name,
            class_name=_class_name(allotment.school_class),
        )
