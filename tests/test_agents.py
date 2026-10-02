from agent.models import ToolCall
import unittest


class TestToolCall(unittest.TestCase):

    def test_tool_call_creation(self):
        call = ToolCall(
            id="123",
            name="execute_sql",
            arguments={"query": "SELECT 1"}
        )

        self.assertEqual(call.name, "execute_sql")
        self.assertEqual(call.arguments["query"], "SELECT 1")
