"""Append one sanitized JSON object per agent run."""

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from telemetry.models import RunRecord


DEFAULT_LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "trajectories.jsonl"


class TrajectoryLogger:
    def __init__(self, path: str | Path = DEFAULT_LOG_PATH):
        self.path = Path(path)
        self._api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()

    def write(self, record: RunRecord) -> None:
        # Sanitize a copy; never alter the messages used by the agent.
        line = json.dumps(self.sanitize(asdict(record)), ensure_ascii=False, allow_nan=False)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line + "\n")

    def sanitize(self, value: Any) -> Any:
        if isinstance(value, str):
            for secret in (self._api_key, os.environ.get("OPENROUTER_API_KEY", "").strip()):
                if secret:
                    value = value.replace(secret, "[REDACTED]")
            return value
        if isinstance(value, dict):
            return {
                self.sanitize(key): "[REDACTED]" if self._is_credential(key) else self.sanitize(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [self.sanitize(item) for item in value]
        return value

    @staticmethod
    def _is_credential(key: str) -> bool:
        normalized = key.lower().replace("-", "").replace("_", "")
        return any(part in normalized for part in (
            "apikey", "authorization", "password", "secret", "accesstoken", "refreshtoken"
        )) or normalized == "token"
