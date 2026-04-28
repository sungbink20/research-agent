"""
Research pipeline powered by OpenAI, grounded with live web search,
past memo retrieval (RAG), and Twitter social signals.

Design decisions:
- Single API call per memo. The memo fields are interconnected (bull/bear
  cases depend on understanding the product), so splitting into separate
  calls would produce less coherent output and cost more.
- We ask Claude to return structured JSON matching our InvestmentMemo schema.
  This is more reliable than parsing freeform text.
- Three context sources are gathered BEFORE the Claude call:
  1. Web search (Tavily) -- live grounding data
  2. RAG (ChromaDB) -- relevant past memos from the archive
  3. Twitter signals -- real-time crypto social sentiment
  Web search and Twitter fetch run concurrently via asyncio.gather.
- Sources from web search are tagged "web", from Claude "llm_knowledge",
  and from Twitter "social". The frontend can distinguish source types.
- Graceful degradation: each context source fails independently. The memo
  will be thinner but won't crash.
"""

import asyncio
import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.pipeline.web_search import (
    SearchResult,
    format_search_results_for_prompt,
    search_company,
)
from app.pipeline.vector_store import (
    format_rag_context_for_prompt,
    retrieve_relevant_memos,
)
from app.pipeline.twitter_signals import (
    fetch_twitter_signals,
    format_twitter_context_for_prompt,
)
from app.schemas import InvestmentMemo, Source

logger = logging.getLogger(__name__)

# The system prompt establishes Claude's role and output expectations.
# Key principles:
# - Be honest about uncertainty (don't hallucinate traction)
# - Distinguish between facts and inferences
# - Surface what it doesn't know via open_questions
# - Prioritize web search results as grounding data when available
SYSTEM_PROMPT = """You are an investment research analyst assistant. Your job is to produce a structured first-pass investment memo for a given company or protocol.

Rules:
1. Be factual. If you are not confident about something, say so explicitly. Never fabricate metrics, funding amounts, or partnerships.
2. Clearly distinguish between established facts and your analytical inferences.
3. For traction_signals, only include things you have reasonable confidence are true. Qualify uncertainty with phrases like "reportedly" or "as of [date]".
4. For competitors, include both direct competitors and adjacent players. Briefly explain how each competes.
5. Bull and bear cases should be specific to THIS company, not generic industry platitudes.
6. Open questions should be genuinely useful -- things an analyst would actually want to investigate.
7. For sources: if web search results are provided, use them as your primary grounding and cite them with source_type "web". You may also include additional sources from your training knowledge with source_type "llm_knowledge". If Twitter social signals are provided, cite relevant ones with source_type "social". Always prefer web search data over your training data when they conflict, as web data is more current.
8. If you know very little about the company, be upfront about it in the summary and load up open_questions with what needs to be researched.
9. If past research memos are provided, use them to inform your analysis. Note any changes, updates, or evolving trends compared to previous research on the same or related companies.
10. If social media signals are provided, incorporate relevant sentiment and trending narratives into your analysis. Note that Twitter signals reflect short-term sentiment and may not indicate long-term fundamentals. Flag when social sentiment diverges from fundamentals.

Output format: Return ONLY valid JSON matching the schema below. No markdown, no commentary, no code fences. Just the JSON object.

Schema:
{
  "company_name": "string",
  "website": "string or null",
  "category": "string (e.g., DeFi, Fintech, SaaS, Infrastructure, L1/L2, etc.)",
  "summary": "string (2-4 sentences)",
  "product": "string",
  "customer": "string",
  "business_model": "string",
  "traction_signals": ["string", ...],
  "competitors": ["string (name + brief context)", ...],
  "bull_case": ["string", ...],
  "bear_case": ["string", ...],
  "risks": ["string", ...],
  "open_questions": ["string", ...],
  "sources": [{"title": "string", "url": "string or null", "snippet": "string or null", "source_type": "web | llm_knowledge | social"}, ...]
}"""


def build_user_prompt(
    query: str,
    context: Optional[str] = None,
    search_context: str = "",
    rag_context: str = "",
    twitter_context: str = "",
) -> str:
    """
    Construct the user message for the Claude API call.

    Context blocks are injected before the research request so Claude
    sees all grounding data first. Order: web search, past memos, Twitter.
    """
    parts = []

    # --- Inject web search results as grounding context ---
    if search_context:
        parts.append(search_context)
        parts.append("")

    # --- Inject relevant past memos (RAG) ---
    if rag_context:
        parts.append(rag_context)
        parts.append("")

    # --- Inject Twitter social signals ---
    if twitter_context:
        parts.append(twitter_context)
        parts.append("")

    parts.append(f"Research the following and produce an investment memo:\n\n{query}")

    if context:
        parts.append(f"\nAdditional context from the analyst:\n{context}")

    return "\n".join(parts)


def _build_web_sources(search_results: list[SearchResult]) -> list[Source]:
    """
    Convert web search results into Source objects for the memo.

    These get merged with any sources Claude generates, giving the memo
    a mix of verified web sources and LLM-knowledge sources.
    """
    sources = []
    for r in search_results:
        sources.append(Source(
            title=r.title,
            url=r.url,
            snippet=r.snippet[:300] if r.snippet else None,
            source_type="web",
        ))
    return sources


async def generate_memo(query: str, context: Optional[str] = None) -> InvestmentMemo:
    """
    Call Claude to generate a structured investment memo, optionally
    grounded with live web search results.

    Pipeline:
    1. Run web search for the query (if Tavily key is configured)
    2. Format search results and inject into the Claude prompt
    3. Call Claude with the enriched prompt
    4. Parse and validate the response
    5. Merge web sources into the memo's sources list

    Raises:
        openai.APIError: If the OpenAI API call fails
        ValueError: If the response can't be parsed into our schema
    """
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY is not configured. "
            "Set it in backend/.env or as an environment variable."
        )

    # --- Step 1: Gather context from all sources concurrently ---
    # Web search and Twitter signals are I/O bound and independent,
    # so we run them in parallel. RAG retrieval is local and fast.

    # 1a. RAG -- retrieve relevant past memos (local, fast)
    try:
        rag_results = retrieve_relevant_memos(query)
        rag_context = format_rag_context_for_prompt(rag_results)
        if rag_results:
            logger.info(f"RAG returned {len(rag_results)} relevant past memos for {query!r}")
    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")
        rag_results = []
        rag_context = ""

    # 1b. Web search + Twitter signals in parallel (network I/O)
    search_results_coro = search_company(query)
    twitter_signals_coro = fetch_twitter_signals(query)

    search_results, twitter_signals = await asyncio.gather(
        search_results_coro,
        twitter_signals_coro,
        return_exceptions=True,
    )

    # Handle exceptions from gather
    if isinstance(search_results, Exception):
        logger.warning(f"Web search failed: {search_results}")
        search_results = []
    if isinstance(twitter_signals, Exception):
        logger.warning(f"Twitter signals failed: {twitter_signals}")
        twitter_signals = None

    search_context = format_search_results_for_prompt(search_results)
    twitter_context = format_twitter_context_for_prompt(twitter_signals)

    if search_results:
        logger.info(f"Web search returned {len(search_results)} results for {query!r}")
    if twitter_signals:
        logger.info(f"Twitter signals available for {query!r}")

    # --- Step 2: Call OpenAI with enriched prompt ---
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    logger.info(f"Generating memo for query: {query!r} (model: {OPENAI_MODEL})")

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            max_completion_tokens=4096,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(
                    query, context, search_context, rag_context, twitter_context,
                )},
            ],
        )
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        raise

    # --- Step 3: Parse the JSON response ---
    raw_text = response.choices[0].message.content.strip()

    try:
        # Strip markdown code fences if Claude includes them despite instructions
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]  # remove first line
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

        memo_data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        logger.error(f"Raw response (first 500 chars): {raw_text[:500]}")
        raise ValueError(
            f"Claude returned invalid JSON. This usually means the response "
            f"was truncated or contained unexpected formatting. Error: {e}"
        )

    # Validate against our Pydantic schema
    try:
        memo = InvestmentMemo.model_validate(memo_data)
    except Exception as e:
        logger.error(f"Claude response failed schema validation: {e}")
        logger.error(f"Parsed data keys: {list(memo_data.keys())}")
        raise ValueError(
            f"Claude's response didn't match the expected memo schema: {e}"
        )

    # --- Step 4: Merge sources ---
    # Tag any Claude-generated sources that lack a type as llm_knowledge
    valid_types = ("web", "llm_knowledge", "social")
    for source in memo.sources:
        if not source.source_type or source.source_type not in valid_types:
            source.source_type = "llm_knowledge"

    # Ensure web search sources are included in the memo even if Claude
    # didn't explicitly cite them. We add them at the front since they're
    # verified real URLs (deduplicated against what Claude already cited).
    if search_results:
        existing_urls = {s.url for s in memo.sources if s.url}
        web_sources = _build_web_sources(search_results)
        new_web_sources = [s for s in web_sources if s.url not in existing_urls]
        # Prepend web sources so they appear first in the sources list
        memo.sources = new_web_sources + memo.sources

    logger.info(
        f"Memo generated: {memo.company_name} ({memo.category}), "
        f"{len(memo.sources)} sources "
        f"({sum(1 for s in memo.sources if s.source_type == 'web')} web, "
        f"{sum(1 for s in memo.sources if s.source_type == 'llm_knowledge')} llm, "
        f"{sum(1 for s in memo.sources if s.source_type == 'social')} social), "
        f"{len(memo.open_questions)} open questions"
    )

    return memo
