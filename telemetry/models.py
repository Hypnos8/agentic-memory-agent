from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunRecord:
    task_id: str
    question: str

    success: bool
    termination_reason: str | None
    final_answer: str | None

    steps: int
    tool_calls: int

    input_tokens: int
    output_tokens: int

    duration_seconds: float

    model: str
    prompt_version: str

    max_steps: int
    max_tool_calls: int

    messages: list[dict[str, Any]] = field(default_factory=list)
    llm_calls: int = 0
    total_tokens: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    configuration: dict[str, Any] = field(default_factory=dict)
    error: dict[str, str] | None = None
    memory_strategy: str = "none"
    retrieved_memories: list[dict[str, Any]] = field(
        default_factory=list
    )
