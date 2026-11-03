from rest_framework import serializers

from ..domain.accessories import AccessoryKind
from ..domain.entities import ClassLevel
from ..domain.fees import FeeHead
from ..domain.usecases.fees import StudentFees

_MONEY = {"max_digits": 10, "decimal_places": 2}


# ---- classes
class ClassInput(serializers.Serializer):
    level = serializers.ChoiceField(choices=[level.value for level in ClassLevel])
    section = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="", max_length=3)


class ClassPatchInput(serializers.Serializer):
    level = serializers.ChoiceField(required=False, choices=[level.value for level in ClassLevel])
    section = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=3)


class ClassOut(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    level = serializers.CharField()
    section = serializers.CharField()
    is_active = serializers.BooleanField()


# ---- students
class StudentInput(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    # Left out, the student gets the next free number in the class.
    roll_number = serializers.CharField(max_length=10, required=False, allow_blank=True, default="")
    class_id = serializers.UUIDField()
    guardian_name = serializers.CharField(max_length=120)
    uses_van = serializers.BooleanField(required=False, default=False)


class StudentPatchInput(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=120)
    roll_number = serializers.CharField(required=False, max_length=10)
    class_id = serializers.UUIDField(required=False)
    guardian_name = serializers.CharField(required=False, max_length=120)
    uses_van = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


class StudentOut(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    roll_number = serializers.CharField()
    class_id = serializers.UUIDField()
    class_name = serializers.CharField()
    guardian_name = serializers.CharField()
    uses_van = serializers.BooleanField()
    is_active = serializers.BooleanField()


# ---- dress and books
class ItemInput(serializers.Serializer):
    kind = serializers.ChoiceField(choices=[kind.value for kind in AccessoryKind])
    name = serializers.CharField(max_length=80)
    price = serializers.DecimalField(**_MONEY)
    class_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class ItemPatchInput(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=80)
    price = serializers.DecimalField(required=False, **_MONEY)
    class_id = serializers.UUIDField(required=False, allow_null=True)


class ItemOut(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    name = serializers.CharField()
    price = serializers.DecimalField(**_MONEY)
    class_id = serializers.UUIDField(allow_null=True)
    is_active = serializers.BooleanField()


class IssueInput(serializers.Serializer):
    student_id = serializers.UUIDField()
    item_id = serializers.UUIDField()
    quantity = serializers.IntegerField(required=False, default=1)
    issued_on = serializers.DateField(required=False)


class IssueOut(serializers.Serializer):
    id = serializers.UUIDField()
    student_id = serializers.UUIDField()
    item_id = serializers.UUIDField()
    kind = serializers.CharField()
    item_name = serializers.CharField()
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(**_MONEY)
    total = serializers.DecimalField(**_MONEY)
    issued_on = serializers.DateField()


# ---- fees
class FeeAmountInput(serializers.Serializer):
    amount = serializers.DecimalField(**_MONEY)


class StructureOut(serializers.Serializer):
    """One fixed fee of a class; an amount of null means not set yet."""

    head = serializers.CharField()
    label = serializers.CharField(source="head.label")
    amount = serializers.DecimalField(allow_null=True, **_MONEY)


class PaymentInput(serializers.Serializer):
    student_id = serializers.UUIDField()
    head = serializers.ChoiceField(choices=[head.value for head in FeeHead])
    amount = serializers.DecimalField(**_MONEY)
    paid_on = serializers.DateField(required=False)
    note = serializers.CharField(required=False, allow_blank=True, default="", max_length=200)


class PaymentOut(serializers.Serializer):
    id = serializers.UUIDField()
    receipt_no = serializers.CharField()
    receipt_number = serializers.IntegerField()
    student_id = serializers.UUIDField()
    head = serializers.CharField()
    amount = serializers.DecimalField(**_MONEY)
    paid_on = serializers.DateField()
    note = serializers.CharField()


class StatementOut(serializers.Serializer):
    def to_representation(self, statement):
        student = statement.student
        return {
            "student_id": str(student.id),
            "student_name": student.name,
            "roll_number": student.roll_number,
            "class_id": str(student.class_id),
            "class_name": student.class_name,
            "uses_van": student.uses_van,
            "heads": [
                {
                    "head": line.head.value, "label": line.head.label,
                    "due": f"{line.due:.2f}", "paid": f"{line.paid:.2f}",
                    "balance": f"{line.balance:.2f}",
                }
                for line in statement.lines
            ],
            "total_due": f"{statement.total_due:.2f}",
            "total_paid": f"{statement.total_paid:.2f}",
            "balance": f"{statement.balance:.2f}",
        }


class StudentFeesOut(serializers.Serializer):
    def to_representation(self, fees: StudentFees):
        data = StatementOut(fees.statement).data
        data["payments"] = PaymentOut(fees.payments, many=True).data
        return data
