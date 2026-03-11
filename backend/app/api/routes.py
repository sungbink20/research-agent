"""
API routes for the investment research agent.

Endpoints:
  POST /api/memos         -- Generate a new memo
  GET  /api/memos         -- List recent memos
  GET  /api/memos/{id}    -- Get a specific memo
  POST /api/memos/{id}/feedback -- Submit feedback on a memo
  GET  /api/health        -- Health check
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas import (
    FeedbackRequest,
    MemoListItem,
    MemoRecord,
    MemoRequest,
    MemoResponse,
)
from app.services.memo_service import (
    create_memo,
    get_memo_by_id,
    get_recent_memos,
    submit_feedback,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.post("/memos", response_model=MemoResponse, status_code=201)
async def generate_memo(request: MemoRequest):
    """
    Generate a new investment memo for the given query.

    This calls the Claude API and may take 10-30 seconds depending
    on the complexity of the query. The frontend should show a loading
    state during this time.
    """
    try:
        result = await create_memo(query=request.query, context=request.context)
        return result
    except ValueError as e:
        # Config errors or parsing failures
        logger.error(f"Memo generation failed: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # API errors, network issues, etc.
        logger.error(f"Unexpected error generating memo: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate memo: {type(e).__name__}: {str(e)}",
        )


@router.get("/memos", response_model=list[MemoListItem])
async def list_memos(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List recent memos, most recent first."""
    return get_recent_memos(limit=limit, offset=offset)


@router.get("/memos/{memo_id}", response_model=MemoRecord)
async def get_memo(memo_id: str):
    """Get a specific memo by ID."""
    record = get_memo_by_id(memo_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Memo not found")
    return record


@router.post("/memos/{memo_id}/feedback", response_model=MemoRecord)
async def add_feedback(memo_id: str, feedback: FeedbackRequest):
    """Submit feedback (rating and/or comments) on a memo."""
    if feedback.rating is None and feedback.feedback is None:
        raise HTTPException(
            status_code=400,
            detail="At least one of 'rating' or 'feedback' must be provided",
        )
    record = submit_feedback(memo_id, feedback)
    if record is None:
        raise HTTPException(status_code=404, detail="Memo not found")
    return record


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "service": "research-agent"}
