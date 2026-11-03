from apps.core.domain.usecase import UseCase

from ..ports import TokenIssuer, TokenPair


class RefreshSession(UseCase):
    def __init__(self, tokens: TokenIssuer):
        self._tokens = tokens

    def call(self, refresh_token: str) -> TokenPair:
        return self._tokens.refresh(refresh_token)
