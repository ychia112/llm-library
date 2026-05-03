import sqlite3
import sqlite_vec
from pathlib import Path

class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.create_tables()

    def create_tables(self):
        # Implementation for sessions and session_vectors tables
        pass
