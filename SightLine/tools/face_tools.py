"""SightLine face library CRUD tools.

Manages the Firestore face library for per-user face registration,
deletion, and loading. Embeddings are stored as Firestore Vectors.

Firestore collection: users/{user_id}/face_library/{face_id}

Privacy: NEVER stores raw images — only 512-D L2-normalized embeddings.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "sightline-hackathon")

# Phase 3 SL-57 registration contract: enroll using 3-5 samples.
MIN_FACE_SAMPLES = 3
MAX_FACE_SAMPLES = 5

_db_client: Optional[firestore.Client] = None


def _get_db() -> firestore.Client:
    """Return a lazily-initialized Firestore client."""
    global _db_client
    if _db_client is None:
        _db_client = firestore.Client(project=PROJECT_ID)
    return _db_client


def set_db_client(client: firestore.Client) -> None:
    """Override the Firestore client (for testing)."""
    global _db_client
    _db_client = client


def _face_collection(user_id: str):
    """Return the face_library subcollection reference for a user."""
    return _get_db().collection("users").document(user_id).collection("face_library")


def register_face(
    user_id: str,
    person_name: str,
    relationship: str,
    image_base64: str,
    photo_index: int = 0,
) -> dict:
    """Register a new face entry by detecting, embedding, and storing.

    Args:
        user_id: The user who owns this face library.
        person_name: Name of the person being registered.
        relationship: Relationship to the user (e.g. "friend", "spouse").
        image_base64: Base64-encoded image containing the person's face.
        photo_index: Index when registering multiple photos (0-based).

    Returns:
        Dict with face_id, person_name, relationship, photo_index, created_at.

    Raises:
        ValueError: If no face is detected in the image.
    """
    # Import here to avoid circular dependency at module level
    from agents.face_agent import _decode_image, _get_face_app

    img = _decode_image(image_base64)
    app = _get_face_app()
    faces = app.get(img)

    if not faces:
        raise ValueError("No face detected in the provided image")

    embedding = faces[0].normed_embedding

    now = datetime.now(timezone.utc)
    doc_data = {
        "person_name": person_name,
        "relationship": relationship,
        "embedding": Vector(embedding.tolist()),
        "photo_index": photo_index,
        "registered_by": user_id,
        "created_at": now,
    }

    doc_ref = _face_collection(user_id).document()
    doc_ref.set(doc_data)

    logger.info("Registered face %s for user %s (%s)", doc_ref.id, user_id, person_name)

    return {
        "face_id": doc_ref.id,
        "person_name": person_name,
        "relationship": relationship,
        "photo_index": photo_index,
        "created_at": now.isoformat(),
    }


def delete_face(user_id: str, face_id: str) -> bool:
    """Delete a single face entry from the library.

    Args:
        user_id: The user who owns this face library.
        face_id: The Firestore document ID of the face to delete.

    Returns:
        True if the document existed and was deleted, False otherwise.
    """
    doc_ref = _face_collection(user_id).document(face_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False
    doc_ref.delete()
    logger.info("Deleted face %s for user %s", face_id, user_id)
    return True


def clear_face_library(user_id: str) -> int:
    """One-click delete for all face entries under a user.

    Args:
        user_id: The user who owns this face library.

    Returns:
        Number of documents deleted.
    """
    docs = _face_collection(user_id).stream()
    count = 0
    for doc in docs:
        doc.reference.delete()
        count += 1

    logger.info("Cleared %d face(s) from library for user %s", count, user_id)
    return count


def delete_all_faces(user_id: str, person_name: str | None = None) -> int:
    """Delete all face entries for a specific person, or clear all when omitted.

    Args:
        user_id: The user who owns this face library.
        person_name: Optional name filter. If omitted, clear the full library.

    Returns:
        Number of documents deleted.
    """
    if not person_name:
        return clear_face_library(user_id)

    query = _face_collection(user_id).where("person_name", "==", person_name)
    docs = query.stream()

    count = 0
    for doc in docs:
        doc.reference.delete()
        count += 1

    logger.info(
        "Deleted %d face(s) for person '%s' (user %s)", count, person_name, user_id
    )
    return count


def list_faces(user_id: str) -> list[dict]:
    """List all registered faces for a user (without embeddings).

    Args:
        user_id: The user who owns this face library.

    Returns:
        List of dicts with face_id, person_name, relationship,
        photo_index, created_at.
    """
    docs = _face_collection(user_id).stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        results.append({
            "face_id": doc.id,
            "person_name": data.get("person_name", ""),
            "relationship": data.get("relationship", ""),
            "photo_index": data.get("photo_index", 0),
            "created_at": (
                data["created_at"].isoformat()
                if isinstance(data.get("created_at"), datetime)
                else str(data.get("created_at", ""))
            ),
        })
    return results


def load_face_library(user_id: str) -> list[dict]:
    """Load all face embeddings into memory for real-time matching.

    Args:
        user_id: The user who owns this face library.

    Returns:
        List of dicts with face_id, person_name, relationship, embedding
        (as numpy array). Ready to pass to face_agent.match_face().
    """
    docs = _face_collection(user_id).stream()

    library = []
    for doc in docs:
        data = doc.to_dict()
        emb_raw = data.get("embedding")
        if emb_raw is None:
            continue

        # Firestore Vector -> list[float] -> numpy array
        if hasattr(emb_raw, "value"):
            emb_list = emb_raw.value
        elif isinstance(emb_raw, (list, tuple)):
            emb_list = emb_raw
        else:
            continue

        library.append({
            "face_id": doc.id,
            "person_name": data.get("person_name", ""),
            "relationship": data.get("relationship", ""),
            "embedding": np.array(emb_list, dtype=np.float32),
        })

    logger.info("Loaded %d face(s) for user %s", len(library), user_id)
    return library
