"""Memory-related function calling tools for the Orchestrator.

These tools are registered with the Gemini agent for function calling.
"""

import logging

logger = logging.getLogger(__name__)


def preload_memory(user_id: str, context: str = "") -> dict:
    """Preload relevant long-term memories for the current conversation context.

    This tool is called by the Orchestrator to fetch memories
    that should be injected into the conversation context.

    Args:
        user_id: The user identifier.
        context: Current conversation context or query.

    Returns:
        Dict with memories list, count, and user_id.
    """
    from memory.memory_bank import load_relevant_memories

    memories = load_relevant_memories(user_id, context, top_k=3)
    return {
        "memories": memories,
        "count": len(memories),
        "user_id": user_id,
    }


def forget_recent_memory(user_id: str, minutes: int = 30) -> dict:
    """Forget (delete) memories created within the last N minutes.

    Reserved interface for user-triggered memory deletion.
    Allows users to say "forget what I just told you" to remove
    recent memories from the system.

    Args:
        user_id: The user identifier.
        minutes: How far back to delete (default 30 minutes).

    Returns:
        Dict with deleted count and status.
    """
    from memory.memory_bank import _get_bank

    bank = _get_bank(user_id)
    deleted = bank.delete_recent_memories(minutes=minutes)
    return {
        "deleted": deleted,
        "minutes": minutes,
        "status": "ok",
    }


def forget_memory(user_id: str, memory_id: str) -> dict:
    """Delete a specific memory by its ID.

    Args:
        user_id: The user identifier.
        memory_id: The memory document ID to delete.

    Returns:
        Dict with deletion status.
    """
    from memory.memory_bank import _get_bank

    bank = _get_bank(user_id)
    success = bank.delete_memory(memory_id)
    return {
        "memory_id": memory_id,
        "deleted": success,
        "status": "ok" if success else "not_found",
    }


MEMORY_FUNCTIONS = {
    "preload_memory": preload_memory,
    "forget_recent_memory": forget_recent_memory,
    "forget_memory": forget_memory,
}
