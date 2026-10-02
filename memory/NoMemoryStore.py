from memory.MemoryStore import MemoryStore
from memory.models import Experience


class NoMemoryStore(MemoryStore):
    @property
    def name(self) -> str:
        return "no_memory"

    def retrieve(self, task: str, k: int=5) -> list[Experience]:
        return []
    def store(self, experience: Experience) -> None:
        pass