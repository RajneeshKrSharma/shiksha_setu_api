from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Max, Q, Sum
from django.db.models.functions import TruncMonth

from apps.core.domain.money import ZERO

from ..domain.accessories import AccessoryIssue, AccessoryItem, AccessoryKind
from ..domain.entities import ClassLevel, SchoolClass, Student
from ..domain.fees import FeeHead, FeePayment
from ..domain.repositories import (
    AccessoryIssueRepository,
    AccessoryItemRepository,
    ClassRepository,
    FeePaymentRepository,
    FeeStructureRepository,
    StudentRepository,
)
from . import models as rows


class DjangoClassRepository(ClassRepository):
    def get(self, entity_id: UUID) -> SchoolClass | None:
        row = rows.SchoolClass.objects.filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def find_active(self, level: ClassLevel, section: str) -> SchoolClass | None:
        row = rows.SchoolClass.objects.filter(
            level=level.value, section=section, is_active=True
        ).first()
        return self._entity(row) if row else None

    def add(self, school_class: SchoolClass) -> SchoolClass:
        row = rows.SchoolClass.objects.create(
            level=school_class.level.value, section=school_class.section
        )
        return self._entity(row)

    def update(self, school_class: SchoolClass) -> SchoolClass:
        row = rows.SchoolClass.objects.get(pk=school_class.id)
        row.level, row.section = school_class.level.value, school_class.section
        row.is_active = school_class.is_active
        row.save(update_fields=["level", "section", "is_active", "updated_at"])
        return self._entity(row)

    def list(self, *, active: bool | None = True) -> list[SchoolClass]:
        found = rows.SchoolClass.objects.all()
        if active is not None:
            found = found.filter(is_active=active)
        classes = [self._entity(row) for row in found]
        return sorted(classes, key=lambda c: (c.level.order, c.section))

    @staticmethod
    def _entity(row: rows.SchoolClass) -> SchoolClass:
        return SchoolClass(
            id=row.pk, level=ClassLevel(row.level), section=row.section, is_active=row.is_active
        )


class DjangoStudentRepository(StudentRepository):
    def get(self, entity_id: UUID) -> Student | None:
        row = rows.Student.objects.select_related("school_class").filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def add(self, student: Student) -> Student:
        row = rows.Student.objects.create(
            name=student.name, roll_number=student.roll_number,
            school_class_id=student.class_id, guardian_name=student.guardian_name,
            uses_van=student.uses_van,
        )
        return self.get(row.pk)

    def update(self, student: Student) -> Student:
        row = rows.Student.objects.get(pk=student.id)
        row.name, row.roll_number = student.name, student.roll_number
        row.school_class_id, row.guardian_name = student.class_id, student.guardian_name
        row.uses_van, row.is_active = student.uses_van, student.is_active
        row.save(update_fields=[
            "name", "roll_number", "school_class", "guardian_name", "uses_van",
            "is_active", "updated_at",
        ])
        return self.get(row.pk)

    def list(self, *, query: str = "", active: bool | None = None,
             class_id: UUID | None = None) -> list[Student]:
        found = rows.Student.objects.select_related("school_class")
        if active is not None:
            found = found.filter(is_active=active)
        if class_id is not None:
            found = found.filter(school_class_id=class_id)
        if query:
            found = found.filter(Q(name__icontains=query) | Q(roll_number__icontains=query))
        students = list(found)
        students.sort(key=lambda r: (
            ClassLevel(r.school_class.level).order, r.school_class.section,
            int(r.roll_number) if r.roll_number.isdigit() else 10**9, r.roll_number, r.name,
        ))
        return [self._entity(row) for row in students]

    def find_active_by_roll(self, class_id: UUID, roll_number: str) -> Student | None:
        row = rows.Student.objects.select_related("school_class").filter(
            school_class_id=class_id, roll_number=roll_number, is_active=True
        ).first()
        return self._entity(row) if row else None

    def count_active_in_class(self, class_id: UUID) -> int:
        return rows.Student.objects.filter(school_class_id=class_id, is_active=True).count()

    @staticmethod
    def _entity(row: rows.Student) -> Student:
        school_class = SchoolClass(
            level=ClassLevel(row.school_class.level), section=row.school_class.section
        )
        return Student(
            id=row.pk, name=row.name, roll_number=row.roll_number,
            class_id=row.school_class_id, guardian_name=row.guardian_name,
            uses_van=row.uses_van, is_active=row.is_active, class_name=school_class.name,
        )


class DjangoAccessoryItemRepository(AccessoryItemRepository):
    def get(self, entity_id: UUID) -> AccessoryItem | None:
        row = rows.AccessoryItem.objects.filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def add(self, item: AccessoryItem) -> AccessoryItem:
        row = rows.AccessoryItem.objects.create(
            kind=item.kind.value, name=item.name, price=item.price, school_class_id=item.class_id
        )
        return self._entity(row)

    def update(self, item: AccessoryItem) -> AccessoryItem:
        row = rows.AccessoryItem.objects.get(pk=item.id)
        row.name, row.price, row.school_class_id = item.name, item.price, item.class_id
        row.is_active = item.is_active
        row.save(update_fields=["name", "price", "school_class", "is_active", "updated_at"])
        return self._entity(row)

    def list(self, *, kind: AccessoryKind | None = None, class_id: UUID | None = None,
             active: bool = True) -> list[AccessoryItem]:
        found = rows.AccessoryItem.objects.filter(is_active=active)
        if kind is not None:
            found = found.filter(kind=kind.value)
        if class_id is not None:
            found = found.filter(Q(school_class_id=class_id) | Q(school_class__isnull=True))
        return [self._entity(row) for row in found]

    @staticmethod
    def _entity(row: rows.AccessoryItem) -> AccessoryItem:
        return AccessoryItem(
            id=row.pk, kind=AccessoryKind(row.kind), name=row.name, price=row.price,
            class_id=row.school_class_id, is_active=row.is_active,
        )


class DjangoAccessoryIssueRepository(AccessoryIssueRepository):
    def add(self, issue: AccessoryIssue) -> AccessoryIssue:
        row = rows.AccessoryIssue.objects.create(
            student_id=issue.student_id, item_id=issue.item_id, quantity=issue.quantity,
            unit_price=issue.unit_price, issued_on=issue.issued_on,
            issued_by_id=issue.issued_by_id,
        )
        return self._entity(rows.AccessoryIssue.objects.select_related("item").get(pk=row.pk))

    def list(self, *, student_id: UUID | None = None,
             kind: AccessoryKind | None = None) -> list[AccessoryIssue]:
        found = rows.AccessoryIssue.objects.select_related("item")
        if student_id is not None:
            found = found.filter(student_id=student_id)
        if kind is not None:
            found = found.filter(item__kind=kind.value)
        return [self._entity(row) for row in found]

    def total_sold(self, student_id: UUID) -> dict[AccessoryKind, Decimal]:
        totals = {kind: ZERO for kind in AccessoryKind}
        for row in rows.AccessoryIssue.objects.select_related("item").filter(student_id=student_id):
            totals[AccessoryKind(row.item.kind)] += row.unit_price * row.quantity
        return totals

    @staticmethod
    def _entity(row: rows.AccessoryIssue) -> AccessoryIssue:
        return AccessoryIssue(
            id=row.pk, student_id=row.student_id, item_id=row.item_id,
            kind=AccessoryKind(row.item.kind), item_name=row.item.name,
            quantity=row.quantity, unit_price=row.unit_price, issued_on=row.issued_on,
            issued_by_id=row.issued_by_id,
        )


class DjangoFeeStructureRepository(FeeStructureRepository):
    def amounts_for(self, class_id: UUID) -> dict[FeeHead, Decimal]:
        return {
            FeeHead(row.head): row.amount
            for row in rows.FeeAmount.objects.filter(school_class_id=class_id)
        }

    def set_amount(self, class_id: UUID, head: FeeHead, amount: Decimal) -> None:
        rows.FeeAmount.objects.update_or_create(
            school_class_id=class_id, head=head.value, defaults={"amount": amount}
        )


class DjangoFeePaymentRepository(FeePaymentRepository):
    def add(self, payment: FeePayment) -> FeePayment:
        # Receipt numbers run 1, 2, 3 ...; if two payments race for one number the
        # unique constraint rejects one and it takes the next.
        for attempt in range(5):
            number = (rows.FeePayment.objects.aggregate(top=Max("receipt_number"))["top"] or 0) + 1
            try:
                with transaction.atomic():
                    row = rows.FeePayment.objects.create(
                        student_id=payment.student_id, head=payment.head.value,
                        amount=payment.amount, paid_on=payment.paid_on, note=payment.note,
                        received_by_id=payment.received_by_id, receipt_number=number,
                    )
                return self._entity(row)
            except IntegrityError:
                if attempt == 4:
                    raise

    def list(self, *, student_id: UUID | None = None, from_date: date | None = None,
             to_date: date | None = None) -> list[FeePayment]:
        found = rows.FeePayment.objects.all()
        if student_id is not None:
            found = found.filter(student_id=student_id)
        if from_date is not None:
            found = found.filter(paid_on__gte=from_date)
        if to_date is not None:
            found = found.filter(paid_on__lte=to_date)
        return [self._entity(row) for row in found]

    def total_paid(self, student_id: UUID) -> dict[FeeHead, Decimal]:
        sums = rows.FeePayment.objects.filter(student_id=student_id).values("head").annotate(
            total=Sum("amount")
        )
        return {FeeHead(item["head"]): item["total"] for item in sums}

    def collected_by_month(self, from_date: date, to_date: date
                           ) -> dict[date, dict[FeeHead, Decimal]]:
        found = (
            rows.FeePayment.objects.filter(paid_on__gte=from_date, paid_on__lte=to_date)
            .annotate(month=TruncMonth("paid_on")).values("month", "head")
            .annotate(total=Sum("amount"))
        )
        collected: dict[date, dict[FeeHead, Decimal]] = {}
        for item in found:
            month = item["month"].date() if hasattr(item["month"], "date") else item["month"]
            collected.setdefault(month, {})[FeeHead(item["head"])] = item["total"]
        return collected

    @staticmethod
    def _entity(row: rows.FeePayment) -> FeePayment:
        return FeePayment(
            id=row.pk, student_id=row.student_id, head=FeeHead(row.head), amount=row.amount,
            paid_on=row.paid_on, received_by_id=row.received_by_id, note=row.note,
            receipt_number=row.receipt_number,
        )
