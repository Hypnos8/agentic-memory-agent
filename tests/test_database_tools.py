import unittest
from pathlib import Path

from agent.models import ToolCall
from data.SQLiteDatabase import SQLiteDatabase
from tools.ToolRegistry import ToolRegistry
from tools.database_tools import ExecuteSQLTool


class TestDatabaseTools(unittest.TestCase):
    def setUp(self):

        path = Path(__file__).resolve().parents[1] / "data" / "demo.sqlite"
        if not path.is_file():
            self.fail("data/demo.sqlite fehlt. Zuerst python scripts/generate_demo_db.py ausführen.")
        self.registry = ToolRegistry()
        self.registry.register(ExecuteSQLTool(SQLiteDatabase(path)))

    def test_execute_sql_tool(self):
        call = ToolCall(
            id="1",
            name="execute_sql",
            arguments={
                "query": """
                         SELECT segment, ROUND(AVG(satisfaction_score), 1) AS avg_satisfaction
                         FROM surveys
                                  JOIN customers USING (customer_id)
                         GROUP BY segment
                         ORDER BY segment
                         """
            },
        )

        result = self.registry.execute(call)
        self.assertTrue(result.success, result.error)
        self.assertEqual(result.tool_call_id, call.id)
        self.assertIsNone(result.error)
        self.assertEqual(result.content.splitlines(), [
            "segment | avg_satisfaction",
            "--- | ---",
            "Consumer | 6.5",
            "Enterprise | 7.1",
            "SMB | 5.8",
        ])
