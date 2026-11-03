from abc import ABC, abstractmethod
from datetime import date, datetime


class Clock(ABC):
    """Today's date and the time now, asked from here so the rules never read the
    system clock themselves."""

    @abstractmethod
    def today(self) -> date: ...

    @abstractmethod
    def now(self) -> datetime:
        """The current moment in the school's own time zone."""
