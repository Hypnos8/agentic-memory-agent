import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


class SQLiteDatabase:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def list_tables(self) -> list[str]:
        query = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name;
        """

        with closing(self._connect()) as connection:
            rows = connection.execute(query).fetchall()

        return [row["name"] for row in rows]

    def get_schema(self, table_name: str) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"PRAGMA table_info({self._quote_identifier(table_name)})"
            ).fetchall()

        if not rows:
            raise ValueError(f"Unknown table: {table_name}")

        return [
            {
                "name": row["name"],
                "type": row["type"],
                "nullable": not bool(row["notnull"]),
                "primary_key": bool(row["pk"]),
            }
            for row in rows
        ]

    def execute_readonly(
        self,
        query: str,
        max_rows: int = 100,
    ) -> list[dict[str, Any]]:
        self._validate_readonly_query(query)

        with closing(self._connect()) as connection:
            cursor = connection.execute(query)
            rows = cursor.fetchmany(max_rows)

        return [dict(row) for row in rows]

    @staticmethod
    def _validate_readonly_query(query: str) -> None:
        stripped = query.strip()

        if not stripped:
            raise ValueError("SQL query must not be empty.")

        first_token = stripped.split(maxsplit=1)[0].upper()

        if first_token not in {"SELECT", "WITH"}:
            raise ValueError(
                "Only read-only SELECT queries are allowed."
            )

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'
