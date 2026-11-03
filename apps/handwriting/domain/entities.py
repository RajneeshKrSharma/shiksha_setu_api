from dataclasses import dataclass


@dataclass(frozen=True)
class ScanFile:
    """One photo or PDF page-set the teacher handed in."""

    name: str
    mime_type: str
    data: bytes


@dataclass(frozen=True)
class PageText:
    """What was written in one scan, exactly as the reader found it."""

    name: str
    text: str
