import base64
import json
import logging
import ssl
import time
import urllib.error
import urllib.request

import certifi

from apps.core.domain.errors import ExternalServiceError

from ..domain.entities import ScanFile
from ..domain.readers import HandwritingReader

log = logging.getLogger("handwriting")
if not log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[handwriting] %(message)s"))
    log.addHandler(_handler)
    log.setLevel(logging.INFO)
    log.propagate = False

# Gemini answers 429 or 5xx while it is overloaded.
_BUSY = (429, 500, 502, 503, 504)

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_PROMPT = """This is a photo or scan of handwritten school work. The writing is English, Hindi (Devanagari), or both. The page may be tilted or upside down.

Copy all the text exactly as it is written, in the order it is written.
- Keep every number, label, bracket and line break as on the page.
- Keep Hindi in Devanagari and English in English. Do not translate, correct, complete or explain anything.
- Where a word cannot be read with confidence, write [?] in its place. Never guess.
- Do not copy anything that is crossed out.
- Write nothing before or after the copied text.
"""


class GeminiHandwritingReader(HandwritingReader):
    """Reads handwriting with Google's Gemini vision models over their REST API. The models are
    tried in order: when one is busy or too slow, the next one gets the same scan."""

    def __init__(self, api_key: str, models: list[str], timeout: int = 25):
        self._api_key = api_key
        self._models = models
        self._timeout = timeout
        # Python from python.org ships without root certificates, so use certifi's.
        self._tls = ssl.create_default_context(cafile=certifi.where())

    def read(self, scan: ScanFile) -> str:
        if not self._api_key or not self._models:
            raise ExternalServiceError("The handwriting reader is not set up on the server.",
                                       code="reader_not_configured")
        started = time.monotonic()
        failure: ExternalServiceError | None = None
        for model in self._models:
            try:
                text = self._ask(model, scan)
            except ExternalServiceError as error:
                failure = error
                log.info("%s: %s did not work after %.1fs (%s)", scan.name, model,
                         time.monotonic() - started, error.code)
                continue
            log.info("%s read by %s in %.1fs, %d characters", scan.name, model,
                     time.monotonic() - started, len(text))
            return text
        raise failure

    def _ask(self, model: str, scan: ScanFile) -> str:
        request = urllib.request.Request(
            _ENDPOINT.format(model=model),
            data=json.dumps(self._body(scan)).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": self._api_key},
            method="POST",
        )
        log.info("sending %s (%d KB) to %s", scan.name, len(scan.data) // 1024, model)
        try:
            with urllib.request.urlopen(request, timeout=self._timeout, context=self._tls) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            raise ExternalServiceError(self._explain(error.code), code=f"http_{error.code}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise ExternalServiceError("Could not reach the handwriting reader. Try again.",
                                       code="reader_unreachable") from error
        return self._text_of(payload)

    @staticmethod
    def _body(scan: ScanFile) -> dict:
        return {
            "contents": [{"parts": [
                {"text": _PROMPT},
                {"inline_data": {"mime_type": scan.mime_type,
                                 "data": base64.b64encode(scan.data).decode("ascii")}},
            ]}],
            "generationConfig": {"temperature": 0},
        }

    @staticmethod
    def _text_of(payload: dict) -> str:
        try:
            parts = payload["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError) as error:
            raise ExternalServiceError("The reader sent back nothing. Try another photo.",
                                       code="reader_empty") from error
        return "".join(part.get("text", "") for part in parts).strip()

    @staticmethod
    def _explain(status: int) -> str:
        if status in (400, 403):
            return "The handwriting reader refused the request. Check its key and model."
        if status in _BUSY:
            return "The handwriting reader (Gemini) is overloaded right now. Try again in a minute."
        return "The handwriting reader had a problem. Try again."
