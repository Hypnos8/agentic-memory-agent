from uuid import uuid4

from agent.models import (
    AgentResult,
    AgentState,
    Message, TerminationReason,
)

from agent.prompts import DATA_ANALYSIS_SYSTEM_PROMPT
from llm.LLMClient import LLMClient
from tools.ToolRegistry import ToolRegistry

class AgentRunner:
    def __init__(self, llm: LLMClient,
                 tool_registry: ToolRegistry,
                 max_steps: int = 10,
                 max_tool_calls: int = 15,):
        self.llm = llm
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
    def run(self, question: str) -> AgentResult:
        state = self._initialize_state(question)

        while (
                not state.completed
                and state.termination_reason is None
        ):
            if not self._check_limits(state):
                break
            self._run_step(state)
        return self._build_result(state)

    def _initialize_state(self, question:str) -> AgentState:
        return AgentState(
            task_id=str(uuid4()),
            user_question=question,
            messages=[Message(role="system", content=DATA_ANALYSIS_SYSTEM_PROMPT), Message(role="user", content=question)],
            step_count=0,
            completed=False,
        )

    def _run_step(self, state: AgentState) -> None:
        response = self.llm.generate(
            messages=state.messages,
            tools=self.tool_registry.definitions(),
        )

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
                result = self.tool_registry.execute(tool_call)

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