from abc import ABC, abstractmethod


class UseCase(ABC):
    """One class per action, with one public method."""

    @abstractmethod
    def call(self, *args, **kwargs):
        raise NotImplementedError
