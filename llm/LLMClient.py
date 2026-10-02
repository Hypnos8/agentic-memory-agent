from abc import ABC, abstractmethod
from typing import Any

from agent.models import Message, AgentResponse


class LLMConfigurationError(ValueError):
    """The client cannot start with the supplied configuration."""


class LLMAPIError(RuntimeError):
    """The provider request failed or returned an invalid response."""


class LLMClient(ABC):

    @abstractmethod
    def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
    ) -> AgentResponse:
        """
        Generate the next agent response.

        The implementation may return either:
        - plain text
        - one or more tool calls
        """
        raise NotImplementedError
