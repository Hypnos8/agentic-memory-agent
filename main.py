from pathlib import Path

from data.SQLiteDatabase import SQLiteDatabase
from tools.ToolRegistry import ToolRegistry
from tools.database_tools import ListTablesTool, GetSchemaTool, ExecuteSQLTool

database = SQLiteDatabase(Path(__file__).resolve().parent / "data" / "demo.sqlite")
registry = ToolRegistry()

registry.register(
    ListTablesTool(database)
)

registry.register(
    GetSchemaTool(database)
)

registry.register(
    ExecuteSQLTool(database)
)
