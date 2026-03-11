"""
Research pipeline powered by OpenAI, grounded with live web search.

Design decisions:
- Single API call per memo. The memo fields are interconnected (bull/bear
  cases depend on understanding the product), so splitting into separate
  calls would produce less coherent output and cost more.
- We ask Claude to return structured JSON matching our InvestmentMemo schema.
  This is more reliable than parsing freeform text.
- Web search runs BEFORE the Claude call to inject live grounding data.
  This addresses the #1 known limitation from MVP: Claude's training data
  cutoff. Search results are formatted as plain text in the prompt so
  Claude can synthesize them into the memo fields.
- Sources from web search are tagged "web" and carry real URLs. Sources
  from Claude's training data are tagged "llm_knowledge". The frontend
  can distinguish between verified and unverified sources.
- Graceful degradation: if web search is unavailable (no API key, network
  error), the pipeline falls back to Claude-only mode. The memo will be
  thinner but won't crash.
"""

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
7. For sources: if web search results are provided, use them as your primary grounding and cite them with source_type "web". You may also include additional sources from your training knowledge with source_type "llm_knowledge". Always prefer web search data over your training data when they conflict, as web data is more current.
8. If you know very little about the company, be upfront about it in the summary and load up open_questions with what needs to be researched.

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
  "sources": [{"title": "string", "url": "string or null", "snippet": "string or null", "source_type": "web | llm_knowledge"}, ...]
}"""


def build_user_prompt(
    query: str,
    context: Optional[str] = None,
    search_context: str = "",
) -> str:
    """
    Construct the user message for the Claude API call.

    If search_context is provided, it's injected before the research request
    so Claude sees the grounding data first.
    """
    parts = []

    # --- Inject web search results as grounding context ---
    # This block is only present when Tavily returned results.
    # Claude is instructed (in the system prompt) to prioritize this data.
    if search_context:
        parts.append(search_context)
        parts.append("")  # blank line separator

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

    # --- Step 1: Web search for grounding context ---
    # This runs before the Claude call. If it fails or returns nothing,
    # we proceed with Claude-only mode (graceful degradation).
    search_results = await search_company(query)
    search_context = format_search_results_for_prompt(search_results)

    if search_results:
        logger.info(
            f"Web search returned {len(search_results)} results for {query!r}. "
            f"Injecting into prompt."
        )
    else:
        logger.info(
            f"No web search results for {query!r}. "
            f"Proceeding with Claude training data only."
        )

    # --- Step 2: Call OpenAI with enriched prompt ---
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    logger.info(f"Generating memo for query: {query!r} (model: {OPENAI_MODEL})")

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            max_completion_tokens=4096,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(query, context, search_context)},
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
    for source in memo.sources:
        if not source.source_type or source.source_type not in ("web", "llm_knowledge"):
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
        f"{sum(1 for s in memo.sources if s.source_type == 'llm_knowledge')} llm), "
        f"{len(memo.open_questions)} open questions"
    )

    return memo
