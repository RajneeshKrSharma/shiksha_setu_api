from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Max, Sum
from django.db.models.functions import TruncMonth

from ..domain.entities import PayMonth, Payment, PaymentKind, PaymentMode, SalaryRate
from ..domain.repositories import PaymentRepository, SalaryRepository
from . import models as rows


class DjangoSalaryRepository(SalaryRepository):
    def history(self, person_id: UUID) -> list[SalaryRate]:
        return [self._entity(row) for row in rows.SalaryRate.objects.filter(person_id=person_id)]

    def save(self, rate: SalaryRate) -> SalaryRate:
        row, _ = rows.SalaryRate.objects.update_or_create(
            person_id=rate.person_id, effective_from=rate.effective_from.first_day,
            defaults={"amount": rate.amount, "set_by_id": rate.set_by_id},
        )
        return self._entity(row)

    @staticmethod
    def _entity(row: rows.SalaryRate) -> SalaryRate:
        return SalaryRate(
            id=row.pk, person_id=row.person_id, amount=row.amount,
            effective_from=PayMonth.of(row.effective_from), set_by_id=row.set_by_id,
        )


class DjangoPaymentRepository(PaymentRepository):
    def add(self, payment: Payment) -> Payment:
        # Receipt numbers run 1, 2, 3 ...; if two payments race for one number the
        # unique constraint rejects one and it takes the next.
        for attempt in range(5):
            number = (rows.Payment.objects.aggregate(top=Max("receipt_number"))["top"] or 0) + 1
            try:
                with transaction.atomic():
                    row = rows.Payment.objects.create(
                        person_id=payment.person_id, kind=payment.kind.value,
                        amount=payment.amount, paid_on=payment.paid_on, mode=payment.mode.value,
                        note=payment.note, paid_by_id=payment.paid_by_id,
                        month=payment.month.first_day if payment.month else None,
                        fuel_bill_id=payment.fuel_bill_id, receipt_number=number,
                    )
                return self._entity(rows.Payment.objects.select_related("person").get(pk=row.pk))
            except IntegrityError:
                if attempt == 4:
                    raise

    def list(self, *, person_id: UUID | None = None, from_date: date | None = None,
             to_date: date | None = None) -> list[Payment]:
        found = rows.Payment.objects.select_related("person")
        if person_id is not None:
            found = found.filter(person_id=person_id)
        if from_date is not None:
            found = found.filter(paid_on__gte=from_date)
        if to_date is not None:
            found = found.filter(paid_on__lte=to_date)
        return [self._entity(row) for row in found]

    def paid_by_month(self, person_id: UUID) -> dict[PayMonth, Decimal]:
        sums = (
            rows.Payment.objects.filter(person_id=person_id, kind=PaymentKind.SALARY.value)
            .values("month").annotate(total=Sum("amount"))
        )
        return {PayMonth.of(item["month"]): item["total"] for item in sums}

    def paid_by_fuel_bill(self, person_id: UUID) -> dict[UUID, Decimal]:
        sums = (
            rows.Payment.objects.filter(person_id=person_id, kind=PaymentKind.FUEL_BILL.value)
            .values("fuel_bill_id").annotate(total=Sum("amount"))
        )
        return {item["fuel_bill_id"]: item["total"] for item in sums}

    def paid_out_by_month(self, from_date: date, to_date: date
                          ) -> dict[date, dict[PaymentKind, Decimal]]:
        found = (
            rows.Payment.objects.filter(paid_on__gte=from_date, paid_on__lte=to_date)
            .annotate(bucket=TruncMonth("paid_on")).values("bucket", "kind")
            .annotate(total=Sum("amount"))
        )
        paid: dict[date, dict[PaymentKind, Decimal]] = {}
        for item in found:
            bucket = item["bucket"].date() if hasattr(item["bucket"], "date") else item["bucket"]
            paid.setdefault(bucket, {})[PaymentKind(item["kind"])] = item["total"]
        return paid

    def has_salary_payment_from(self, person_id: UUID, month: PayMonth) -> bool:
        return rows.Payment.objects.filter(
            person_id=person_id, kind=PaymentKind.SALARY.value, month__gte=month.first_day
        ).exists()

    @staticmethod
    def _entity(row: rows.Payment) -> Payment:
        return Payment(
            id=row.pk, person_id=row.person_id, kind=PaymentKind(row.kind), amount=row.amount,
            paid_on=row.paid_on, mode=PaymentMode(row.mode), paid_by_id=row.paid_by_id,
            note=row.note, month=PayMonth.of(row.month) if row.month else None,
            fuel_bill_id=row.fuel_bill_id, receipt_number=row.receipt_number,
            person_name=row.person.name, role=row.person.role,
        )
