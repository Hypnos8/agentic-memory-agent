from datetime import datetime, timezone
from dataclasses import dataclass, field


@dataclass
class Experience:
    id: str
    content: str
    source_task_id: str | None= None

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)
