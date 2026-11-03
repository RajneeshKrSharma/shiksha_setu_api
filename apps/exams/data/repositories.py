from __future__ import annotations

from datetime import date
from uuid import UUID

from django.db import transaction

from apps.students.domain.entities import ClassLevel, SchoolClass

from ..domain.entities import (
    Exam,
    ExamMark,
    ExamType,
    Paper,
    PaperItem,
    PaperStatus,
    Question,
    QuestionType,
    QuestionUnit,
)
from ..domain.repositories import (
    ExamRepository,
    MarkRepository,
    PaperRepository,
    QuestionRepository,
    UnitRepository,
)
from . import models as rows


def _class_name(row) -> str:
    return SchoolClass(level=ClassLevel(row.level), section=row.section).name


class DjangoExamRepository(ExamRepository):
    def get(self, entity_id: UUID) -> Exam | None:
        row = self._rows().filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def add(self, exam: Exam) -> Exam:
        row = rows.Exam.objects.create(
            exam_type=exam.exam_type.value, school_class_id=exam.class_id, subject=exam.subject,
            held_on=exam.held_on, max_marks=exam.max_marks,
        )
        return self.get(row.pk)

    def update(self, exam: Exam) -> Exam:
        row = rows.Exam.objects.get(pk=exam.id)
        row.exam_type, row.held_on = exam.exam_type.value, exam.held_on
        row.max_marks, row.is_active = exam.max_marks, exam.is_active
        row.save(update_fields=["exam_type", "held_on", "max_marks", "is_active", "updated_at"])
        return self.get(row.pk)

    def list(self, *, class_ids: frozenset[UUID] | None = None, class_id: UUID | None = None,
             exam_type: ExamType | None = None, from_date: date | None = None,
             to_date: date | None = None) -> list[Exam]:
        found = self._rows().filter(is_active=True)
        if class_ids is not None:
            found = found.filter(school_class_id__in=class_ids)
        if class_id is not None:
            found = found.filter(school_class_id=class_id)
        if exam_type is not None:
            found = found.filter(exam_type=exam_type.value)
        if from_date is not None:
            found = found.filter(held_on__gte=from_date)
        if to_date is not None:
            found = found.filter(held_on__lte=to_date)
        return [self._entity(row) for row in found]

    def find_same(self, class_id: UUID, subject: str, exam_type: ExamType,
                  held_on: date) -> Exam | None:
        row = self._rows().filter(
            school_class_id=class_id, subject__iexact=subject, exam_type=exam_type.value,
            held_on=held_on, is_active=True,
        ).first()
        return self._entity(row) if row else None

    @staticmethod
    def _rows():
        return rows.Exam.objects.select_related("school_class")

    @staticmethod
    def _entity(row: rows.Exam) -> Exam:
        return Exam(
            id=row.pk, exam_type=ExamType(row.exam_type), class_id=row.school_class_id,
            subject=row.subject, held_on=row.held_on, max_marks=row.max_marks,
            is_active=row.is_active, class_name=_class_name(row.school_class),
        )


class DjangoUnitRepository(UnitRepository):
    def get(self, entity_id: UUID) -> QuestionUnit | None:
        row = self._rows().filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def add(self, unit: QuestionUnit) -> QuestionUnit:
        row = rows.QuestionUnit.objects.create(
            teacher_id=unit.teacher_id, school_class_id=unit.class_id, subject=unit.subject,
            name=unit.name,
        )
        return self.get(row.pk)

    def update(self, unit: QuestionUnit) -> QuestionUnit:
        row = rows.QuestionUnit.objects.get(pk=unit.id)
        row.name, row.is_active = unit.name, unit.is_active
        row.save(update_fields=["name", "is_active", "updated_at"])
        return self.get(row.pk)

    def list(self, *, teacher_id: UUID | None = None, class_id: UUID | None = None,
             subject: str | None = None) -> list[QuestionUnit]:
        found = self._rows().filter(is_active=True)
        if teacher_id is not None:
            found = found.filter(teacher_id=teacher_id)
        if class_id is not None:
            found = found.filter(school_class_id=class_id)
        if subject:
            found = found.filter(subject__iexact=subject)
        ordered = sorted(found, key=lambda r: (
            ClassLevel(r.school_class.level).order, r.school_class.section,
            r.subject.lower(), r.name.lower(),
        ))
        return [self._entity(row) for row in ordered]

    def find_same(self, teacher_id: UUID, class_id: UUID, subject: str,
                  name: str) -> QuestionUnit | None:
        row = self._rows().filter(
            teacher_id=teacher_id, school_class_id=class_id, subject__iexact=subject,
            name__iexact=name, is_active=True,
        ).first()
        return self._entity(row) if row else None

    @staticmethod
    def _rows():
        return rows.QuestionUnit.objects.select_related("teacher", "school_class")

    @staticmethod
    def _entity(row: rows.QuestionUnit) -> QuestionUnit:
        return QuestionUnit(
            id=row.pk, teacher_id=row.teacher_id, class_id=row.school_class_id,
            subject=row.subject, name=row.name, is_active=row.is_active,
            class_name=_class_name(row.school_class), teacher_name=row.teacher.name,
        )


class DjangoQuestionRepository(QuestionRepository):
    def get(self, entity_id: UUID) -> Question | None:
        row = rows.Question.objects.filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def add(self, question: Question) -> Question:
        row = rows.Question.objects.create(
            unit_id=question.unit_id, text=question.text, marks=question.marks,
            question_type=question.question_type.value,
        )
        return self._entity(row)

    def update(self, question: Question) -> Question:
        row = rows.Question.objects.get(pk=question.id)
        row.text, row.marks = question.text, question.marks
        row.question_type, row.is_active = question.question_type.value, question.is_active
        row.save(update_fields=["text", "marks", "question_type", "is_active", "updated_at"])
        return self._entity(row)

    def list(self, unit_id: UUID) -> list[Question]:
        found = rows.Question.objects.filter(unit_id=unit_id, is_active=True)
        return [self._entity(row) for row in found]

    def get_many(self, ids: list[UUID]) -> dict[UUID, Question]:
        found = rows.Question.objects.filter(pk__in=ids, is_active=True)
        return {row.pk: self._entity(row) for row in found}

    @staticmethod
    def _entity(row: rows.Question) -> Question:
        return Question(
            id=row.pk, unit_id=row.unit_id, text=row.text, marks=row.marks,
            question_type=QuestionType(row.question_type), is_active=row.is_active,
        )


class DjangoPaperRepository(PaperRepository):
    def get(self, entity_id: UUID) -> Paper | None:
        row = self._rows().filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def for_exam(self, exam_id: UUID) -> Paper | None:
        row = self._rows().filter(exam_id=exam_id).first()
        return self._entity(row) if row else None

    @transaction.atomic
    def add(self, paper: Paper) -> Paper:
        row = rows.Paper.objects.create(
            exam_id=paper.exam_id, prepared_by_id=paper.prepared_by_id,
            status=paper.status.value,
        )
        self._write_items(row, paper.items)
        return self.get(row.pk)

    @transaction.atomic
    def update(self, paper: Paper) -> Paper:
        row = rows.Paper.objects.get(pk=paper.id)
        row.status, row.decided_by_id = paper.status.value, paper.decided_by_id
        row.decided_on, row.decision_note = paper.decided_on, paper.decision_note
        row.save()
        row.items.all().delete()
        self._write_items(row, paper.items)
        return self.get(row.pk)

    def list(self, *, status: PaperStatus | None = None) -> list[Paper]:
        found = self._rows()
        if status is not None:
            found = found.filter(status=status.value)
        return [self._entity(row) for row in found]

    @staticmethod
    def _write_items(row: rows.Paper, items: list[PaperItem]) -> None:
        rows.PaperItem.objects.bulk_create([
            rows.PaperItem(
                paper=row, position=item.position, question_id=item.question_id,
                text=item.text, marks=item.marks, question_type=item.question_type.value,
            )
            for item in items
        ])

    @staticmethod
    def _rows():
        return rows.Paper.objects.select_related("prepared_by").prefetch_related("items")

    @staticmethod
    def _entity(row: rows.Paper) -> Paper:
        return Paper(
            id=row.pk, exam_id=row.exam_id, prepared_by_id=row.prepared_by_id,
            prepared_by_name=row.prepared_by.name, status=PaperStatus(row.status),
            decided_by_id=row.decided_by_id, decided_on=row.decided_on,
            decision_note=row.decision_note,
            items=[
                PaperItem(i.position, i.question_id, i.text, i.marks, QuestionType(i.question_type))
                for i in row.items.all()
            ],
        )


class DjangoMarkRepository(MarkRepository):
    def save_many(self, marks: list[ExamMark]) -> None:
        for mark in marks:
            rows.ExamMark.objects.update_or_create(
                exam_id=mark.exam_id, student_id=mark.student_id,
                defaults={"marks": mark.marks, "absent": mark.absent,
                          "entered_by_id": mark.entered_by_id},
            )

    def for_exam(self, exam_id: UUID) -> dict[UUID, ExamMark]:
        return {row.student_id: self._entity(row)
                for row in rows.ExamMark.objects.filter(exam_id=exam_id)}

    def for_student(self, student_id: UUID) -> dict[UUID, ExamMark]:
        return {row.exam_id: self._entity(row)
                for row in rows.ExamMark.objects.filter(student_id=student_id)}

    def count_for_exam(self, exam_id: UUID) -> int:
        return rows.ExamMark.objects.filter(exam_id=exam_id).count()

    @staticmethod
    def _entity(row: rows.ExamMark) -> ExamMark:
        return ExamMark(
            id=row.pk, exam_id=row.exam_id, student_id=row.student_id, marks=row.marks,
            absent=row.absent, entered_by_id=row.entered_by_id,
        )
