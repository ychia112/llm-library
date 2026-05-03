import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import sqlite_vec

from llmlib.models import Message, Session


class LibraryDB:
    """Manages the local SQLite database with vector search capabilities via sqlite-vec."""
    DEFAULT_DB_PATH = Path("~/.llmlib/library.db").expanduser()
    DEFAULT_EMBEDDING_DIM = 1536

    def __init__(self, db_path: Optional[Path] = None):
        """Initializes the database connection and ensures tables exist."""
        self.db_path = (db_path or self.DEFAULT_DB_PATH).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.init_db()

    def init_db(self) -> None:
        """Initializes the database schema."""
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    topic TEXT,
                    tags TEXT NOT NULL,
                    question_type TEXT,
                    summary TEXT,
                    embedding_id INTEGER,
                    messages TEXT NOT NULL
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS library_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_platform
                ON sessions(platform)
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_question_type
                ON sessions(question_type)
                """
            )
            self.conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_embedding_id
                ON sessions(embedding_id)
                WHERE embedding_id IS NOT NULL
                """
            )

            dim = self._get_embedding_dim()
            if dim is None:
                dim = self.DEFAULT_EMBEDDING_DIM
                self.conn.execute(
                    "INSERT INTO library_meta(key, value) VALUES('embedding_dim', ?)",
                    (str(dim),),
                )
            self._create_vector_table_if_missing(dim)

    def upsert_session(self, session: Session, embedding: list[float]) -> None:
        """Inserts or updates a session and its corresponding vector embedding."""
        embedding_dim = len(embedding)
        if embedding_dim == 0:
            raise ValueError("embedding must not be empty")

        self._ensure_embedding_dim(embedding_dim)
        embedding_payload = self._serialize_embedding(embedding)

        with self.conn:
            existing_embedding_id = self._get_existing_embedding_id(session.id)
            target_embedding_id = session.embedding_id or existing_embedding_id

            if target_embedding_id is None:
                cursor = self.conn.execute(
                    "INSERT INTO session_vectors(embedding) VALUES (?)",
                    (embedding_payload,),
                )
                target_embedding_id = cursor.lastrowid
            else:
                self.conn.execute(
                    "DELETE FROM session_vectors WHERE rowid = ?",
                    (target_embedding_id,),
                )
                self.conn.execute(
                    "INSERT INTO session_vectors(rowid, embedding) VALUES (?, ?)",
                    (target_embedding_id, embedding_payload),
                )

            self.conn.execute(
                """
                INSERT INTO sessions(
                    id, source_id, platform, title, created_at, updated_at,
                    topic, tags, question_type, summary, embedding_id, messages
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    source_id=excluded.source_id,
                    platform=excluded.platform,
                    title=excluded.title,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    topic=excluded.topic,
                    tags=excluded.tags,
                    question_type=excluded.question_type,
                    summary=excluded.summary,
                    embedding_id=excluded.embedding_id,
                    messages=excluded.messages
                """,
                (
                    session.id,
                    session.source_id,
                    session.platform,
                    session.title,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                    session.topic,
                    json.dumps(session.tags, ensure_ascii=False),
                    session.question_type,
                    session.summary,
                    target_embedding_id,
                    json.dumps([msg.model_dump(mode="json") for msg in session.messages], ensure_ascii=False),
                ),
            )

            session.embedding_id = target_embedding_id

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[Session]:
        """Searches for sessions similar to the provided query embedding."""
        if top_k <= 0:
            return []
        if not query_embedding:
            raise ValueError("query_embedding must not be empty")

        self._ensure_embedding_dim(len(query_embedding))

        rows = self.conn.execute(
            """
            SELECT s.*
            FROM (
                SELECT rowid, distance
                FROM session_vectors
                WHERE embedding MATCH ? AND k = ?
            ) AS v
            JOIN sessions AS s ON s.embedding_id = v.rowid
            ORDER BY v.distance ASC
            """,
            (self._serialize_embedding(query_embedding), top_k),
        ).fetchall()
        return [self._row_to_session(row) for row in rows]

    def get_session(self, session_id: str) -> Session | None:
        """Retrieves a single session by its unique ID."""
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_session(row)

    def list_sessions(
        self,
        tag: Optional[str] = None,
        platform: Optional[str] = None,
        question_type: Optional[str] = None,
    ) -> list[Session]:
        """Lists sessions with optional filtering by tag, platform, or question type."""
        clauses = ["1=1"]
        params: list[Any] = []

        if platform:
            clauses.append("platform = ?")
            params.append(platform)
        if question_type:
            clauses.append("question_type = ?")
            params.append(question_type)
        if tag:
            clauses.append("EXISTS (SELECT 1 FROM json_each(sessions.tags) WHERE json_each.value = ?)")
            params.append(tag)

        query = f"""
            SELECT *
            FROM sessions
            WHERE {' AND '.join(clauses)}
            ORDER BY updated_at DESC
        """
        rows = self.conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_session(row) for row in rows]

    def delete_session(self, session_id: str) -> None:
        """Deletes a session and its corresponding vector embedding from the database."""
        row = self.conn.execute(
            "SELECT embedding_id FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()

        with self.conn:
            self.conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            if row is not None and row["embedding_id"] is not None:
                self.conn.execute(
                    "DELETE FROM session_vectors WHERE rowid = ?",
                    (row["embedding_id"],),
                )

    def close(self) -> None:
        """Closes the database connection."""
        self.conn.close()

    def _create_vector_table_if_missing(self, dim: int) -> None:
        table_exists = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='session_vectors'"
        ).fetchone()
        if table_exists is None:
            self.conn.execute(
                f"CREATE VIRTUAL TABLE session_vectors USING vec0(embedding float[{dim}])"
            )

    def _recreate_vector_table(self, dim: int) -> None:
        self.conn.execute("DROP TABLE IF EXISTS session_vectors")
        self.conn.execute(
            f"CREATE VIRTUAL TABLE session_vectors USING vec0(embedding float[{dim}])"
        )

    def _get_embedding_dim(self) -> Optional[int]:
        row = self.conn.execute(
            "SELECT value FROM library_meta WHERE key = 'embedding_dim'"
        ).fetchone()
        if row is None:
            return None
        return int(row["value"])

    def _set_embedding_dim(self, dim: int) -> None:
        self.conn.execute(
            """
            INSERT INTO library_meta(key, value)
            VALUES('embedding_dim', ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (str(dim),),
        )

    def _ensure_embedding_dim(self, dim: int) -> None:
        existing_dim = self._get_embedding_dim()
        if existing_dim is None:
            with self.conn:
                self._set_embedding_dim(dim)
                self._recreate_vector_table(dim)
            return

        if existing_dim == dim:
            self._create_vector_table_if_missing(dim)
            return

        count_row = self.conn.execute("SELECT COUNT(*) AS c FROM session_vectors").fetchone()
        count = int(count_row["c"]) if count_row is not None else 0
        if count > 0:
            raise ValueError(
                f"embedding dimension mismatch: expected {existing_dim}, got {dim}"
            )

        with self.conn:
            self._set_embedding_dim(dim)
            self._recreate_vector_table(dim)

    def _get_existing_embedding_id(self, session_id: str) -> Optional[int]:
        row = self.conn.execute(
            "SELECT embedding_id FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None or row["embedding_id"] is None:
            return None
        return int(row["embedding_id"])

    def _serialize_embedding(self, embedding: list[float]) -> str:
        return json.dumps([float(v) for v in embedding], ensure_ascii=False)

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        tags = json.loads(row["tags"]) if row["tags"] else []
        raw_messages = json.loads(row["messages"]) if row["messages"] else []
        messages = [Message.model_validate(msg) for msg in raw_messages]

        return Session(
            id=row["id"],
            source_id=row["source_id"],
            platform=row["platform"],
            title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            messages=messages,
            topic=row["topic"],
            tags=tags,
            question_type=row["question_type"],
            summary=row["summary"],
            embedding_id=row["embedding_id"],
        )


class Database(LibraryDB):
    pass
