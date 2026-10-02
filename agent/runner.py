from uuid import uuid4
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from agent.models import (
    AgentResult,
    AgentState,
    Message, TerminationReason,
)

from agent.prompts import DATA_ANALYSIS_SYSTEM_PROMPT, SYSTEM_PROMPT_VERSION
from llm.LLMClient import LLMClient
from telemetry.logger import DEFAULT_LOG_PATH, TrajectoryLogger
from telemetry.models import RunRecord
from tools.ToolRegistry import ToolRegistry

class AgentRunner:
    def __init__(self, llm: LLMClient,
                 tool_registry: ToolRegistry,
                 max_steps: int = 10,
                 max_tool_calls: int = 15,
                 log_path: str | Path = DEFAULT_LOG_PATH):
        self.llm = llm
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        self.logger = TrajectoryLogger(log_path)

    def run(self, question: str) -> AgentResult:
        started = perf_counter()
        state = self._initialize_state(question)
        record = RunRecord(
            task_id=state.task_id, question=question, success=False,
            termination_reason=None, final_answer=None, steps=0, tool_calls=0,
            input_tokens=0, output_tokens=0, duration_seconds=0,
            model=getattr(self.llm, "model", type(self.llm).__name__),
            prompt_version=SYSTEM_PROMPT_VERSION,
            max_steps=self.max_steps, max_tool_calls=self.max_tool_calls,
        )
        run_error = None
        try:
            record.configuration = {
                "max_steps": self.max_steps,
                "max_tool_calls": self.max_tool_calls,
                "model": record.model,
                "tool_definitions": self.tool_registry.definitions(),
                "tools": self.tool_registry.logging_configuration(),
            }
            if hasattr(self.llm, "timeout"):
                record.configuration["llm_timeout_seconds"] = self.llm.timeout
            while not state.completed and state.termination_reason is None:
                if not self._check_limits(state):
                    break
                self._run_step(state, record)
            return self._build_result(state)
        except Exception as exc:
            run_error = exc
            state.completed = False
            state.termination_reason = TerminationReason.ERROR
            record.error = self._error(exc)
            raise
        finally:
            record.success = state.completed
            record.termination_reason = state.termination_reason.value if state.termination_reason else None
            record.final_answer = state.final_answer
            record.steps = state.step_count
            record.input_tokens = state.input_tokens
            record.output_tokens = state.output_tokens
            record.total_tokens = state.input_tokens + state.output_tokens
            record.duration_seconds = perf_counter() - started
            try:
                record.messages = [
                    {"role": message.role, "content": message.content,
                     "tool_calls": [asdict(call) for call in message.tool_calls],
                     "tool_call_id": message.tool_call_id}
                    for message in state.messages
                ]
                self.logger.write(record)
            except Exception as logging_error:
                if run_error is None:
                    raise
                run_error.add_note(self.logger.sanitize(
                    f"Trajectory logging also failed: {type(logging_error).__name__}: {logging_error}"
                ))

    @staticmethod
    def _error(exc: Exception) -> dict[str, str]:
        return {"type": type(exc).__name__, "message": str(exc)}

    def _initialize_state(self, question:str) -> AgentState:
        return AgentState(
            task_id=str(uuid4()),
            user_question=question,
            messages=[Message(role="system", content=DATA_ANALYSIS_SYSTEM_PROMPT), Message(role="user", content=question)],
            step_count=0,
            completed=False,
        )

    def _run_step(self, state: AgentState, record: RunRecord) -> None:
        definitions = self.tool_registry.definitions()
        record.llm_calls += 1
        record.events.append({"type": "llm_call", "llm_call": record.llm_calls,
                              "message_count": len(state.messages)})
        try:
            response = self.llm.generate(messages=state.messages, tools=definitions)
        except Exception as exc:
            record.events.append({"type": "llm_error", "llm_call": record.llm_calls,
                                  "error": self._error(exc)})
            raise
        record.events.append({
            "type": "llm_response", "llm_call": record.llm_calls,
            "text": response.text, "tool_calls": [asdict(call) for call in response.tool_calls],
            "input_tokens": response.input_tokens, "output_tokens": response.output_tokens,
        })

        state.step_count += 1
        state.input_tokens += response.input_tokens
        state.output_tokens += response.output_tokens

        state.messages.append(
            Message(
                role="assistant",
                content=response.text,
                tool_calls=response.tool_calls,
                provider_metadata=response.provider_metadata,
            )
        )

        if response.tool_calls:
            for tool_call in response.tool_calls:
                if state.tool_call_count >= self.max_tool_calls:
                    state.termination_reason = TerminationReason.MAX_TOOL_CALLS
                    return
                record.tool_calls += 1
                record.events.append({"type": "tool_call", "llm_call": record.llm_calls,
                                      **asdict(tool_call)})
                try:
                    result = self.tool_registry.execute(tool_call)
                except Exception as exc:
                    record.events.append({"type": "tool_error", "tool_call_id": tool_call.id,
                                          "error": self._error(exc)})
                    raise
                record.events.append({"type": "tool_result", **asdict(result)})

                state.tool_call_count += 1

                state.messages.append(
                    Message(
                        role="tool",
                        content=(
                            result.content
                            if result.success
                            else result.error
                        ),
                        tool_call_id=result.tool_call_id,
                    )
                )
            return

        if response.text:
            state.final_answer = response.text
            state.completed = True
            state.termination_reason = TerminationReason.COMPLETED

        if not response.tool_calls and not response.text:
            state.termination_reason = (
                TerminationReason.EMPTY_RESPONSE
            )
            return

    def _build_result(
            self,
            state: AgentState,
    ) -> AgentResult:

        return AgentResult(
            task_id=state.task_id,
            question=state.user_question,
            final_answer=state.final_answer,
            success=state.completed,
            steps=state.step_count,
            tool_calls=state.tool_call_count,
            input_tokens=state.input_tokens,
            output_tokens=state.output_tokens,
            termination_reason=state.termination_reason,
            
        )

    def _check_limits(self, state: AgentState) -> bool:
        if state.step_count >= self.max_steps:
            state.termination_reason = TerminationReason.MAX_STEPS
            return False
        if state.tool_call_count >= self.max_tool_calls:
            state.termination_reason = TerminationReason.MAX_TOOL_CALLS
            return False
        return True
