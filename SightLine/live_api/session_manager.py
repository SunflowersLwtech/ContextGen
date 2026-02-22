"""Session manager for SightLine Live API connections.

Manages session state, resumption handles, and RunConfig construction
for the Gemini Live API via Google ADK.

Phase 3 additions:
- Firestore UserProfile loading (async, with fallback to defaults)
- Per-session face library cache tracking
"""

import logging
import os
from typing import Optional

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import types

from lod.models import EphemeralContext, SessionContext, UserProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LOD-driven VAD presets (SL-36)
# ---------------------------------------------------------------------------

LOD_VAD_PRESETS: dict[int, dict] = {
    1: {
        "voice_name": "Aoede",
        "start_sensitivity": types.StartSensitivity.START_SENSITIVITY_HIGH,
        "end_sensitivity": types.EndSensitivity.END_SENSITIVITY_HIGH,
        "silence_duration_ms": 400,
        "prefix_padding_ms": 100,
    },
    2: {
        "voice_name": "Aoede",
        "start_sensitivity": types.StartSensitivity.START_SENSITIVITY_HIGH,
        "end_sensitivity": types.EndSensitivity.END_SENSITIVITY_LOW,
        "silence_duration_ms": 800,
        "prefix_padding_ms": 200,
    },
    3: {
        "voice_name": "Aoede",
        "start_sensitivity": types.StartSensitivity.START_SENSITIVITY_LOW,
        "end_sensitivity": types.EndSensitivity.END_SENSITIVITY_LOW,
        "silence_duration_ms": 1300,
        "prefix_padding_ms": 300,
    },
}

# ---------------------------------------------------------------------------
# Firestore client (lazy)
# ---------------------------------------------------------------------------

_firestore_client = None


def _get_firestore():
    """Lazily initialize the Firestore client."""
    global _firestore_client
    if _firestore_client is None:
        try:
            from google.cloud import firestore
            project = os.getenv("GOOGLE_CLOUD_PROJECT", "sightline-hackathon")
            _firestore_client = firestore.Client(project=project)
        except Exception:
            logger.warning("Firestore client unavailable; using default profiles")
            _firestore_client = False  # Sentinel to avoid retrying
    return _firestore_client if _firestore_client else None


class SessionManager:
    """Manages Live API session state and RunConfig construction.

    Tracks session resumption handles and per-session context so that
    dropped connections can be transparently resumed.
    """

    def __init__(self) -> None:
        self._session_handles: dict[str, str] = {}
        self._session_contexts: dict[str, SessionContext] = {}
        self._user_profiles: dict[str, UserProfile] = {}
        self._ephemeral_contexts: dict[str, EphemeralContext] = {}

    # -- RunConfig ----------------------------------------------------------

    def get_run_config(self, session_id: str, lod: int = 2) -> RunConfig:
        """Build a RunConfig for the given session."""
        cached_handle = self._session_handles.get(session_id)

        session_resumption = types.SessionResumptionConfig(
            handle=cached_handle,
        )
        if cached_handle:
            logger.info("Resuming session %s with cached handle", session_id)
        else:
            logger.info("Starting fresh session %s (no cached handle)", session_id)

        vad_preset = LOD_VAD_PRESETS.get(lod, LOD_VAD_PRESETS[2])

        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=vad_preset["voice_name"],
                    )
                )
            ),
            proactivity=types.ProactivityConfig(proactive_audio=True),
            enable_affective_dialog=True,
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            session_resumption=session_resumption,
            context_window_compression=types.ContextWindowCompressionConfig(
                trigger_tokens=100_000,
                sliding_window=types.SlidingWindow(target_tokens=80_000),
            ),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    start_of_speech_sensitivity=vad_preset.get("start_sensitivity"),
                    end_of_speech_sensitivity=vad_preset.get("end_sensitivity"),
                    prefix_padding_ms=vad_preset.get("prefix_padding_ms", 200),
                    silence_duration_ms=vad_preset.get("silence_duration_ms", 800),
                )
            ),
        )

        return run_config

    # -- Session handle cache -----------------------------------------------

    def update_handle(self, session_id: str, handle: str) -> None:
        """Cache a session resumption handle."""
        self._session_handles[session_id] = handle
        logger.debug("Cached resumption handle for session %s", session_id)

    def get_handle(self, session_id: str) -> Optional[str]:
        """Retrieve a cached resumption handle."""
        return self._session_handles.get(session_id)

    # -- Per-session context ------------------------------------------------

    def get_session_context(self, session_id: str) -> SessionContext:
        """Get or create the SessionContext for this session."""
        if session_id not in self._session_contexts:
            self._session_contexts[session_id] = SessionContext()
        return self._session_contexts[session_id]

    async def load_user_profile(self, user_id: str) -> UserProfile:
        """Load UserProfile from Firestore, falling back to defaults.

        Caches the result so subsequent calls for the same user_id
        return the cached profile without hitting Firestore again.
        """
        if user_id in self._user_profiles:
            return self._user_profiles[user_id]

        profile = UserProfile.default()
        profile.user_id = user_id

        db = _get_firestore()
        if db:
            try:
                doc = db.collection("users").document(user_id).get()
                if doc.exists:
                    profile = UserProfile.from_firestore(doc.to_dict(), user_id=user_id)
                    logger.info("Loaded UserProfile from Firestore for user %s", user_id)
                else:
                    logger.info("No Firestore profile for user %s; using defaults", user_id)
            except Exception:
                logger.exception("Failed to load profile for user %s; using defaults", user_id)

        self._user_profiles[user_id] = profile
        return profile

    def get_user_profile(self, user_id: str) -> UserProfile:
        """Get cached UserProfile (sync). Use load_user_profile for initial load."""
        if user_id not in self._user_profiles:
            self._user_profiles[user_id] = UserProfile.default()
            self._user_profiles[user_id].user_id = user_id
        return self._user_profiles[user_id]

    def get_ephemeral_context(self, session_id: str) -> EphemeralContext:
        """Get or create the latest EphemeralContext for this session."""
        if session_id not in self._ephemeral_contexts:
            self._ephemeral_contexts[session_id] = EphemeralContext()
        return self._ephemeral_contexts[session_id]

    def update_ephemeral_context(self, session_id: str, ctx: EphemeralContext) -> None:
        """Store the latest ephemeral context snapshot."""
        self._ephemeral_contexts[session_id] = ctx

    # -- Cleanup ------------------------------------------------------------

    def remove_session(self, session_id: str) -> None:
        """Remove all cached state for a session."""
        self._session_handles.pop(session_id, None)
        self._session_contexts.pop(session_id, None)
        self._ephemeral_contexts.pop(session_id, None)
        logger.debug("Removed session state for %s", session_id)
