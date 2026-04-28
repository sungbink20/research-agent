"""
Twitter/X social signals module for grounding investment memos with
real-time crypto Twitter sentiment.

Adapted from the standalone twitter_analyzer project. This module:
1. Searches Twitter for tweets mentioning the company/protocol
2. Sends tweets to Claude for structured extraction (narratives, sentiment, tokens)
3. Formats the analysis for injection into the research prompt

Graceful degradation: if X_BEARER_TOKEN or ANTHROPIC_API_KEY are not set,
or if the Twitter API / Claude call fails, returns None and the pipeline
continues without social signals.

Rate limits: the Twitter free tier allows 1500 tweets/month read.
Each memo generation searches for ~15 tweets to stay conservative.
"""

import json
import logging
from typing import Optional

from app.config import ANTHROPIC_API_KEY, X_BEARER_TOKEN

logger = logging.getLogger(__name__)

TWEET_BUDGET_PER_MEMO = 15

# Extraction prompt adapted from twitter_analyzer/analyzer/prompts.py
EXTRACTION_PROMPT = """\
You are a crypto-market intelligence analyst. Given the following batch of tweets \
related to "{query}", extract structured insights.

TWEETS:
{tweets_text}

Return ONLY valid JSON with this exact schema (no preamble, no markdown fences):
{{
  "trending_narratives": [
    {{"theme": "string", "evidence": "string"}}
  ],
  "tokens_mentioned": [
    {{"symbol": "string", "mention_count": 0, "sentiment": "bullish|bearish|neutral"}}
  ],
  "top_quotes": [
    {{"text": "string", "author": "string", "why_notable": "string"}}
  ],
  "overall_sentiment": {{
    "direction": "bullish|bearish|neutral",
    "reasoning": "string"
  }}
}}

Rules:
- Focus on insights relevant to {query} as an investment opportunity.
- Merge duplicate tokens and sum their counts.
- Symbols must include the $ prefix (e.g. $ETH).
- Pick at most 3 top quotes that are most insightful.
- Be precise; do not hallucinate mentions that aren't in the tweets.
"""


def _search_tweets(query: str) -> list[dict]:
    """
    Search Twitter for tweets about the query.
    Returns a list of tweet dicts. Inline implementation to avoid
    cross-project imports and PostgreSQL dependency.
    """
    try:
        from twitter_api_v2 import TwitterAPI
    except ImportError:
        logger.warning(
            "python-twitter-v2 is not installed -- Twitter signals disabled. "
            "Run: pip install python-twitter-v2"
        )
        return []

    api = TwitterAPI(bearer_token=X_BEARER_TOKEN)

    # Two targeted searches to cover the company from different angles
    search_queries = [
        f"{query} crypto",
        f"${query}",  # token ticker search
    ]

    all_tweets: list[dict] = []
    seen_ids: set[str] = set()
    budget = TWEET_BUDGET_PER_MEMO

    for sq in search_queries:
        if budget <= 0:
            break
        try:
            resp = api.search_recent_tweets(
                query=sq,
                max_results=max(10, min(budget, 10)),  # API minimum is 10
                tweet_fields=["created_at", "author_id", "text"],
                expansions=["author_id"],
                user_fields=["username", "name"],
            )
        except Exception as e:
            logger.warning(f"Twitter search failed for {sq!r}: {e}")
            continue

        # Build author lookup
        users = {}
        for u in (resp.get("includes", {}).get("users") or []):
            users[u["id"]] = u.get("username", "unknown")

        for t in (resp.get("data") or []):
            if budget <= 0:
                break
            tid = t["id"]
            if tid in seen_ids:
                continue
            seen_ids.add(tid)
            author = users.get(t.get("author_id"), "unknown")
            all_tweets.append({
                "tweet_id": tid,
                "text": t["text"],
                "author": author,
                "author_handle": author,
                "created_at": t.get("created_at"),
            })
            budget -= 1

    logger.info(f"Twitter search for {query!r}: collected {len(all_tweets)} tweets")
    return all_tweets


def _analyze_tweets(query: str, tweets: list[dict]) -> Optional[dict]:
    """
    Send tweets to Claude for structured extraction.
    Uses the Anthropic SDK directly (same pattern as twitter_analyzer).
    """
    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed -- skipping tweet analysis")
        return None

    tweets_text = "\n\n".join(
        f"@{t['author_handle']} ({t.get('created_at', 'unknown date')}):\n{t['text']}"
        for t in tweets
    )

    prompt = EXTRACTION_PROMPT.format(query=query, tweets_text=tweets_text)

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]

        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Tweet analysis failed: {e}")
        return None


async def fetch_twitter_signals(query: str) -> Optional[dict]:
    """
    Main entry point: search Twitter + analyze with Claude.
    Returns structured analysis dict or None if unavailable.

    This is async for interface consistency with the rest of the pipeline,
    but the Twitter API client is synchronous under the hood.
    """
    if not X_BEARER_TOKEN:
        logger.info("X_BEARER_TOKEN not set -- skipping Twitter signals")
        return None

    if not ANTHROPIC_API_KEY:
        logger.info("ANTHROPIC_API_KEY not set -- skipping Twitter signal analysis")
        return None

    tweets = _search_tweets(query)
    if not tweets:
        logger.info(f"No tweets found for {query!r}")
        return None

    analysis = _analyze_tweets(query, tweets)
    if analysis:
        logger.info(
            f"Twitter analysis for {query!r}: "
            f"sentiment={analysis.get('overall_sentiment', {}).get('direction', 'unknown')}, "
            f"{len(analysis.get('trending_narratives', []))} narratives, "
            f"{len(analysis.get('tokens_mentioned', []))} tokens"
        )
    return analysis


def format_twitter_context_for_prompt(signals: Optional[dict]) -> str:
    """
    Format Twitter analysis as a text block for prompt injection.
    Same pattern as format_search_results_for_prompt in web_search.py.
    """
    if not signals:
        return ""

    lines = [
        "## Social Signals (from Crypto Twitter)\n",
        "The following is a structured analysis of recent tweets. "
        "Incorporate relevant sentiment and narratives, but note that "
        "Twitter signals reflect short-term sentiment and may not indicate "
        "long-term fundamentals.\n",
    ]

    # Overall sentiment
    sentiment = signals.get("overall_sentiment", {})
    if sentiment:
        lines.append(f"**Overall Sentiment:** {sentiment.get('direction', 'unknown')}")
        lines.append(f"Reasoning: {sentiment.get('reasoning', 'N/A')}")
        lines.append("")

    # Trending narratives
    narratives = signals.get("trending_narratives", [])
    if narratives:
        lines.append("**Trending Narratives:**")
        for n in narratives:
            lines.append(f"- {n.get('theme', 'Unknown')}: {n.get('evidence', '')}")
        lines.append("")

    # Token mentions
    tokens = signals.get("tokens_mentioned", [])
    if tokens:
        lines.append("**Token Mentions:**")
        for t in tokens:
            lines.append(
                f"- {t.get('symbol', '?')} -- "
                f"{t.get('mention_count', 0)} mentions, "
                f"sentiment: {t.get('sentiment', 'unknown')}"
            )
        lines.append("")

    # Top quotes
    quotes = signals.get("top_quotes", [])
    if quotes:
        lines.append("**Notable Quotes:**")
        for q in quotes:
            lines.append(f'> "{q.get("text", "")}" -- @{q.get("author", "unknown")}')
            if q.get("why_notable"):
                lines.append(f"  ({q['why_notable']})")
        lines.append("")

    return "\n".join(lines)
