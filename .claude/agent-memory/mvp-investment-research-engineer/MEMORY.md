# Research Agent - Agent Memory

## Project Overview
Internal investment research tool: user enters a company/protocol name, gets a structured first-pass investment memo grounded with live web search, past research (RAG), and Crypto Twitter social signals.

## Architecture
- **Monorepo**: `backend/` (FastAPI + Python) and `frontend/` (Next.js + TypeScript)
- **Database**: SQLite with raw SQL (no ORM). Memo stored as JSON blob in TEXT column.
- **Vector Store**: ChromaDB (embedded mode) at `./data/chroma` for RAG. Memos indexed on creation.
- **AI Pipeline**: Three context sources gathered before a single Claude API call:
  1. Web search (Tavily) -- live grounding data
  2. RAG (ChromaDB) -- semantically similar past memos
  3. Twitter signals (X API v2 + Anthropic SDK) -- real-time crypto social sentiment
- Web search and Twitter fetch run concurrently via `asyncio.gather`. RAG retrieval is local/fast.
- **Frontend**: Next.js App Router, Tailwind, single-page app (no routing needed for MVP)

## Key Files
- `backend/app/schemas.py` - Pydantic models, single source of truth for data shapes
- `backend/app/pipeline/researcher.py` - Claude prompt + response parsing (orchestrates all 3 context sources)
- `backend/app/pipeline/web_search.py` - Tavily web search module (standalone, swappable)
- `backend/app/pipeline/vector_store.py` - ChromaDB RAG module (init, index, retrieve, format)
- `backend/app/pipeline/twitter_signals.py` - Twitter collection + Claude analysis (adapted from twitter_analyzer project)
- `backend/app/db/database.py` - SQLite persistence
- `backend/app/services/memo_service.py` - Orchestration: generate -> save -> index into vector store
- `frontend/src/lib/types.ts` - TypeScript types mirroring backend schemas (manual sync)
- `frontend/src/lib/api.ts` - API client, all backend calls go through here

## Known Technical Debt
1. ~~Sources are from Claude training data, not live web.~~ DONE: Tavily web search added.
2. ~~No RAG / no memory of past research.~~ DONE: ChromaDB vector store added.
3. ~~No social signal integration.~~ DONE: Twitter analyzer integrated.
4. Frontend types manually synced with backend schemas (could generate from OpenAPI)
5. No auth, no caching, no async job queue
6. SQLite module-level connection (fine for local single-user, not for deployment)
7. Two SDK patterns in backend: OpenAI SDK (memo generation) + Anthropic SDK (tweet analysis). Could consolidate later.

## Decisions Made
- **Single Claude call** over multiple calls: fields are interconnected, fewer calls = faster + cheaper
- **No ORM**: one table, raw SQL is simpler and has zero config
- **No state management library**: React state + fetch sufficient for MVP
- **Dark UI theme**: matches investment tooling aesthetic, reduces eye strain for long sessions
- **Tavily for web search**: async client, 3 targeted queries per company (overview, competitors, news), graceful degradation if no API key
- **Source types**: "web" (Tavily URLs), "llm_knowledge" (Claude training data), "social" (Twitter signals). Web sources prepended to list.
- **ChromaDB for RAG**: embedded mode (no server), persists to `./data/chroma`, uses default ONNX MiniLM-L6 embeddings (no extra API calls). Memos indexed on save via `memo_service.create_memo()`.
- **Twitter analyzer adapted (not imported)**: logic from `twitter_analyzer/` project was adapted into `twitter_signals.py` to avoid cross-project imports and PostgreSQL dependency. Uses Anthropic SDK for tweet extraction.
- **Graceful degradation everywhere**: each context source (web, RAG, Twitter) fails independently. Missing API keys or errors skip that source without affecting others.
- **Backfill endpoint**: `POST /api/admin/backfill-vectors` indexes all historical memos into ChromaDB for projects that pre-date RAG.

## Environment Variables
- `OPENAI_API_KEY` (required) - memo generation
- `TAVILY_API_KEY` (optional) - web search
- `X_BEARER_TOKEN` (optional) - Twitter social signals
- `ANTHROPIC_API_KEY` (optional) - Twitter signal analysis via Claude
- `CHROMA_PERSIST_DIR` (optional, default `./data/chroma`) - vector store location
- `DATABASE_PATH` (optional, default `./data/memos.db`) - SQLite location
- `OPENAI_MODEL` (optional, default `gpt-4o`) - model for memo generation
