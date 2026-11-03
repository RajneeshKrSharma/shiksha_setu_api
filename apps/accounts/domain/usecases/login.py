from apps.core.domain.usecase import UseCase

from ..ports import Authenticator, TokenIssuer, TokenPair


class Login(UseCase):
    def __init__(self, authenticator: Authenticator, tokens: TokenIssuer):
        self._authenticator = authenticator
        self._tokens = tokens

    def call(self, email: str, password: str) -> TokenPair:
        account = self._authenticator.authenticate(email, password)
        return self._tokens.issue(account)
