import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import sqlite_vec
from sqlite_vec import serialize_float32

from llmlib.models import Message, Session


class LibraryDB:
    """Manages the local SQLite database with vector search capabilities via sqlite-vec."""
    DEFAULT_DB_PATH = Path("~/.llmlib/library.db").expanduser()

    def __init__(self, db_path: Optional[Path] = None):
        """Initializes the database connection and ensures tables exist."""
        self.db_path = (db_path or self.DEFAULT_DB_PATH).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # FastAPI dependencies can cross thread boundaries (worker -> event loop),
        # so disable sqlite's same-thread guard for this local single-process DB usage.
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        self.init_db()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

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
                    key_entities TEXT NOT NULL DEFAULT '[]',
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
            
            # Migration check
            cursor = self.conn.execute("PRAGMA table_info(sessions)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "key_entities" not in columns:
                self.conn.execute("ALTER TABLE sessions ADD COLUMN key_entities TEXT NOT NULL DEFAULT '[]'")

            dim = self._get_embedding_dim()
            if dim is not None:
                self._create_vector_table_if_missing(dim)

    def upsert_session(self, session: Session, embedding: list[float]) -> None:
        embedding_dim = len(embedding)
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
                self.conn.execute("DELETE FROM session_vectors WHERE rowid = ?", (target_embedding_id,))
                self.conn.execute("INSERT INTO session_vectors(rowid, embedding) VALUES (?, ?)", (target_embedding_id, embedding_payload))

            self.conn.execute(
                """
                INSERT INTO sessions(
                    id, source_id, platform, title, created_at, updated_at,
                    topic, tags, key_entities, question_type, summary, embedding_id, messages
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    source_id=excluded.source_id, platform=excluded.platform, title=excluded.title,
                    created_at=excluded.created_at, updated_at=excluded.updated_at,
                    topic=excluded.topic, tags=excluded.tags, key_entities=excluded.key_entities,
                    question_type=excluded.question_type, summary=excluded.summary,
                    embedding_id=excluded.embedding_id, messages=excluded.messages
                """,
                (
                    session.id, session.source_id, session.platform, session.title,
                    session.created_at.isoformat(), session.updated_at.isoformat(),
                    session.topic, json.dumps(session.tags, ensure_ascii=False),
                    json.dumps(session.key_entities, ensure_ascii=False),
                    session.question_type, session.summary, target_embedding_id,
                    json.dumps([msg.model_dump(mode="json") for msg in session.messages], ensure_ascii=False),
                ),
            )
            session.embedding_id = target_embedding_id

    def search_with_scores(self, query_embedding: list[float], top_k: int = 5) -> list[tuple[Session, float]]:
        if not query_embedding: return []
        table_exists = self.conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='session_vectors'").fetchone()
        if not table_exists: return []
        
        # Ensure we have data
        count = self.conn.execute("SELECT COUNT(*) FROM session_vectors").fetchone()[0]
        if count == 0: return []

        self._ensure_embedding_dim(len(query_embedding))
        rows = self.conn.execute(
            """
            SELECT s.*, v.distance FROM (
                SELECT rowid, distance FROM session_vectors WHERE embedding MATCH ? AND k = ?
            ) AS v JOIN sessions AS s ON s.embedding_id = v.rowid ORDER BY v.distance ASC
            """,
            (self._serialize_embedding(query_embedding), top_k),
        ).fetchall()
        return [(self._row_to_session(row), max(0.0, min(1.0, 1.0 - float(row["distance"])))) for row in rows]

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[Session]:
        """Backwards-compatible search API: returns sessions only."""
        return [session for session, _ in self.search_with_scores(query_embedding, top_k=top_k)]

    def get_session(self, session_id: str) -> Session | None:
        row = self.conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return self._row_to_session(row) if row else None

    def delete_session(self, session_id: str) -> None:
        row = self.conn.execute("SELECT embedding_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        with self.conn:
            self.conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            if row is not None and row["embedding_id"] is not None:
                self.conn.execute("DELETE FROM session_vectors WHERE rowid = ?", (row["embedding_id"],))

    def list_sessions(
        self,
        tag=None,
        platform=None,
        question_type=None,
        topic=None,
        limit=50,
        offset=0,
        return_total: bool = False,
    ):
        clauses = ["1=1"]
        params = []
        if platform: clauses.append("platform = ?"); params.append(platform)
        if question_type: clauses.append("question_type = ?"); params.append(question_type)
        if topic: clauses.append("topic = ?"); params.append(topic)
        if tag: clauses.append("EXISTS (SELECT 1 FROM json_each(sessions.tags) WHERE json_each.value = ?)"); params.append(tag)

        where = " AND ".join(clauses)
        total = self.conn.execute(f"SELECT COUNT(*) FROM sessions WHERE {where}", tuple(params)).fetchone()[0]
        rows = self.conn.execute(f"SELECT * FROM sessions WHERE {where} ORDER BY updated_at DESC LIMIT ? OFFSET ?", tuple(params + [limit, offset])).fetchall()
        sessions = [self._row_to_session(row) for row in rows]
        if return_total:
            return sessions, total
        return sessions

    def get_library_overview(self) -> dict[str, Any]:
        total = self.conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        by_platform = [{"platform": r["platform"], "count": r["count"]} for r in self.conn.execute("SELECT platform, COUNT(*) as count FROM sessions GROUP BY platform")]
        by_qtype = [{"question_type": r["question_type"], "count": r["count"]} for r in self.conn.execute("SELECT question_type, COUNT(*) as count FROM sessions GROUP BY question_type")]
        
        tag_counts = {}
        for r in self.conn.execute("SELECT tags FROM sessions").fetchall():
            for t in json.loads(r["tags"]): tag_counts[t] = tag_counts.get(t, 0) + 1
        top_tags = sorted([{"tag": k, "count": v} for k, v in tag_counts.items()], key=lambda x: x["count"], reverse=True)[:10]
        
        by_topic = []
        for r in self.conn.execute("SELECT topic, COUNT(*) as count FROM sessions WHERE topic IS NOT NULL GROUP BY topic").fetchall():
            topic = r["topic"]
            t_tags = {}
            for tr in self.conn.execute("SELECT tags FROM sessions WHERE topic = ?", (topic,)).fetchall():
                for t in json.loads(tr["tags"]): t_tags[t] = t_tags.get(t, 0) + 1
            by_topic.append({"topic": topic, "count": r["count"], "top_tags": sorted(t_tags.keys(), key=lambda x: t_tags[x], reverse=True)[:3]})

        recent = [self._row_to_session(row) for row in self.conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC LIMIT 5").fetchall()]
        return {"total_sessions": total, "by_topic": by_topic, "by_question_type": by_qtype, "by_platform": by_platform, "top_tags": top_tags, "recent_sessions": recent}

    def get_topics(self) -> list[dict[str, Any]]:
        return self.get_library_overview()["by_topic"]

    def get_tags(self, topic=None) -> list[dict[str, Any]]:
        query = "SELECT tags FROM sessions"
        params = []
        if topic: query += " WHERE topic = ?"; params.append(topic)
        tag_counts = {}
        for r in self.conn.execute(query, tuple(params)).fetchall():
            for t in json.loads(r["tags"]): tag_counts[t] = tag_counts.get(t, 0) + 1
        return sorted([{"tag": k, "count": v} for k, v in tag_counts.items()], key=lambda x: x["count"], reverse=True)

    def close(self) -> None:
        self.conn.close()

    def _get_embedding_dim(self) -> Optional[int]:
        row = self.conn.execute("SELECT value FROM library_meta WHERE key = 'embedding_dim'").fetchone()
        return int(row["value"]) if row else None

    def _ensure_embedding_dim(self, dim: int) -> None:
        curr = self._get_embedding_dim()
        if not curr:
            with self.conn:
                self.conn.execute("INSERT INTO library_meta(key, value) VALUES('embedding_dim', ?)", (str(dim),))
                self.conn.execute("DROP TABLE IF EXISTS session_vectors")
                self.conn.execute(f"CREATE VIRTUAL TABLE session_vectors USING vec0(embedding float[{dim}])")
        elif curr != dim:
            if self.conn.execute("SELECT COUNT(*) FROM session_vectors").fetchone()[0] > 0:
                raise ValueError(f"Dim mismatch: {curr} vs {dim}")
            with self.conn:
                self.conn.execute("UPDATE library_meta SET value = ? WHERE key = 'embedding_dim'", (str(dim),))
                self.conn.execute("DROP TABLE IF EXISTS session_vectors")
                self.conn.execute(f"CREATE VIRTUAL TABLE session_vectors USING vec0(embedding float[{dim}])")

    def _create_vector_table_if_missing(self, dim: int) -> None:
        if not self.conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='session_vectors'").fetchone():
            self.conn.execute(f"CREATE VIRTUAL TABLE session_vectors USING vec0(embedding float[{dim}])")

    def _get_existing_embedding_id(self, session_id: str) -> Optional[int]:
        row = self.conn.execute("SELECT embedding_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return row["embedding_id"] if row else None

    def _serialize_embedding(self, embedding: list[float]) -> bytes:
        return serialize_float32([float(v) for v in embedding])

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        return Session(
            id=row["id"], source_id=row["source_id"], platform=row["platform"], title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]), updated_at=datetime.fromisoformat(row["updated_at"]),
            messages=[Message.model_validate(m) for m in json.loads(row["messages"])],
            topic=row["topic"], tags=json.loads(row["tags"]),
            key_entities=json.loads(row["key_entities"]) if "key_entities" in row.keys() else [],
            question_type=row["question_type"], summary=row["summary"], embedding_id=row["embedding_id"]
        )

class Database(LibraryDB): pass
