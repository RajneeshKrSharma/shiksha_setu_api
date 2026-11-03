from apps.accounts.domain.capabilities import MANAGE_QUESTION_BANK, PREPARE_QUESTIONS
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.errors import RuleViolation
from apps.core.domain.usecase import UseCase

from ..entities import PageText, ScanFile
from ..readers import HandwritingReader

MAX_FILES = 6
MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = ("image/jpeg", "image/png", "image/webp", "application/pdf")


class ReadHandwriting(UseCase):
    """A teacher hands in photos or PDFs of handwritten pages and gets the text back,
    one result per file, exactly as written."""

    def __init__(self, reader: HandwritingReader, authorizer: Authorizer):
        self._reader = reader
        self._authorizer = authorizer

    def call(self, actor: UserAccount, files: list[ScanFile]) -> list[PageText]:
        self._authorize(actor)
        self._check(files)
        return [PageText(scan.name, self._reader.read(scan)) for scan in files]

    def _authorize(self, actor: UserAccount | None) -> None:
        self._authorizer.require_any(actor, PREPARE_QUESTIONS, MANAGE_QUESTION_BANK)

    @staticmethod
    def _check(files: list[ScanFile]) -> None:
        if not files:
            raise RuleViolation("Choose at least one photo or PDF.")
        if len(files) > MAX_FILES:
            raise RuleViolation(f"Send at most {MAX_FILES} files at a time.")
        for scan in files:
            if scan.mime_type not in ALLOWED_TYPES:
                raise RuleViolation(f"{scan.name}: only JPG, PNG, WebP or PDF files are accepted.")
            if not scan.data:
                raise RuleViolation(f"{scan.name} is empty.")
            if len(scan.data) > MAX_FILE_BYTES:
                raise RuleViolation(f"{scan.name} is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")


class ReadHandwritingWithoutSignIn(ReadHandwriting):
    """The same reading with no sign-in. Only for trying the reader by hand while developing;
    the container hands it out only when DEBUG is on."""

    def _authorize(self, actor: UserAccount | None) -> None:
        return None
