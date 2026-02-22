"""Memory retrieval ranking with three-dimensional scoring.

Dimensions:
- relevance: Semantic similarity to current context
- recency: How recent the memory is
- importance: User-assigned or system-inferred importance
"""

import time

# Dimension weights (tunable)
RELEVANCE_WEIGHT = 0.5
RECENCY_WEIGHT = 0.3
IMPORTANCE_WEIGHT = 0.2


def rank_memories(
    memories: list[dict],
    query_context: str = "",
    max_results: int = 3,
) -> list[dict]:
    """Rank memories by composite score of relevance, recency, importance.

    Each memory dict should have:
      - content: str
      - timestamp: float (unix epoch)
      - importance: float (0-1)
      - relevance_score: float (0-1, from semantic search)

    Returns sorted list (highest score first), limited to max_results.
    """
    scored = []
    now = time.time()

    for mem in memories:
        relevance = float(mem.get("relevance_score", 0.5))
        importance = float(mem.get("importance", 0.5))

        # Recency: exponential decay (half-life = 24 hours)
        ts = float(mem.get("timestamp", now))
        age_hours = (now - ts) / 3600
        recency = 2 ** (-age_hours / 24)

        composite = (
            RELEVANCE_WEIGHT * relevance
            + RECENCY_WEIGHT * recency
            + IMPORTANCE_WEIGHT * importance
        )

        scored.append({**mem, "_composite_score": composite, "_recency": recency})

    scored.sort(key=lambda m: m["_composite_score"], reverse=True)
    return scored[:max_results]


def score_memories(memories: list[dict], context: str = "") -> list[dict]:
    """Alias for rank_memories (backward compatibility)."""
    return rank_memories(memories, query_context=context)
