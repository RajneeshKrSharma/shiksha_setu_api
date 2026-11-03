from rest_framework import serializers

from ..domain.entities import PayeeSummary, PaymentKind, PaymentMode, SalaryRate, Statement
from ..domain.usecases.statements import PersonAccount

_MONEY = {"max_digits": 10, "decimal_places": 2}


def _money(value) -> str | None:
    return None if value is None else f"{value:.2f}"


class SalaryInput(serializers.Serializer):
    amount = serializers.DecimalField(**_MONEY)
    effective_from = serializers.CharField(max_length=7)


class SalaryRateOut(serializers.Serializer):
    def to_representation(self, rate: SalaryRate):
        return {"amount": _money(rate.amount), "effective_from": str(rate.effective_from)}


class PaymentInput(serializers.Serializer):
    person_id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=[k.value for k in PaymentKind])
    amount = serializers.DecimalField(**_MONEY)
    mode = serializers.ChoiceField(choices=[m.value for m in PaymentMode])
    paid_on = serializers.DateField(required=False)
    note = serializers.CharField(required=False, allow_blank=True, default="", max_length=200)
    month = serializers.CharField(required=False, allow_null=True, default=None, max_length=7)
    fuel_bill_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class PaymentOut(serializers.Serializer):
    id = serializers.UUIDField()
    receipt_no = serializers.CharField()
    receipt_number = serializers.IntegerField()
    person_id = serializers.UUIDField()
    person_name = serializers.CharField()
    role = serializers.CharField()
    kind = serializers.CharField()
    amount = serializers.DecimalField(**_MONEY)
    paid_on = serializers.DateField()
    mode = serializers.CharField()
    note = serializers.CharField()
    month = serializers.SerializerMethodField()
    fuel_bill_id = serializers.UUIDField(allow_null=True)

    def get_month(self, payment):
        return str(payment.month) if payment.month else None


class StatementOut(serializers.Serializer):
    def to_representation(self, statement: Statement):
        return {
            "salary": [
                {"month": str(line.month), "due": _money(line.due), "paid": _money(line.paid),
                 "balance": _money(line.balance)}
                for line in statement.salary
            ],
            "fuel_bills": [
                {"bill_id": str(line.bill_id), "billed_on": line.billed_on.isoformat(),
                 "van_name": line.van_name, "due": _money(line.due), "paid": _money(line.paid),
                 "balance": _money(line.balance)}
                for line in statement.fuel
            ],
            "total_due": _money(statement.total_due),
            "total_paid": _money(statement.total_paid),
            "balance": _money(statement.balance),
        }


class PayeeOut(serializers.Serializer):
    def to_representation(self, summary: PayeeSummary):
        return {
            "person_id": str(summary.person_id),
            "name": summary.name,
            "role": summary.role,
            "current_salary": _money(summary.current_salary),
            "salary_balance": _money(summary.statement.salary_balance),
            "fuel_balance": _money(summary.statement.fuel_balance),
            "balance": _money(summary.statement.balance),
        }


class AccountOut(serializers.Serializer):
    def to_representation(self, account: PersonAccount):
        person = account.person
        return {
            "person_id": str(person.id),
            "name": person.name,
            "role": person.role.value if person.role else None,
            "current_salary": _money(account.current_salary),
            **StatementOut(account.statement).data,
            "payments": PaymentOut(account.payments, many=True).data,
        }
