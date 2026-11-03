from dataclasses import dataclass
from uuid import UUID

from .errors import RuleViolation


@dataclass(eq=False, kw_only=True)
class Entity:
    """Identity is the id: two objects with the same id are the same thing."""

    id: UUID | None = None

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Entity) and self.id is not None and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass(eq=False, kw_only=True)
class Person(Entity):
    """The base every person in the school is built on (Student, Teacher, Staff, ...)."""

    NAME_MAX = 120

    name: str
    email: str = ""
    is_active: bool = True

    def rename(self, name: str) -> None:
        name = name.strip()
        if not name or len(name) > self.NAME_MAX:
            raise RuleViolation(
                f"Required, up to {self.NAME_MAX} characters.",
                errors={"name": [f"Required, up to {self.NAME_MAX} characters."]},
            )
        self.name = name

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False
