from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID


class LeaveCalendar(ABC):
    """Who is on approved leave. The requests module answers this; attendance only asks."""

    @abstractmethod
    def people_on_leave(self, day: date) -> frozenset[UUID]: ...
