# Research Agent

AI-powered first-pass investment memo generator. Enter a company name, protocol, or URL and get a structured investment memo grounded with live web search, past research (RAG), and Crypto Twitter social signals.

Built for internal use by investment teams doing initial diligence.

## Architecture

```
frontend/          Next.js (App Router, TypeScript, Tailwind)
backend/           FastAPI (Python, Pydantic, SQLite)
  app/
    api/           HTTP routes
    services/      Business logic orchestration + persistence
    pipeline/
      researcher.py     Claude-powered memo generation (orchestrates all context sources)
      web_search.py     Tavily web search for live grounding
      vector_store.py   ChromaDB RAG -- stores and retrieves past memos by semantic similarity
      twitter_signals.py Twitter/X social signal collection + Claude analysis
    db/            SQLite persistence
    schemas.py     Pydantic models (single source of truth for data shapes)
    config.py      Environment + model + API key config
    main.py        FastAPI app entry point
  data/
    memos.db       SQLite database
    chroma/        ChromaDB vector store (persistent)
```

## Context Sources

The research pipeline gathers context from three sources before generating a memo:

1. **Web Search (Tavily)** -- live web results for the company (overview, competitors, news). Runs concurrently with Twitter.
2. **RAG (ChromaDB)** -- retrieves semantically similar past memos from the archive. If you've researched Aave before, researching Compound will pull in Aave as context.
3. **Twitter Signals** -- searches Crypto Twitter for recent mentions, then uses Claude to extract trending narratives, sentiment, token mentions, and notable quotes. Runs concurrently with web search.

Each source degrades gracefully -- missing API keys or failures skip that source without crashing the pipeline.

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- An OpenAI API key (get one at https://platform.openai.com)
- (Optional) A Tavily API key for live web search (https://tavily.com)
- (Optional) An X/Twitter Bearer Token for social signals (https://developer.x.com)
- (Optional) An Anthropic API key for Twitter signal analysis (https://console.anthropic.com)

### Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and set:
#   OPENAI_API_KEY     (required)
#   TAVILY_API_KEY     (optional -- enables live web search)
#   X_BEARER_TOKEN     (optional -- enables Twitter social signals)
#   ANTHROPIC_API_KEY  (optional -- enables Twitter signal analysis, needed alongside X_BEARER_TOKEN)

# Run the server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run the dev server
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### Backfilling the Vector Store

If you have existing memos from before RAG was added, backfill them into ChromaDB:

```bash
curl -X POST http://localhost:8000/api/admin/backfill-vectors
```

This indexes all historical memos so they can be retrieved as context for future research.

## Usage

1. Start both the backend and frontend servers
2. Open `http://localhost:3000` in your browser
3. Enter a company name (e.g., "Stripe") or click an example
4. Wait 15-30 seconds for the AI to generate the memo
5. Review the memo, rate it, and leave feedback

## Memo Fields

Each generated memo is produced by a Claude model call, grounded with up to three context sources, and includes:

- **Summary**: Executive overview
- **Product**: What it does
- **Customer**: Who uses it
- **Business Model**: How it makes money
- **Traction Signals**: Evidence of adoption
- **Competitors**: Direct and indirect
- **Bull Case**: Reasons to invest
- **Bear Case**: Reasons to be cautious
- **Risks**: Key risk factors
- **Open Questions**: What to investigate further
- **Sources**: References tagged by type (`web`, `llm_knowledge`, `social`)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/memos` | Generate a new investment memo |
| GET | `/api/memos` | List recent memos (paginated) |
| GET | `/api/memos/{id}` | Get a specific memo |
| POST | `/api/memos/{id}/feedback` | Submit rating + feedback |
| POST | `/api/admin/backfill-vectors` | Index all existing memos into ChromaDB |
| GET | `/api/health` | Health check |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for memo generation |
| `OPENAI_MODEL` | No | Model to use (default: `gpt-4o`) |
| `TAVILY_API_KEY` | No | Enables live web search grounding |
| `X_BEARER_TOKEN` | No | Enables Twitter/X social signals |
| `ANTHROPIC_API_KEY` | No | Enables Claude-powered Twitter signal analysis |
| `DATABASE_PATH` | No | SQLite path (default: `./data/memos.db`) |
| `CHROMA_PERSIST_DIR` | No | ChromaDB storage (default: `./data/chroma`) |

## Important Limitations

- **Sources come from a mix of live web search, model knowledge, and social media**, and may contain inaccuracies. They should be independently verified.
- **Each context source is best-effort**: missing API keys or failures skip that source gracefully.
- **Twitter free tier is limited**: 1500 tweets/month read. Each memo uses ~15 tweets.
- **RAG improves over time**: the more memos you generate, the better the retrieval context becomes.
- **Not investment advice**: This is a research acceleration tool, not a decision-making system.

## What to Build Next

1. **Document ingestion**: Upload PDFs, earnings transcripts, or paste URLs for analysis using the same retrieval pipeline
2. **Memo comparison**: Side-by-side view of two companies or two versions of a memo
3. **Export**: PDF/Notion/email export of memos
4. **Prompt tuning**: Admin UI to edit the system prompt without code changes
5. **Caching**: Don't re-research the same company within a configurable window
6. **Auth**: Simple auth if deployed beyond localhost
