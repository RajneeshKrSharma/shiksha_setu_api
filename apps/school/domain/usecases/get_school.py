from apps.core.domain.usecase import UseCase

from ..entities import School
from ..repositories import SchoolRepository


class GetSchool(UseCase):
    def __init__(self, schools: SchoolRepository):
        self._schools = schools

    def call(self) -> School:
        return self._schools.current()
