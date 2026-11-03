from datetime import date
from uuid import UUID

from apps.accounts.domain.capabilities import MANAGE_ACCESSORIES
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.clock import Clock
from apps.core.domain.errors import NotFound, RuleViolation
from apps.core.domain.usecase import UseCase

from ..accessories import AccessoryIssue, AccessoryItem, AccessoryKind
from ..repositories import (
    AccessoryIssueRepository,
    AccessoryItemRepository,
    ClassRepository,
    StudentRepository,
)


class _AccessoryUseCase(UseCase):
    def __init__(self, items: AccessoryItemRepository, authorizer: Authorizer,
                 audit: AuditLogger):
        self._items = items
        self._authorizer = authorizer
        self._audit = audit

    def _existing(self, item_id: UUID) -> AccessoryItem:
        item = self._items.get(item_id)
        if item is None or not item.is_active:
            raise NotFound("This item was not found.")
        return item


class ListAccessoryItems(_AccessoryUseCase):
    def call(self, actor: UserAccount, *, kind: AccessoryKind | None = None,
             class_id: UUID | None = None) -> list[AccessoryItem]:
        self._authorizer.require(actor, MANAGE_ACCESSORIES)
        return self._items.list(kind=kind, class_id=class_id)


class _ItemWriter(_AccessoryUseCase):
    def __init__(self, items: AccessoryItemRepository, classes: ClassRepository,
                 authorizer: Authorizer, audit: AuditLogger):
        super().__init__(items, authorizer, audit)
        self._classes = classes

    def _check_class(self, class_id: UUID | None) -> None:
        if class_id is None:
            return
        school_class = self._classes.get(class_id)
        if school_class is None or not school_class.is_active:
            raise RuleViolation("This class does not exist.",
                                errors={"class_id": ["Choose an existing class."]})


class AddAccessoryItem(_ItemWriter):
    def call(self, actor: UserAccount, *, kind: AccessoryKind, name: str, price,
             class_id: UUID | None = None) -> AccessoryItem:
        self._authorizer.require(actor, MANAGE_ACCESSORIES)
        self._check_class(class_id)
        saved = self._items.add(
            AccessoryItem.create(kind=kind, name=name, price=price, class_id=class_id)
        )
        self._audit.record(actor.id, "accessory_item_added", f"item:{saved.id}",
                           {"name": saved.name, "price": str(saved.price)})
        return saved


class UpdateAccessoryItem(_ItemWriter):
    """`changes` holds only what to change, from name, price and class_id (None: every class)."""

    ALLOWED = {"name", "price", "class_id"}

    def call(self, actor: UserAccount, item_id: UUID, **changes) -> AccessoryItem:
        self._authorizer.require(actor, MANAGE_ACCESSORIES)
        if not changes or not set(changes) <= self.ALLOWED:
            raise RuleViolation("Nothing to change.")
        item = self._existing(item_id)
        class_id = changes.get("class_id", item.class_id)
        self._check_class(class_id)
        item.change(name=changes.get("name", item.name), price=changes.get("price", item.price),
                    class_id=class_id)
        saved = self._items.update(item)
        self._audit.record(actor.id, "accessory_item_updated", f"item:{saved.id}",
                           {"name": saved.name, "price": str(saved.price)})
        return saved


class RemoveAccessoryItem(_AccessoryUseCase):
    """Stops the item from being sold. What was already sold stays."""

    def call(self, actor: UserAccount, item_id: UUID) -> None:
        self._authorizer.require(actor, MANAGE_ACCESSORIES)
        item = self._existing(item_id)
        item.remove()
        self._items.update(item)
        self._audit.record(actor.id, "accessory_item_removed", f"item:{item_id}",
                           {"name": item.name})


class IssueAccessory(UseCase):
    """Sells an item to a student. The price is added to what the student owes."""

    def __init__(self, items: AccessoryItemRepository, issues: AccessoryIssueRepository,
                 students: StudentRepository, authorizer: Authorizer, audit: AuditLogger,
                 clock: Clock):
        self._items = items
        self._issues = issues
        self._students = students
        self._authorizer = authorizer
        self._audit = audit
        self._clock = clock

    def call(self, actor: UserAccount, *, student_id: UUID, item_id: UUID, quantity: int = 1,
             issued_on: date | None = None) -> AccessoryIssue:
        self._authorizer.require(actor, MANAGE_ACCESSORIES)
        student = self._students.get(student_id)
        if student is None or not student.is_active:
            raise NotFound("This student was not found.")
        item = self._items.get(item_id)
        if item is None or not item.is_active:
            raise NotFound("This item was not found.")
        issue = AccessoryIssue.sell(student=student, item=item, quantity=quantity,
                                    issued_on=issued_on or self._clock.today(),
                                    issued_by_id=actor.id)
        saved = self._issues.add(issue)
        self._audit.record(actor.id, "accessory_issued", f"student:{student_id}", {
            "item": item.name, "quantity": quantity, "total": str(saved.total),
        })
        return saved


class ListAccessoryIssues(UseCase):
    def __init__(self, issues: AccessoryIssueRepository, authorizer: Authorizer):
        self._issues = issues
        self._authorizer = authorizer

    def call(self, actor: UserAccount, *, student_id: UUID | None = None,
             kind: AccessoryKind | None = None) -> list[AccessoryIssue]:
        self._authorizer.require(actor, MANAGE_ACCESSORIES)
        return self._issues.list(student_id=student_id, kind=kind)
