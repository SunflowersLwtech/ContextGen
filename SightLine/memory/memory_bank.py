"""SightLine long-term memory service.

Wraps Firestore-based storage for persistent cross-session memory.
Uses Gemini embeddings for semantic retrieval via Firestore vector search.

Firestore collection: user_profiles/{user_id}/memories/{memory_id}
Embedding model: gemini-embedding-001 (truncated to 2048-D)
"""

import logging
import os
import re
import time
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "sightline-hackathon")
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 2048


def _compute_embedding(text: str) -> list[float]:
    """Compute a 2048-D embedding for the given text using google-genai.

    Returns a zero vector on failure so callers can proceed gracefully.
    """
    normalized = (text or "").strip()
    if not normalized:
        logger.debug("Embedding input text is empty; using zero vector")
        return [0.0] * EMBEDDING_DIM

    try:
        from google import genai

        client = genai.Client()
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=normalized,
            config={"output_dimensionality": EMBEDDING_DIM},
        )
        return result.embeddings[0].values
    except Exception:
        logger.warning("Embedding computation failed; using zero vector", exc_info=True)
        return [0.0] * EMBEDDING_DIM


class MemoryBankService:
    """Firestore-backed long-term memory for a single user.

    Provides persistent memory storage across sessions with semantic
    retrieval via embeddings.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._firestore = None
        self._memories_cache: list[dict] = []
        self._init_backend()

    def _init_backend(self, max_retries: int = 3):
        """Initialize Firestore backend with retry and exponential backoff."""
        for attempt in range(max_retries):
            try:
                from google.cloud import firestore

                self._firestore = firestore.Client(project=PROJECT_ID)
                logger.info("MemoryBankService initialized for user %s", self.user_id)
                return
            except Exception as e:
                wait = min(2 ** attempt, 4)
                logger.warning(
                    "Firestore init attempt %d/%d failed: %s (retry in %ds)",
                    attempt + 1, max_retries, e, wait,
                )
                if attempt < max_retries - 1:
                    import time as _time
                    _time.sleep(wait)
        logger.error(
            "Firestore unavailable after %d attempts; memories will be EPHEMERAL",
            max_retries,
        )

    def _memories_collection(self):
        """Return the memories subcollection reference for this user."""
        return (
            self._firestore.collection("user_profiles")
            .document(self.user_id)
            .collection("memories")
        )

    def store_memory(
        self, content: str, category: str = "general", importance: float = 0.5
    ) -> Optional[str]:
        """Store a memory with metadata and embedding.

        Args:
            content: The memory text content.
            category: Classification (e.g. "general", "place", "person").
            importance: Importance score from 0 to 1.

        Returns:
            The Firestore document ID, or None on failure.
        """
        if not self._firestore:
            # Ephemeral fallback: store in cache only
            memory_id = uuid.uuid4().hex
            self._memories_cache.append({
                "memory_id": memory_id,
                "content": content,
                "category": category,
                "importance": importance,
                "timestamp": time.time(),
            })
            return memory_id

        try:
            from google.cloud.firestore_v1.vector import Vector

            embedding = _compute_embedding(content)
            now = time.time()
            doc_data = {
                "content": content,
                "category": category,
                "importance": importance,
                "timestamp": now,
                "embedding": Vector(embedding),
            }

            doc_ref = self._memories_collection().document()
            doc_ref.set(doc_data)
            logger.info("Stored memory %s for user %s", doc_ref.id, self.user_id)
            return doc_ref.id
        except Exception:
            logger.error("Failed to store memory for user %s", self.user_id, exc_info=True)
            return None

    def retrieve_memories(self, context: str, top_k: int = 3) -> list[dict]:
        """Retrieve relevant memories using vector search with text fallback.

        First attempts Firestore vector nearest-neighbor search. If that
        fails (e.g. index not ready), falls back to fetching recent
        memories and doing client-side text matching.

        Results are re-ranked using the three-dimensional scoring from
        memory_ranking (relevance 0.5 + recency 0.3 + importance 0.2).

        Args:
            context: Current conversation context or query string.
            top_k: Maximum number of memories to return.

        Returns:
            List of memory dicts with content, category, importance,
            timestamp, relevance_score, and memory_id.
        """
        from memory.memory_ranking import rank_memories

        if not self._firestore:
            results = self._retrieve_from_cache(context, top_k * 2)
            return rank_memories(results, query_context=context, max_results=top_k)

        # Try Firestore vector search first
        try:
            results = self._vector_search(context, top_k * 2)
            return rank_memories(results, query_context=context, max_results=top_k)
        except Exception:
            logger.debug("Vector search unavailable, falling back to text match", exc_info=True)

        # Fallback: fetch recent memories and rank by text overlap
        results = self._text_fallback(context, top_k * 2)
        return rank_memories(results, query_context=context, max_results=top_k)

    def _vector_search(self, context: str, top_k: int) -> list[dict]:
        """Firestore find_nearest vector search."""
        from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
        from google.cloud.firestore_v1.vector import Vector

        query_embedding = _compute_embedding(context)
        coll = self._memories_collection()

        vector_query = coll.find_nearest(
            vector_field="embedding",
            query_vector=Vector(query_embedding),
            distance_measure=DistanceMeasure.COSINE,
            limit=top_k,
        )

        results = []
        for doc in vector_query.stream():
            data = doc.to_dict()
            results.append({
                "memory_id": doc.id,
                "content": data.get("content", ""),
                "category": data.get("category", "general"),
                "importance": float(data.get("importance", 0.5)),
                "timestamp": float(data.get("timestamp", 0)),
                "relevance_score": 0.8,  # Vector search results are inherently relevant
            })

        return results

    def _text_fallback(self, context: str, top_k: int) -> list[dict]:
        """Fetch recent memories and score by keyword overlap."""
        coll = self._memories_collection()
        query = coll.order_by("timestamp", direction="DESCENDING").limit(20)

        results = []
        context_words = set(context.lower().split())

        for doc in query.stream():
            data = doc.to_dict()
            content = data.get("content", "")
            content_words = set(content.lower().split())

            # Simple Jaccard-like relevance score
            if context_words and content_words:
                overlap = len(context_words & content_words)
                union = len(context_words | content_words)
                relevance = overlap / union if union > 0 else 0.0
            else:
                relevance = 0.1

            results.append({
                "memory_id": doc.id,
                "content": content,
                "category": data.get("category", "general"),
                "importance": float(data.get("importance", 0.5)),
                "timestamp": float(data.get("timestamp", 0)),
                "relevance_score": relevance,
            })

        # Sort by relevance and return top_k
        results.sort(key=lambda m: m["relevance_score"], reverse=True)
        return results[:top_k]

    def _retrieve_from_cache(self, context: str, top_k: int) -> list[dict]:
        """Retrieve from in-memory cache (ephemeral fallback)."""
        context_words = set(context.lower().split())
        scored = []

        for mem in self._memories_cache:
            content_words = set(mem["content"].lower().split())
            if context_words and content_words:
                overlap = len(context_words & content_words)
                union = len(context_words | content_words)
                relevance = overlap / union if union > 0 else 0.0
            else:
                relevance = 0.1

            scored.append({**mem, "relevance_score": relevance})

        scored.sort(key=lambda m: m["relevance_score"], reverse=True)
        return scored[:top_k]

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory by ID.

        Args:
            memory_id: The Firestore document ID.

        Returns:
            True if the document existed and was deleted, False otherwise.
        """
        if not self._firestore:
            before = len(self._memories_cache)
            self._memories_cache = [
                m for m in self._memories_cache if m.get("memory_id") != memory_id
            ]
            return len(self._memories_cache) < before

        try:
            doc_ref = self._memories_collection().document(memory_id)
            doc = doc_ref.get()
            if not doc.exists:
                return False
            doc_ref.delete()
            logger.info("Deleted memory %s for user %s", memory_id, self.user_id)
            return True
        except Exception:
            logger.error("Failed to delete memory %s", memory_id, exc_info=True)
            return False

    def delete_recent_memories(self, minutes: int = 30) -> int:
        """Delete memories created within the last N minutes.

        Args:
            minutes: How far back to delete.

        Returns:
            Number of memories deleted.
        """
        cutoff = time.time() - (minutes * 60)

        if not self._firestore:
            before = len(self._memories_cache)
            self._memories_cache = [
                m for m in self._memories_cache
                if m.get("timestamp", 0) < cutoff
            ]
            return before - len(self._memories_cache)

        try:
            coll = self._memories_collection()
            query = coll.where("timestamp", ">=", cutoff)
            count = 0
            for doc in query.stream():
                doc.reference.delete()
                count += 1
            logger.info(
                "Deleted %d recent memories (last %d min) for user %s",
                count, minutes, self.user_id,
            )
            return count
        except Exception:
            logger.error("Failed to delete recent memories", exc_info=True)
            return 0


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

_bank_instances: dict[str, MemoryBankService] = {}


def _get_bank(user_id: str) -> MemoryBankService:
    """Get or create a MemoryBankService for the given user."""
    if user_id not in _bank_instances:
        _bank_instances[user_id] = MemoryBankService(user_id)
    return _bank_instances[user_id]


def _sanitize_memory_content(text: str) -> str:
    """Remove prompt-injection patterns from memory content."""
    text = re.sub(r'(?i)ignore\s+(all\s+)?previous\s+instructions?', '[REDACTED]', text)
    text = re.sub(r'(?i)you\s+are\s+now\s+', 'the user mentioned ', text)
    text = re.sub(r'(?i)system\s*:\s*', '', text)
    return text.strip()


def load_relevant_memories(user_id: str, context: str, top_k: int = 3) -> list[str]:
    """Load top-K relevant memories for prompt injection.

    Returns a list of sanitized memory content strings, ranked by relevance.
    """
    bank = _get_bank(user_id)
    results = bank.retrieve_memories(context, top_k=top_k)
    return [_sanitize_memory_content(m["content"]) for m in results]


def preload_memory(user_id: str, context: str) -> dict:
    """PreloadMemoryTool - function calling compatible entry point.

    Returns a dict suitable for injection into the agent context.
    """
    memories = load_relevant_memories(user_id, context, top_k=3)
    return {
        "memories": memories,
        "count": len(memories),
        "user_id": user_id,
    }
