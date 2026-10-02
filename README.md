# Agentic Memory Agent

## LLM client (OpenRouter)

`llm.LLMClient.LLMClient` is the provider-independent interface from
[issue #6](https://github.com/Hypnos8/agentic-memory-agent/issues/6).
`OpenRouterClient` implements it using the standard library, with
`xiaomi/mimo-v2.5` as the default model. No provider SDK is required.
Set `OPENROUTER_API_KEY` in your process environment (or PyCharm run configuration).
For PowerShell, the syntax is:

```powershell
$env:OPENROUTER_API_KEY = "<your-openrouter-key>"
```

Do not commit the key. `.env` files are not loaded automatically.

```python
from agent.models import Message
from llm.LLMClient import LLMClient
from llm.OpenRouterClient import OpenRouterClient

client: LLMClient = OpenRouterClient()
response = client.generate([Message("user", "Say hello in German.")], tools=[])
print(response.text)
print(response.input_tokens, response.output_tokens)
```

Pass `registry.definitions()` as `tools` to enable tool calling. The adapter
returns decoded `ToolCall` objects in `response.tool_calls`. To continue after
tool execution, append the assistant response and then each tool result:

```python
messages.append(Message("assistant", response.text, tool_calls=response.tool_calls,
                        provider_metadata=response.provider_metadata))
for call in response.tool_calls:
    result = registry.execute(call)
    messages.append(Message("tool", result.content if result.success else result.error,
                            tool_call_id=result.tool_call_id))
response = client.generate(messages, registry.definitions())
```

Here `messages` is your existing conversation and `registry` is your configured
`ToolRegistry`. Preserve `provider_metadata` unchanged when replaying assistant
messages so reasoning metadata survives tool rounds. Input/output token counts
are per response; accumulate them in the agent if needed. Missing usage defaults
to zero. Missing credentials raise `LLMConfigurationError`; HTTP, connection,
and malformed-response errors raise `LLMAPIError` (both in `llm.LLMClient`).
Requests are non-streaming, have a configurable 120-second timeout, and are not
automatically retried. Tests mock HTTP and require neither credentials nor credits.

Protocol references: [OpenRouter API](https://openrouter.ai/docs/api/reference/overview)
and [tool calling](https://openrouter.ai/docs/guides/features/tool-calling).

## Trajectory logging

Every `AgentRunner.run()` appends one UTF-8 JSON line to
`logs/trajectories.jsonl`, resolved relative to the project directory. The parent
directory is created automatically and generated logs are ignored by Git.
Override the destination with `AgentRunner(..., log_path="path/to/runs.jsonl")`.

Each record contains the task ID, question, final answer, success and termination
reason, elapsed seconds, model, prompt version, token totals, conversation, and
ordered `events`. Events pair `llm_call` with `llm_response`/`llm_error`, and
`tool_call` with `tool_result`/`tool_error`. Tool IDs link requests to their
results, including failures. Model responses retain all requested tool calls,
even if an execution limit prevents some from running. `message_count` on an
LLM-call event identifies the input prefix of the recorded conversation.

`llm_calls` and `tool_calls` count attempted invocations, including exceptions;
`steps` counts returned LLM responses. Input/output tokens accumulate reported
usage, and `total_tokens` is their sum. Missing usage retains the client's zero
default. Duration measures the run before writing the log. Reproducibility
configuration includes execution limits, model, LLM timeout when available,
tool definitions, database paths, and SQL row limits.

Normal completion, execution limits, empty responses, and exceptions all write
a record. Unexpected exceptions are logged with termination reason `error` and
then re-raised. A log-write failure is raised; if the run itself already failed,
the original exception is preserved with a note about the logging failure.

Credentials and client objects are not serialized. The configured
`OPENROUTER_API_KEY` is redacted from strings, credential-bearing dictionary
fields are redacted, and opaque provider metadata is omitted. Redaction applies
only to the log copy, not to the live conversation. Logging covers runs entering
`run()`, not setup failures or forced process termination. Concurrent processes
should use separate log files.

Read records for evaluation using the standard library:

```python
import json

with open("logs/trajectories.jsonl", encoding="utf-8") as stream:
    for line in stream:
        record = json.loads(line)
        print(record["task_id"], record["termination_reason"], record["total_tokens"])
```

## Local demo database

From the repository root, run with Python 3.14 or later:

```sh
python scripts/generate_demo_db.py
```

This creates `data/demo.sqlite`, replacing any existing database at that path.
No packages, downloads, or external services are needed. To use another location:

```sh
python scripts/generate_demo_db.py --output data/test.sqlite
```

The generator uses seed **42**, fixed dates, and stable insertion order. Repeated
runs with the same Python/SQLite versions produce identical database bytes;
binary identity across different runtime versions is not guaranteed. Generated
databases live in the ignored `data/` directory and are regenerated locally.

- `customers`: 240 customers, with `customer_id`, `segment` (Consumer, SMB,
  Enterprise; 80 each), and `country` (DE, FR, GB, US, or NULL).
- `surveys`: 5,760 surveys, one per customer per month from January 2024 through
  December 2025. Columns are `survey_id`, `customer_id`, `survey_date` (ISO date),
  `satisfaction_score` (1–10), `recommendation_score` (integer 0–10), and `comment`.
- `surveys.customer_id` references `customers.customer_id`. When writing from
  another connection, enable SQLite enforcement with `PRAGMA foreign_keys = ON`.
- Approximately 5% of countries, 8% of satisfaction scores, 10% of recommendation
  scores, and 15% of comments are NULL. Missing scores are not zeros; SQL `AVG`
  excludes them. Comments are synthetic and contain no real customer information.

## Verify the known trends

Open `data/demo.sqlite` in a SQLite viewer and run this join and aggregation:

```sql
SELECT c.segment,
       substr(s.survey_date, 1, 4) AS year,
       COUNT(*) AS surveys,
       COUNT(s.satisfaction_score) AS scored_surveys,
       ROUND(AVG(s.satisfaction_score), 2) AS avg_satisfaction,
       ROUND(AVG(s.recommendation_score), 2) AS avg_recommendation
FROM customers AS c
JOIN surveys AS s ON s.customer_id = c.customer_id
GROUP BY c.segment, year
ORDER BY c.segment, year;
```

Every segment has 960 surveys each year. SMB satisfaction improves by about
1.9 points from 2024 to 2025, Enterprise declines by about 1.4 points, and Consumer
stays near 6.5. Recommendation scores follow the same trends. The monthly
satisfaction baselines change by +0.16 for SMB and -0.12 for Enterprise, with
bounded random noise; Consumer has a constant baseline. These are deliberately
simple test fixtures, not a model of real customer behavior.

Run the reproducibility, integrity, missing-value, and trend checks with:

```sh
python -m unittest discover -s tests -v
```
