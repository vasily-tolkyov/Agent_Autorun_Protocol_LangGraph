from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


@asynccontextmanager
async def create_checkpointer():
    root = Path(__file__).resolve().parents[2]
    var_dir = root / "var"
    var_dir.mkdir(parents=True, exist_ok=True)
    database_path = var_dir / "langgraph-checkpoints.sqlite"
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        yield saver
