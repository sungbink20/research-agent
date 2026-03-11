"""
SQLite persistence layer for investment memos.

Design decisions:
- Store the full memo as a JSON blob in a TEXT column. This keeps the schema
  simple and lets us evolve the memo format without migrations.
- Use a separate columns for query, feedback, and timestamps so we can
  filter/sort without parsing JSON.
- No ORM -- raw SQL is fine for one table and keeps dependencies minimal.

Technical debt: If we need full-text search over memo contents, we should
add an FTS5 virtual table. Not worth it for MVP.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.config import DATABASE_PATH
from app.schemas import (
    FeedbackRequest,
    InvestmentMemo,
    MemoListItem,
    MemoRecord,
)

# Module-level connection. SQLite is single-writer anyway, and for a local
# tool used by one team, connection pooling is unnecessary overhead.
_connection: Optional[sqlite3.Connection] = None


def _get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL")  # better concurrent read perf
        _connection.execute("PRAGMA foreign_keys=ON")
    return _connection


def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memos (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            context TEXT,
            memo_json TEXT NOT NULL,
            feedback TEXT,
            rating INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()


def save_memo(
    query: str,
    context: Optional[str],
    memo: InvestmentMemo,
) -> MemoRecord:
    """Persist a newly generated memo. Returns the full record with metadata."""
    conn = _get_connection()
    memo_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    conn.execute(
        """
        INSERT INTO memos (id, query, context, memo_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (memo_id, query, context, memo.model_dump_json(), now_iso, now_iso),
    )
    conn.commit()

    return MemoRecord(
        id=memo_id,
        query=query,
        context=context,
        memo=memo,
        created_at=now,
        updated_at=now,
    )


def get_memo(memo_id: str) -> Optional[MemoRecord]:
    """Fetch a single memo by ID."""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM memos WHERE id = ?", (memo_id,)).fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def list_memos(limit: int = 50, offset: int = 0) -> list[MemoListItem]:
    """List memos, most recent first. Returns summary items, not full memos."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT id, query, memo_json, created_at FROM memos ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()

    items = []
    for row in rows:
        memo_data = json.loads(row["memo_json"])
        items.append(
            MemoListItem(
                id=row["id"],
                query=row["query"],
                company_name=memo_data.get("company_name", "Unknown"),
                category=memo_data.get("category", "Unknown"),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
        )
    return items


def update_feedback(memo_id: str, feedback: FeedbackRequest) -> Optional[MemoRecord]:
    """Update feedback/rating on an existing memo."""
    conn = _get_connection()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Build SET clause dynamically based on what's provided
    updates = ["updated_at = ?"]
    params: list = [now_iso]

    if feedback.rating is not None:
        updates.append("rating = ?")
        params.append(feedback.rating)
    if feedback.feedback is not None:
        updates.append("feedback = ?")
        params.append(feedback.feedback)

    params.append(memo_id)
    set_clause = ", ".join(updates)

    cursor = conn.execute(
        f"UPDATE memos SET {set_clause} WHERE id = ?",
        params,
    )
    conn.commit()

    if cursor.rowcount == 0:
        return None
    return get_memo(memo_id)


def _row_to_record(row: sqlite3.Row) -> MemoRecord:
    """Convert a database row to a MemoRecord."""
    memo = InvestmentMemo.model_validate_json(row["memo_json"])
    return MemoRecord(
        id=row["id"],
        query=row["query"],
        context=row["context"],
        memo=memo,
        feedback=row["feedback"],
        rating=row["rating"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
