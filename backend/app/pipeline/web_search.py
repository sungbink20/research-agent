"""
Web search module for grounding investment memos with live data.

Uses Tavily API to fetch current web results before the Claude call.
This is intentionally a standalone module -- easy to swap Tavily for
another search provider (Serper, SerpAPI, Brave, etc.) without touching
the rest of the pipeline.

Design decisions:
- Multiple targeted queries per company rather than one broad search.
  Investment research needs different angles: overview, competitors, news.
- Graceful degradation: if TAVILY_API_KEY is unset or the API fails,
  we return an empty list and let Claude work from training data alone.
- Results are returned as simple dataclasses, not Pydantic models,
  to keep this module decoupled from the API schema layer.
"""

import logging
from dataclasses import dataclass

from app.config import TAVILY_API_KEY

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single web search result. Intentionally simple."""
    title: str
    url: str
    snippet: str
    score: float  # Tavily relevance score, 0-1


async def search_company(query: str) -> list[SearchResult]:
    """
    Run multiple targeted searches for a company/protocol and return
    deduplicated results sorted by relevance.

    Args:
        query: Company or protocol name (e.g. "Uniswap", "Stripe")

    Returns:
        List of SearchResult, empty if search is unavailable or fails.
    """
    if not TAVILY_API_KEY:
        logger.warning(
            "TAVILY_API_KEY not set -- skipping web search. "
            "Memo will be based on Claude's training data only. "
            "Set TAVILY_API_KEY in backend/.env for live web grounding."
        )
        return []

    # Import here so the module loads even if tavily-python isn't installed.
    # This supports the graceful degradation pattern.
    try:
        from tavily import AsyncTavilyClient
    except ImportError:
        logger.error(
            "tavily-python is not installed. Run: pip install tavily-python"
        )
        return []

    client = AsyncTavilyClient(api_key=TAVILY_API_KEY)

    # Three focused queries to cover different research angles.
    # Tavily's search depth "basic" is fast and cheap; "advanced" costs 2x.
    search_queries = [
        f"{query} company overview funding valuation",
        f"{query} competitors market landscape",
        f"{query} latest news 2025 2026",
    ]

    all_results: list[SearchResult] = []
    seen_urls: set[str] = set()

    for sq in search_queries:
        try:
            response = await client.search(
                query=sq,
                search_depth="basic",
                max_results=5,
            )

            for result in response.get("results", []):
                url = result.get("url", "")
                # Deduplicate by URL across the three queries
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(SearchResult(
                        title=result.get("title", "Untitled"),
                        url=url,
                        snippet=result.get("content", "")[:500],  # cap snippet length
                        score=result.get("score", 0.0),
                    ))
        except Exception as e:
            # Don't let one failed query kill the whole search step.
            # Log and continue with whatever results we already have.
            logger.warning(f"Tavily search failed for query {sq!r}: {e}")
            continue

    # Sort by relevance score descending, take top 10 to keep prompt size reasonable
    all_results.sort(key=lambda r: r.score, reverse=True)
    all_results = all_results[:10]

    logger.info(
        f"Web search for {query!r}: {len(all_results)} results "
        f"from {len(search_queries)} queries"
    )

    return all_results


def format_search_results_for_prompt(results: list[SearchResult]) -> str:
    """
    Format search results as a text block to inject into the Claude prompt.

    Each result includes title, URL, and a truncated snippet.
    This is plain text, not JSON -- Claude reads it as grounding context.
    """
    if not results:
        return ""

    lines = ["## Web Search Results (live data -- use these to ground your analysis)\n"]

    for i, r in enumerate(results, 1):
        # Truncate snippet to ~300 chars for prompt efficiency
        snippet = r.snippet[:300].strip()
        if len(r.snippet) > 300:
            snippet += "..."
        lines.append(f"### [{i}] {r.title}")
        lines.append(f"URL: {r.url}")
        lines.append(f"Snippet: {snippet}")
        lines.append("")  # blank line between results

    return "\n".join(lines)
