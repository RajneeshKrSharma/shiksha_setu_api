from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from .entity import Entity, Person

E = TypeVar("E", bound=Entity)
P = TypeVar("P", bound=Person)


class Repository(ABC, Generic[E]):
    """What the domain needs from storage. The data layer implements it."""

    @abstractmethod
    def get(self, entity_id: UUID) -> E | None: ...

    @abstractmethod
    def add(self, entity: E) -> E: ...

    @abstractmethod
    def update(self, entity: E) -> E: ...


class MemberRepository(Repository[P]):
    """The contract every kind of member (student, teacher, staff) shares."""

    @abstractmethod
    def list(self, *, query: str = "", active: bool | None = None) -> list[P]: ...
