"""Memory auto-extraction at session end.

Analyzes the session transcript using Gemini Flash to extract key memories
(preferences, experiences, people, locations, routines) and stores them
in the user's memory bank with conflict detection.
"""

import json
import logging
from typing import Optional

import numpy as np

from memory.memory_bank import MemoryBankService, _compute_embedding, EMBEDDING_DIM
from memory.memory_budget import MemoryBudgetTracker

logger = logging.getLogger(__name__)

EXTRACTION_MODEL = "gemini-3-flash-preview"

EXTRACTION_PROMPT = """\
You are a memory extraction system for SightLine, an AI assistant for visually impaired users.

Analyze the following conversation transcript and extract key facts the user would want \
remembered across sessions. Focus on:

1. **preference** — User preferences (e.g., "prefers clock-position directions", "likes detailed descriptions")
2. **experience** — Notable experiences or events (e.g., "visited Central Park on 2024-03-15")
3. **person** — People mentioned by name and their relationship (e.g., "David is the user's coworker")
4. **location** — Important locations (e.g., "user's office is at 123 Main St")
5. **routine** — Regular habits or routines (e.g., "takes the 8am bus to work")

For each extracted memory, provide:
- "content": A concise factual statement (1-2 sentences max)
- "category": One of [preference, experience, person, location, routine]
- "importance": Float 0-1 (how important is this for future sessions?)
- "confidence": Float 0-1 (how confident are you this is a real, extractable fact?)

Return a JSON array of objects. If no meaningful memories can be extracted, return an empty array [].

Only extract facts that are clearly stated or strongly implied. Do NOT speculate.

Transcript:
{transcript}
"""


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    va = np.array(a, dtype=np.float64)
    vb = np.array(b, dtype=np.float64)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


class MemoryExtractor:
    """Extracts and stores key memories from a session transcript."""

    def __init__(self, similarity_threshold: float = 0.85, confidence_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        self.confidence_threshold = confidence_threshold

    def extract_and_store(
        self,
        user_id: str,
        session_id: str,
        transcript_history: list[dict],
        memory_bank: MemoryBankService,
        budget: MemoryBudgetTracker,
    ) -> int:
        """Extract memories from a session transcript and store them.

        Args:
            user_id: The user identifier.
            session_id: The session identifier.
            transcript_history: List of {"role": "user"|"agent", "text": "..."} dicts.
            memory_bank: The user's MemoryBankService instance.
            budget: The session's MemoryBudgetTracker.

        Returns:
            Number of memories stored (new + updated).
        """
        if not transcript_history:
            logger.info("No transcript history for session %s, skipping extraction", session_id)
            return 0

        transcript_text = self._format_transcript(transcript_history)
        if len(transcript_text.strip()) < 20:
            logger.info("Transcript too short for session %s, skipping extraction", session_id)
            return 0

        # Extract candidate memories via Gemini Flash
        candidates = self._call_extraction_model(transcript_text)
        if not candidates:
            logger.info("No memories extracted for session %s", session_id)
            return 0

        # Fetch existing memories for conflict detection
        existing_memories = memory_bank.retrieve_memories(context="", top_k=50)

        stored_count = 0
        for candidate in candidates:
            confidence = float(candidate.get("confidence", 0))
            if confidence < self.confidence_threshold:
                logger.debug(
                    "Skipping low-confidence memory (%.2f): %s",
                    confidence, candidate.get("content", "")[:80],
                )
                continue

            if budget.exhausted:
                logger.info("Memory budget exhausted, stopping extraction for session %s", session_id)
                break

            if not budget.try_write():
                logger.info("Memory budget denied write, stopping extraction for session %s", session_id)
                break

            content = candidate["content"]
            category = candidate.get("category", "general")
            importance = float(candidate.get("importance", 0.5))

            # Conflict detection: check if a similar memory already exists
            duplicate = self._find_duplicate(content, existing_memories)
            if duplicate is not None:
                # Update existing memory instead of creating new one
                memory_id = duplicate.get("memory_id")
                if memory_id:
                    memory_bank.delete_memory(memory_id)
                    new_id = memory_bank.store_memory(content, category, importance)
                    if new_id:
                        logger.info(
                            "Updated memory %s -> %s for user %s (conflict resolved)",
                            memory_id, new_id, user_id,
                        )
                        stored_count += 1
            else:
                new_id = memory_bank.store_memory(content, category, importance)
                if new_id:
                    logger.info("Stored new memory %s for user %s", new_id, user_id)
                    stored_count += 1

        logger.info(
            "Memory extraction complete for session %s: %d memories stored",
            session_id, stored_count,
        )
        return stored_count

    def _format_transcript(self, transcript_history: list[dict]) -> str:
        """Format transcript history into a readable string."""
        lines = []
        for entry in transcript_history:
            role = entry.get("role", "unknown")
            text = entry.get("text", "")
            if text.strip():
                label = "User" if role == "user" else "Assistant"
                lines.append(f"{label}: {text}")
        return "\n".join(lines)

    def _call_extraction_model(self, transcript_text: str) -> list[dict]:
        """Call Gemini Flash to extract memories from transcript."""
        try:
            from google import genai

            client = genai.Client()
            prompt = EXTRACTION_PROMPT.format(transcript=transcript_text)

            response = client.models.generate_content(
                model=EXTRACTION_MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.2,
                },
            )

            raw_text = response.text.strip()
            candidates = json.loads(raw_text)
            if not isinstance(candidates, list):
                logger.warning("Extraction model returned non-list: %s", type(candidates))
                return []
            return candidates
        except Exception:
            logger.exception("Memory extraction model call failed")
            return []

    def _find_duplicate(
        self, content: str, existing_memories: list[dict]
    ) -> Optional[dict]:
        """Check if content is semantically similar to an existing memory.

        Returns the matching memory dict if similarity > threshold, else None.
        """
        if not existing_memories:
            return None

        new_embedding = _compute_embedding(content)
        # Skip comparison if embedding failed (zero vector)
        if all(v == 0.0 for v in new_embedding[:10]):
            return None

        for mem in existing_memories:
            existing_content = mem.get("content", "")
            if not existing_content:
                continue
            existing_embedding = _compute_embedding(existing_content)
            if all(v == 0.0 for v in existing_embedding[:10]):
                continue

            sim = _cosine_similarity(new_embedding, existing_embedding)
            if sim > self.similarity_threshold:
                logger.debug(
                    "Found duplicate (sim=%.3f): '%s' ~ '%s'",
                    sim, content[:50], existing_content[:50],
                )
                return mem

        return None
