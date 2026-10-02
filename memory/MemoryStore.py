from abc import ABC, abstractmethod

from memory.models import Experience


class MemoryStore(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the memory store."""
        raise NotImplementedError
    @abstractmethod
    def retrieve(self, task: str, k: int=5) -> list[Experience]:
        raise NotImplementedError
    @abstractmethod
    def store(self, experience: Experience) -> None:
        """Store the experience in the memory store."""
        raise NotImplementedError

