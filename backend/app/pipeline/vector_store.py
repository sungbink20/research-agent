"""
Vector store module for RAG -- retrieves relevant past memos as context.

Uses ChromaDB in embedded mode (no server needed). Memos are indexed when
created and retrieved by semantic similarity when generating new memos.
This gives the research pipeline memory: if you've researched Aave before,
researching Compound will pull in the Aave memo as relevant context.

Graceful degradation: if chromadb is not installed or the store fails to
initialize, all functions return empty results and log warnings. The rest
of the pipeline continues without RAG context.
"""

import logging
from typing import Optional

from app.config import CHROMA_PERSIST_DIR

logger = logging.getLogger(__name__)

# Module-level ChromaDB collection, initialized on startup.
_collection = None


def init_vector_store() -> bool:
    """
    Initialize ChromaDB persistent client and create/get the memos collection.
    Returns True if successful, False if ChromaDB is unavailable.
    """
    global _collection
    try:
        import chromadb
    except ImportError:
        logger.warning(
            "chromadb is not installed -- RAG disabled. "
            "Run: pip install chromadb"
        )
        return False

    try:
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = client.get_or_create_collection(
            name="memos",
            metadata={"hnsw:space": "cosine"},
        )
        count = _collection.count()
        logger.info(
            f"Vector store initialized: {count} memos indexed "
            f"(persist dir: {CHROMA_PERSIST_DIR})"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")
        _collection = None
        return False


def _memo_to_document(memo) -> str:
    """Convert an InvestmentMemo to a single text document for embedding."""
    parts = [
        f"Company: {memo.company_name}",
        f"Category: {memo.category}",
        f"Summary: {memo.summary}",
        f"Product: {memo.product}",
        f"Customer: {memo.customer}",
        f"Business Model: {memo.business_model}",
    ]
    if memo.bull_case:
        parts.append(f"Bull Case: {'; '.join(memo.bull_case)}")
    if memo.bear_case:
        parts.append(f"Bear Case: {'; '.join(memo.bear_case)}")
    if memo.risks:
        parts.append(f"Risks: {'; '.join(memo.risks)}")
    if memo.competitors:
        parts.append(f"Competitors: {'; '.join(memo.competitors)}")
    if memo.traction_signals:
        parts.append(f"Traction: {'; '.join(memo.traction_signals)}")
    return "\n".join(parts)


def index_memo(memo_id: str, memo) -> bool:
    """
    Index a memo into ChromaDB for future retrieval.
    Returns True if successful, False otherwise.
    """
    if _collection is None:
        return False

    try:
        document = _memo_to_document(memo)
        _collection.upsert(
            ids=[memo_id],
            documents=[document],
            metadatas=[{
                "company_name": memo.company_name,
                "category": memo.category,
            }],
        )
        logger.info(f"Indexed memo {memo_id} ({memo.company_name}) into vector store")
        return True
    except Exception as e:
        logger.warning(f"Failed to index memo {memo_id}: {e}")
        return False


def retrieve_relevant_memos(query: str, n_results: int = 3) -> list[dict]:
    """
    Query ChromaDB for memos semantically similar to the query.
    Returns a list of dicts with memo_id, company_name, category, snippet, distance.
    """
    if _collection is None or _collection.count() == 0:
        return []

    try:
        # Don't request more results than we have documents
        actual_n = min(n_results, _collection.count())
        results = _collection.query(
            query_texts=[query],
            n_results=actual_n,
        )

        memos = []
        for i in range(len(results["ids"][0])):
            memos.append({
                "memo_id": results["ids"][0][i],
                "company_name": results["metadatas"][0][i].get("company_name", "Unknown"),
                "category": results["metadatas"][0][i].get("category", "Unknown"),
                "snippet": results["documents"][0][i][:500],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
        return memos
    except Exception as e:
        logger.warning(f"Vector store query failed: {e}")
        return []


def format_rag_context_for_prompt(results: list[dict]) -> str:
    """
    Format retrieved memos as a text block for prompt injection.
    Similar pattern to format_search_results_for_prompt in web_search.py.
    """
    if not results:
        return ""

    lines = [
        "## Past Research (from your memo archive)\n",
        "The following are summaries from previously generated investment memos "
        "that may be relevant. Use them to inform your analysis -- note any "
        "changes or updates compared to prior research.\n",
    ]

    for i, r in enumerate(results, 1):
        lines.append(f"### [{i}] {r['company_name']} ({r['category']})")
        lines.append(r["snippet"])
        lines.append("")

    return "\n".join(lines)
