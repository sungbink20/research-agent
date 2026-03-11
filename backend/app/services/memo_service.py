"""
Memo service -- orchestrates research pipeline and persistence.

This is intentionally thin for MVP. It coordinates:
1. Calling the research pipeline to generate a memo
2. Saving the result to the database
3. Retrieving stored memos

Future additions would go here:
- Caching (don't re-research the same company within N hours)
- Pipeline composition (web search -> Claude -> validation)
- Async job queue for long-running research
- Memo versioning (re-run research, compare old vs new)
"""

import logging
from typing import Optional

from app.db.database import get_memo, list_memos, save_memo, update_feedback
from app.pipeline.researcher import generate_memo
from app.schemas import (
    FeedbackRequest,
    MemoListItem,
    MemoRecord,
    MemoResponse,
)

logger = logging.getLogger(__name__)


async def create_memo(query: str, context: Optional[str] = None) -> MemoResponse:
    """
    Generate a new investment memo and persist it.

    This is the main entry point for memo creation. It:
    1. Calls Claude to generate the memo content
    2. Saves the memo to SQLite
    3. Returns the response with the memo ID

    Raises on API errors or parsing failures -- the route handler
    is responsible for translating those into HTTP error responses.
    """
    logger.info(f"Creating memo for: {query!r}")

    # Step 1: Generate memo via Claude
    memo = await generate_memo(query, context)

    # Step 2: Persist
    record = save_memo(query=query, context=context, memo=memo)

    logger.info(f"Memo saved: id={record.id}, company={memo.company_name}")

    return MemoResponse(
        id=record.id,
        memo=record.memo,
        generated_at=record.created_at,
    )


def get_memo_by_id(memo_id: str) -> Optional[MemoRecord]:
    """Retrieve a single memo by ID."""
    return get_memo(memo_id)


def get_recent_memos(limit: int = 50, offset: int = 0) -> list[MemoListItem]:
    """List recent memos, most recent first."""
    return list_memos(limit=limit, offset=offset)


def submit_feedback(
    memo_id: str, feedback: FeedbackRequest
) -> Optional[MemoRecord]:
    """Attach user feedback to a memo."""
    return update_feedback(memo_id, feedback)
