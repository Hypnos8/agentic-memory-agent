from dataclasses import dataclass,field
from enum import Enum
from typing import Any

@dataclass
class Message:
    role: str
    content: str | None
    tool_calls: list["ToolCall"] = field(default_factory=list)
    tool_call_id: str | None = None
    provider_metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]

@dataclass
class ToolResult:
    tool_call_id: str
    success: bool
    content: str
    error: str | None=None

@dataclass
class AgentResponse:
    text: str | None=None
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    provider_metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentState:
    task_id: str
    user_question: str
    messages: list[Message] = field(default_factory=list)
    step_count: int = 0
    tool_call_count: int = 0
    termination_reason: TerminationReason | None = None
    completed: bool = False
    final_answer: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0

@dataclass
class AgentResult:
    task_id: str
    question: str
    final_answer: str | None
    success: bool
    steps: int
    tool_calls: int
    input_tokens: int
    output_tokens: int
    termination_reason: TerminationReason | None

class TerminationReason(str, Enum):
    COMPLETED = "completed"
    MAX_STEPS = "max_steps"
    MAX_TOOL_CALLS = "max_tool_calls"
    EMPTY_RESPONSE = "empty_response"