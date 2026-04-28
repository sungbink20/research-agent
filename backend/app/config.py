"""
Application configuration loaded from environment variables.

We use a simple module-level config object rather than dependency injection
for MVP simplicity. Easy to swap for a proper settings pattern later.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# Optional but recommended: enables live web search grounding for memos.
# Get a key at https://tavily.com -- free tier includes 1000 searches/month.
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

# Optional: enables Twitter/X social signals in memos.
# Free tier: 1500 tweets/month read. Each memo uses ~15 tweets.
X_BEARER_TOKEN: str = os.getenv("X_BEARER_TOKEN", "")

# Optional: used by the Twitter signal analyzer to call Claude for extraction.
# If not set, falls back to OPENAI_API_KEY is not used -- Twitter signals are simply skipped.
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# --- Database ---
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./data/memos.db")

# --- Vector Store (RAG) ---
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")

# --- OpenAI model ---
# Using gpt-4o for good quality at reasonable cost/speed.
# Switch to gpt-4o-mini for faster/cheaper, o1 for higher reasoning quality.
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

# --- Server ---
CORS_ORIGINS: list[str] = [
    "http://localhost:3000",  # Next.js dev server
    "http://127.0.0.1:3000",
]


def validate_config() -> list[str]:
    """Check for missing required config. Returns list of warnings."""
    warnings = []
    if not OPENAI_API_KEY:
        warnings.append(
            "OPENAI_API_KEY is not set. The research pipeline will fail. "
            "Set it in backend/.env or as an environment variable."
        )
    if not TAVILY_API_KEY:
        warnings.append(
            "TAVILY_API_KEY is not set. Memos will use Claude training data only "
            "(no live web search). Set it in backend/.env for grounded results."
        )
    if not X_BEARER_TOKEN:
        warnings.append(
            "X_BEARER_TOKEN is not set. Twitter social signals will be skipped. "
            "Set it in backend/.env to include Crypto Twitter context in memos."
        )
    if not ANTHROPIC_API_KEY:
        warnings.append(
            "ANTHROPIC_API_KEY is not set. Twitter signal analysis requires this. "
            "Set it in backend/.env alongside X_BEARER_TOKEN."
        )
    # Ensure data directories exist
    db_dir = Path(DATABASE_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    chroma_dir = Path(CHROMA_PERSIST_DIR)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return warnings
