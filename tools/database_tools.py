from typing import Any

from data.SQLiteDatabase import SQLiteDatabase
from tools.Tool import Tool


class ListTablesTool(Tool):
    name = "list_tables"
    description = "List all tables available in the database."

    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }

    def execute(self) -> str:
        tables = self.database.list_tables()

        if not tables:
            return "No tables found."

        return "\n".join(tables)

class GetSchemaTool(Tool):
    name = "get_schema"
    description = (
        "Inspect the columns and data types of a database table."
    )

    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to inspect.",
                    }
                },
                "required": ["table_name"],
            },
        }

    def execute(self, table_name: str) -> str:
        schema = self.database.get_schema(table_name)

        lines = [f"Table: {table_name}", ""]

        for column in schema:
            flags = []

            if column["primary_key"]:
                flags.append("PRIMARY KEY")

            if not column["nullable"]:
                flags.append("NOT NULL")

            suffix = ""
            if flags:
                suffix = f" ({', '.join(flags)})"

            lines.append(
                f"- {column['name']}: {column['type']}{suffix}"
            )

        return "\n".join(lines)
class ExecuteSQLTool(Tool):
    name = "execute_sql"
    description = (
        "Execute a read-only SQL query against the database. "
        "Only SELECT queries are allowed."
    )

    def __init__(
        self,
        database: SQLiteDatabase,
        max_rows: int = 100,
    ):
        self.database = database
        self.max_rows = max_rows

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Read-only SQLite query to execute."
                        ),
                    }
                },
                "required": ["query"],
            },
        }

    def execute(self, query: str) -> str:
        rows = self.database.execute_readonly(
            query=query,
            max_rows=self.max_rows,
        )

        if not rows:
            return "Query returned no rows."

        return self._format_rows(rows)

    @staticmethod
    def _format_rows(
        rows: list[dict[str, Any]],
    ) -> str:
        columns = list(rows[0].keys())

        lines = [
            " | ".join(columns),
            " | ".join("---" for _ in columns),
        ]

        for row in rows:
            lines.append(
                " | ".join(
                    str(row[column])
                    if row[column] is not None
                    else "NULL"
                    for column in columns
                )
            )

        return "\n".join(lines)
