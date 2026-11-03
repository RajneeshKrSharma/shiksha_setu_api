from datetime import date, datetime

from django.utils import timezone

from apps.core.domain.clock import Clock


class SystemClock(Clock):
    def today(self) -> date:
        return timezone.localdate()

    def now(self) -> datetime:
        return timezone.localtime()
