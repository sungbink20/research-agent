"""
Pydantic schemas for the investment research agent.

These are the single source of truth for data shapes across the API.
The memo schema mirrors what Claude returns and what the frontend renders.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Request schemas ---

class MemoRequest(BaseModel):
    """What the user submits to kick off research."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Company name, protocol name, or URL to research",
        examples=["Stripe", "Uniswap", "https://example.com"],
    )
    context: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional additional context: sector focus, specific questions, etc.",
    )


# --- Source schema ---

class Source(BaseModel):
    """A single source reference used in the memo."""
    title: str
    url: Optional[str] = None
    snippet: Optional[str] = Field(
        default=None,
        description="Relevant excerpt from this source",
    )
    source_type: str = Field(
        default="web",
        description="Type of source: web, filing, transcript, docs, etc.",
    )


# --- Core memo schema ---

class InvestmentMemo(BaseModel):
    """
    The structured output of the research pipeline.

    Every field is a string or list of strings -- intentionally simple.
    Analysts want to scan this quickly, not parse nested objects.
    """
    company_name: str
    website: Optional[str] = None
    category: str = Field(
        description="Sector or category: e.g. 'DeFi', 'Fintech', 'SaaS', 'Infrastructure'",
    )
    summary: str = Field(
        description="2-4 sentence executive summary of what this company does and why it matters",
    )
    product: str = Field(
        description="What the product/protocol actually does, in plain language",
    )
    customer: str = Field(
        description="Who uses this and why -- target users, segments, use cases",
    )
    business_model: str = Field(
        description="How it makes money (or plans to). Be specific about revenue streams.",
    )
    traction_signals: list[str] = Field(
        default_factory=list,
        description="Observable evidence of traction: metrics, partnerships, adoption, funding",
    )
    competitors: list[str] = Field(
        default_factory=list,
        description="Direct and indirect competitors, with brief context on each",
    )
    bull_case: list[str] = Field(
        default_factory=list,
        description="Reasons this could be a great investment. Be specific, not generic.",
    )
    bear_case: list[str] = Field(
        default_factory=list,
        description="Reasons this could fail or disappoint. Be honest.",
    )
    risks: list[str] = Field(
        default_factory=list,
        description="Key risks: regulatory, technical, market, execution, etc.",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Questions an analyst should investigate further before making a decision",
    )
    sources: list[Source] = Field(
        default_factory=list,
        description="Sources used to compile this memo",
    )


# --- Persisted memo (includes DB metadata) ---

class MemoRecord(BaseModel):
    """A memo as stored in the database, with metadata."""
    id: str
    query: str
    context: Optional[str] = None
    memo: InvestmentMemo
    feedback: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    created_at: datetime
    updated_at: datetime


# --- Feedback schema ---

class FeedbackRequest(BaseModel):
    """User feedback on a generated memo."""
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    feedback: Optional[str] = Field(default=None, max_length=5000)


# --- API response wrappers ---

class MemoResponse(BaseModel):
    """Response from the memo generation endpoint."""
    id: str
    memo: InvestmentMemo
    generated_at: datetime


class MemoListItem(BaseModel):
    """Summary item for the memo list endpoint."""
    id: str
    query: str
    company_name: str
    category: str
    created_at: datetime
