from agent.runner import AgentRunner
from data.SQLiteDatabase import SQLiteDatabase
from llm.OpenRouterClient import OpenRouterClient
from tools.ToolRegistry import ToolRegistry
from tools.database_tools import (
    ExecuteSQLTool,
    GetSchemaTool,
    ListTablesTool,
)


database = SQLiteDatabase("data/demo.sqlite")

registry = ToolRegistry()
registry.register(ListTablesTool(database))
registry.register(GetSchemaTool(database))
registry.register(ExecuteSQLTool(database))

llm = OpenRouterClient()

runner = AgentRunner(
    llm=llm,
    tool_registry=registry,
)

result = runner.run(
    "Which customer segment had the largest decline "
    "in average satisfaction from 2024 to 2025?"
)

print(result.final_answer)
print("Steps:", result.steps)
print("Tool calls:", result.tool_calls)
print("Tokens:", result.input_tokens + result.output_tokens)