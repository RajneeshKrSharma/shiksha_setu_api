from uuid import UUID

from apps.accounts.domain.capabilities import POST_NOTICES
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import NotFound
from apps.core.domain.usecase import UseCase

from ..entities import Notice, NoticeKind
from ..repositories import NoticeRepository


class ListNotices(UseCase):
    def __init__(self, notices: NoticeRepository):
        self._notices = notices

    def call(self, *, kind: NoticeKind | None = None, limit: int = 50) -> list[Notice]:
        return self._notices.list(kind=kind, limit=limit)


class PostNotice(UseCase):
    def __init__(self, notices: NoticeRepository, authorizer: Authorizer, audit: AuditLogger):
        self._notices = notices
        self._authorizer = authorizer
        self._audit = audit

    def call(self, actor: UserAccount, *, kind: NoticeKind, title: str, body: str) -> Notice:
        self._authorizer.require(actor, POST_NOTICES)
        notice = Notice.post(kind=kind, title=title, body=body, posted_by_id=actor.id)
        saved = self._notices.add(notice)
        self._audit.record(actor.id, "notice_posted", f"notice:{saved.id}",
                           {"kind": kind.value, "title": saved.title})
        return saved


class WithdrawNotice(UseCase):
    """Takes a notice down. The record stays."""

    def __init__(self, notices: NoticeRepository, authorizer: Authorizer, audit: AuditLogger):
        self._notices = notices
        self._authorizer = authorizer
        self._audit = audit

    def call(self, actor: UserAccount, notice_id: UUID) -> None:
        self._authorizer.require(actor, POST_NOTICES)
        notice = self._notices.get(notice_id)
        if notice is None or not notice.is_active:
            raise NotFound("This notice was not found.")
        notice.withdraw()
        self._notices.update(notice)
        self._audit.record(actor.id, "notice_withdrawn", f"notice:{notice.id}",
                           {"title": notice.title})
