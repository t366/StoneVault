import sqlite3
from pathlib import Path

from .schema import SCHEMA_SQL, SCHEMA_VERSION


class DatabaseError(Exception):
    pass


class Database:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version < SCHEMA_VERSION:
                conn.executescript(SCHEMA_SQL)
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
