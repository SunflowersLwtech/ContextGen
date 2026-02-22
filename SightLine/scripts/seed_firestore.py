#!/usr/bin/env python3
"""Seed Firestore with demo user profile and test data.

Usage:
    conda activate sightline
    python scripts/seed_firestore.py

Creates:
    - users/demo_user_001  — default demo user profile
    - users/demo_user_002  — congenital-blind variant (for testing colour-free descriptions)

Requires:
    - GOOGLE_CLOUD_PROJECT env var or gcloud default project
    - Valid credentials (ADC or SA JSON)
"""

import os
import sys

# Ensure the project root is on sys.path so `lod.models` can be imported.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import firestore

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "sightline-hackathon")


def get_client() -> firestore.Client:
    """Create a Firestore client with project ID."""
    return firestore.Client(project=PROJECT_ID)


# ---------------------------------------------------------------------------
# Demo user profiles (matching Infra Report §1.2 schema)
# ---------------------------------------------------------------------------

DEMO_USERS = [
    {
        "doc_id": "demo_user_001",
        "data": {
            "vision_status": "totally_blind",
            "blindness_onset": "acquired",
            "onset_age": 25,
            "has_guide_dog": False,
            "has_white_cane": True,
            "tts_speed": 1.5,
            "verbosity_preference": "standard",
            "language": "en-US",
            "description_priority": "spatial",
            "color_description": True,
            "om_level": "intermediate",
            "travel_frequency": "weekly",
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
    },
    {
        "doc_id": "demo_user_002",
        "data": {
            "vision_status": "totally_blind",
            "blindness_onset": "congenital",
            "onset_age": None,
            "has_guide_dog": True,
            "has_white_cane": False,
            "tts_speed": 2.0,
            "verbosity_preference": "minimal",
            "language": "en-US",
            "description_priority": "spatial",
            "color_description": False,  # Congenital blind — no colour descriptions
            "om_level": "advanced",
            "travel_frequency": "daily",
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
    },
    {
        "doc_id": "demo_user_003",
        "data": {
            "vision_status": "low_vision",
            "blindness_onset": "acquired",
            "onset_age": 40,
            "has_guide_dog": False,
            "has_white_cane": False,
            "tts_speed": 1.2,
            "verbosity_preference": "detailed",
            "language": "en-US",
            "description_priority": "object",
            "color_description": True,
            "om_level": "beginner",
            "travel_frequency": "rarely",
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
    },
]


def seed_users(db: firestore.Client) -> None:
    """Create or overwrite demo user profiles in Firestore."""
    for user in DEMO_USERS:
        doc_ref = db.collection("users").document(user["doc_id"])
        doc_ref.set(user["data"])
        print(f"  [OK] users/{user['doc_id']}")


def seed_session_meta(db: firestore.Client) -> None:
    """Create a sample session metadata document for demo_user_001."""
    doc_ref = (
        db.collection("users")
        .document("demo_user_001")
        .collection("sessions_meta")
        .document("demo_session_001")
    )
    doc_ref.set({
        "start_time": firestore.SERVER_TIMESTAMP,
        "end_time": None,
        "trip_purpose": "Coffee shop visit for demo",
        "lod_distribution": {"lod1": 40, "lod2": 35, "lod3": 25},
        "space_transitions": ["outdoor→lobby", "lobby→cafe"],
        "total_interactions": 0,
    })
    print("  [OK] users/demo_user_001/sessions_meta/demo_session_001")


def verify_indexes(db: firestore.Client) -> None:
    """Check that vector indexes exist (informational only)."""
    print("\n--- Vector Index Status ---")
    print("  face_library (512-D): Check via gcloud firestore indexes composite list")
    print("  memories (2048-D):    Check via gcloud firestore indexes composite list")
    print("  (Indexes were created during Phase 0 — SL-04)")


def main() -> None:
    print(f"Seeding Firestore for project: {PROJECT_ID}\n")

    db = get_client()

    print("--- User Profiles ---")
    seed_users(db)

    print("\n--- Session Metadata ---")
    seed_session_meta(db)

    verify_indexes(db)

    print("\n--- Done! ---")
    print(f"  Total users seeded: {len(DEMO_USERS)}")
    print("  Run `gcloud firestore documents list users --limit=5` to verify.")


if __name__ == "__main__":
    main()
