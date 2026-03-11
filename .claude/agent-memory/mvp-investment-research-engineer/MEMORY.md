# Research Agent - Agent Memory

## Project Overview
Internal investment research tool: user enters a company/protocol name, gets a structured first-pass investment memo with sources, bull/bear framing, and open questions.

## Architecture
- **Monorepo**: `backend/` (FastAPI + Python) and `frontend/` (Next.js + TypeScript)
- **Database**: SQLite with raw SQL (no ORM). Memo stored as JSON blob in TEXT column.
- **AI**: Web search (Tavily) -> single Claude API call per memo (claude-sonnet-4-6). Search results injected as grounding context.
- **Frontend**: Next.js App Router, Tailwind, single-page app (no routing needed for MVP)

## Key Files
- `backend/app/schemas.py` - Pydantic models, single source of truth for data shapes
- `backend/app/pipeline/researcher.py` - Claude prompt + response parsing (with web search injection)
- `backend/app/pipeline/web_search.py` - Tavily web search module (standalone, swappable)
- `backend/app/db/database.py` - SQLite persistence
- `frontend/src/lib/types.ts` - TypeScript types mirroring backend schemas (manual sync)
- `frontend/src/lib/api.ts` - API client, all backend calls go through here

## Known Technical Debt
1. ~~Sources are from Claude training data, not live web.~~ DONE: Tavily web search added. Sources now have "web" and "llm_knowledge" types.
2. Frontend types manually synced with backend schemas (could generate from OpenAPI)
3. No auth, no caching, no async job queue
4. SQLite module-level connection (fine for local single-user, not for deployment)

## Decisions Made
- **Single Claude call** over multiple calls: fields are interconnected, fewer calls = faster + cheaper
- **No ORM**: one table, raw SQL is simpler and has zero config
- **No state management library**: React state + fetch sufficient for MVP
- **Dark UI theme**: matches investment tooling aesthetic, reduces eye strain for long sessions
- **Tavily for web search**: async client, 3 targeted queries per company (overview, competitors, news), graceful degradation if no API key
- **Source types**: "web" (from Tavily, real URLs) and "llm_knowledge" (from Claude training data). Web sources prepended to list.
