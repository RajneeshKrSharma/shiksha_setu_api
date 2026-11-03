from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from apps.core.domain.entity import Entity
from apps.core.domain.errors import RuleViolation
from apps.core.domain.money import Money

from .entities import Student


def _invalid(field: str, message: str) -> RuleViolation:
    return RuleViolation(message, errors={field: [message]})


class AccessoryKind(StrEnum):
    DRESS = "dress"
    BOOKS = "books"


@dataclass(eq=False, kw_only=True)
class AccessoryItem(Entity):
    """Something the school sells: a dress piece or a book set. With no class it is
    for every class."""

    NAME_MAX = 80

    kind: AccessoryKind
    name: str
    price: Decimal
    class_id: UUID | None = None
    is_active: bool = True

    @classmethod
    def create(cls, *, kind: AccessoryKind, name: str, price, class_id: UUID | None) -> "AccessoryItem":
        item = cls(kind=kind, name="-", price=Decimal("0.00"), class_id=class_id)
        item.change(name=name, price=price, class_id=class_id)
        return item

    def change(self, *, name: str, price, class_id: UUID | None) -> None:
        name = name.strip()
        if not name or len(name) > self.NAME_MAX:
            raise _invalid("name", f"Required, up to {self.NAME_MAX} characters.")
        self.name = name
        self.price = Money.parse(price, field="price")
        self.class_id = class_id

    def remove(self) -> None:
        self.is_active = False

    def is_for(self, student: Student) -> bool:
        return self.class_id is None or self.class_id == student.class_id


@dataclass(eq=False, kw_only=True)
class AccessoryIssue(Entity):
    """One sale to a student. The price is copied at the time, so a later price
    change never alters what the student owes."""

    QUANTITY_MAX = 100

    student_id: UUID
    item_id: UUID
    kind: AccessoryKind
    item_name: str = ""
    quantity: int
    unit_price: Decimal
    issued_on: date
    issued_by_id: UUID | None = None

    @classmethod
    def sell(cls, *, student: Student, item: AccessoryItem, quantity: int, issued_on: date,
             issued_by_id: UUID) -> "AccessoryIssue":
        if not 1 <= quantity <= cls.QUANTITY_MAX:
            raise _invalid("quantity", f"Between 1 and {cls.QUANTITY_MAX}.")
        if not item.is_for(student):
            raise _invalid("item_id", "This item is for another class.")
        return cls(student_id=student.id, item_id=item.id, kind=item.kind,
                   item_name=item.name, quantity=quantity, unit_price=item.price,
                   issued_on=issued_on, issued_by_id=issued_by_id)

    @property
    def total(self) -> Decimal:
        return self.unit_price * self.quantity
