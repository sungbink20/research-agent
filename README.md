# Research Agent

AI-powered first-pass investment memo generator. Enter a company name, protocol, or URL and get a structured investment memo with sources, bull/bear framing, and open questions.

Built for internal use by investment teams doing initial diligence.

## Architecture

```
frontend/          Next.js (App Router, TypeScript, Tailwind)
backend/           FastAPI (Python, Pydantic, SQLite)
  app/
    api/           HTTP routes
    services/      Business logic orchestration + persistence
    pipeline/      OpenAI-powered research generation with Tavily web search
    db/            SQLite persistence
    schemas.py     Pydantic models (single source of truth for data shapes)
    config.py      Environment + model + API key config
    main.py        FastAPI app entry point
```

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- An OpenAI API key (get one at https://platform.openai.com)
- (Optional but recommended) A Tavily API key for live web search (https://tavily.com)

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
# Edit .env and add at least your OPENAI_API_KEY
# Optionally set TAVILY_API_KEY for live web search grounding

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

## Usage

1. Start both the backend and frontend servers
2. Open `http://localhost:3000` in your browser
3. Enter a company name (e.g., "Stripe") or click an example
4. Wait 15-30 seconds for the AI to generate the memo
5. Review the memo, rate it, and leave feedback

## Memo Fields

Each generated memo is produced by an OpenAI chat model, optionally grounded with live web search results from Tavily, and includes:

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
- **Sources**: References (from AI knowledge, not live web)

## Important Limitations

- **Sources come from a mix of live web search and model knowledge**, and may contain inaccuracies. They should be independently verified.
- **Web search is best-effort**: if `TAVILY_API_KEY` is not configured or Tavily is unavailable, the pipeline falls back to model-only mode.
- **Not investment advice**: This is a research acceleration tool, not a decision-making system.

## Next Improvements

See the "What to Build Next" section at the bottom of this file.

## What to Build Next

1. **Document ingestion**: Upload PDFs, earnings transcripts, or paste URLs for analysis using the same retrieval pipeline
2. **Memo comparison**: Side-by-side view of two companies or two versions of a memo
3. **Export**: PDF/Notion/email export of memos
4. **Prompt tuning**: Admin UI to edit the system prompt without code changes
5. **Caching**: Don't re-research the same company within a configurable window
6. **Auth**: Simple auth if deployed beyond localhost
