from abc import ABC, abstractmethod

from .entities import ScanFile


class HandwritingReader(ABC):
    """Turns a scan into the text written on it. Which AI does it is not the domain's business."""

    @abstractmethod
    def read(self, scan: ScanFile) -> str:
        raise NotImplementedError
