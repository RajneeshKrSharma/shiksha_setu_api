from apps.core.domain.usecase import UseCase

from ..entities import UserAccount
from ..repositories import UserRepository


class UpdateMyName(UseCase):
    def __init__(self, users: UserRepository):
        self._users = users

    def call(self, actor: UserAccount, name: str) -> UserAccount:
        actor.rename(name)
        return self._users.update(actor)
