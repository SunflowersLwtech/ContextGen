"""Session manager for SightLine Live API connections.

Manages session state, resumption handles, and RunConfig construction
for the Gemini Live API via Google ADK.

Phase 3 additions:
- Firestore UserProfile loading (async, with fallback to defaults)
- Per-session face library cache tracking

Phase 4 additions:
- 3-tier session service fallback: VertexAi → Database → InMemory (depends on AGENT_ENGINE_ID at runtime)
"""

import logging
import os
import time
from typing import Optional

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import types

from lod.models import EphemeralContext, SessionContext, UserProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Session service factory (SL-70)
# ---------------------------------------------------------------------------

AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID", "")


def _env_flag(name: str, default: bool = False) -> bool:
    """Parse bool-like environment values."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def create_session_service():
    """Create the session service, preferring VertexAiSessionService.

    Uses VertexAiSessionService whenever the SDK provides it. Falls back
    gracefully for local development.
    """
    # Read env at call time because server.py loads .env after imports.
    agent_engine_id = os.getenv("AGENT_ENGINE_ID", "").strip() or None
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "sightline-hackathon")
    location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    use_vertex = _env_flag("GOOGLE_GENAI_USE_VERTEXAI", default=False)

    if use_vertex:
        try:
            from google.adk.sessions import VertexAiSessionService

            svc = VertexAiSessionService(
                project=project,
                location=location,
                agent_engine_id=agent_engine_id,
            )
            if agent_engine_id:
                logger.info(
                    "Using VertexAiSessionService (engine=%s)", agent_engine_id
                )
            else:
                logger.info(
                    "Using VertexAiSessionService (engine unset, project=%s, location=%s)",
                    project,
                    location,
                )
            return svc
        except (ImportError, Exception) as exc:
            logger.warning("VertexAiSessionService unavailable (%s); using fallback.", exc)
    else:
        if agent_engine_id:
            logger.info(
                "GOOGLE_GENAI_USE_VERTEXAI is FALSE; ignoring AGENT_ENGINE_ID=%s and using local session service",
                agent_engine_id,
            )
        else:
            logger.info(
                "GOOGLE_GENAI_USE_VERTEXAI is FALSE; using local session service"
            )

    # Cloud Run has an ephemeral filesystem — SQLite will always fail.
    # Skip straight to in-memory to avoid noisy WARNING logs on every cold start.
    if os.getenv("K_SERVICE"):
        from google.adk.sessions import InMemorySessionService as _InMemory

        logger.info("Cloud Run detected — using in-memory session service")
        return _InMemory()

    # Local development: try DatabaseSessionService, then in-memory
    try:
        from google.adk.sessions import DatabaseSessionService

        svc = DatabaseSessionService(db_url="sqlite:///sightline_sessions.db")
        logger.info("Using DatabaseSessionService (SQLite fallback)")
        return svc
    except (ImportError, Exception) as exc:
        logger.warning("DatabaseSessionService unavailable (%s); using in-memory.", exc)

    # Last resort — lightweight in-memory service
    from google.adk.sessions import InMemorySessionService as _InMemory

    logger.warning("Using in-memory session service (development only)")
    return _InMemory()

# ---------------------------------------------------------------------------
# LOD-driven VAD presets (SL-36)
# ---------------------------------------------------------------------------

# NOTE: Server-side automatic VAD is disabled (see get_run_config).
# These presets are retained for debug overlay display and LOD transition
# messages but have no runtime effect on Gemini's VAD behavior.
LOD_VAD_PRESETS: dict[int, dict] = {
    1: {
        "voice_name": "Aoede",
        "start_sensitivity": types.StartSensitivity.START_SENSITIVITY_LOW,
        "end_sensitivity": types.EndSensitivity.END_SENSITIVITY_LOW,
        "silence_duration_ms": 800,
        "prefix_padding_ms": 250,
    },
    2: {
        "voice_name": "Aoede",
        "start_sensitivity": types.StartSensitivity.START_SENSITIVITY_LOW,
        "end_sensitivity": types.EndSensitivity.END_SENSITIVITY_HIGH,
        "silence_duration_ms": 1200,
        "prefix_padding_ms": 250,
    },
    3: {
        "voice_name": "Aoede",
        "start_sensitivity": types.StartSensitivity.START_SENSITIVITY_LOW,
        "end_sensitivity": types.EndSensitivity.END_SENSITIVITY_LOW,
        "silence_duration_ms": 1500,
        "prefix_padding_ms": 300,
    },
}


def _enum_label(value) -> str:
    """Convert SDK enum values into stable log/debug labels."""
    if value is None:
        return "UNSPECIFIED"
    if hasattr(value, "name"):
        return str(value.name)
    return str(value).split(".")[-1]


def get_lod_vad_preset(lod: int) -> dict:
    """Return a copy of the LOD-specific VAD preset."""
    return dict(LOD_VAD_PRESETS.get(lod, LOD_VAD_PRESETS[2]))


def supports_runtime_vad_reconfiguration() -> tuple[bool, str]:
    """Whether ADK transport can hot-update VAD config mid-session.

    google-adk 1.25.x LiveRequestQueue currently only supports:
    content, realtime blobs, and activity start/end signals.
    """
    return (
        False,
        "LiveRequestQueue does not expose realtime_input_config updates mid-session.",
    )


def build_vad_runtime_update_payload(lod: int) -> dict:
    """Build a serializable VAD payload for logging/debug contracts."""
    preset = get_lod_vad_preset(lod)
    return {
        "lod": lod,
        "start_of_speech_sensitivity": _enum_label(preset.get("start_sensitivity")),
        "end_of_speech_sensitivity": _enum_label(preset.get("end_sensitivity")),
        "prefix_padding_ms": int(preset.get("prefix_padding_ms", 200)),
        "silence_duration_ms": int(preset.get("silence_duration_ms", 800)),
    }


def build_vad_runtime_update_message(lod: int) -> str:
    """Build an internal control message injected on LOD transitions."""
    payload = build_vad_runtime_update_payload(lod)
    return (
        "[VAD UPDATE]\n"
        "Internal control sync. Keep this as configuration context only.\n"
        f"- LOD: {payload['lod']}\n"
        f"- start_of_speech_sensitivity: {payload['start_of_speech_sensitivity']}\n"
        f"- end_of_speech_sensitivity: {payload['end_of_speech_sensitivity']}\n"
        f"- prefix_padding_ms: {payload['prefix_padding_ms']}\n"
        f"- silence_duration_ms: {payload['silence_duration_ms']}\n"
        "Do not narrate this block to the user."
    )

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

    _USER_PROFILE_TTL_SEC = 3600.0  # 1 hour

    def __init__(self) -> None:
        self._session_handles: dict[str, str] = {}
        self._session_contexts: dict[str, SessionContext] = {}
        self._user_profiles: dict[str, UserProfile] = {}
        self._user_profile_access_times: dict[str, float] = {}
        self._ephemeral_contexts: dict[str, EphemeralContext] = {}

    # -- RunConfig ----------------------------------------------------------

    # Languages supported by Gemini Live API native audio models.
    # zh-CN/zh-TW are NOT supported; language preference is handled
    # via system instructions in prompt_builder instead.
    _NATIVE_AUDIO_LANGUAGES = {
        "ar-EG", "bn-BD", "nl-NL", "en-IN", "en-US", "fr-FR", "de-DE",
        "hi-IN", "id-ID", "it-IT", "ja-JP", "ko-KR", "mr-IN", "pl-PL",
        "pt-BR", "ro-RO", "ru-RU", "es-ES", "es-US", "ta-IN", "te-IN", "th-TH",
        "tr-TR", "uk-UA", "vi-VN",
    }

    def get_run_config(self, session_id: str, lod: int = 2, language_code: str = "") -> RunConfig:
        """Build a RunConfig for the given session."""
        cached_handle = self._session_handles.get(session_id)

        session_resumption = types.SessionResumptionConfig(
            handle=cached_handle,
        )
        if cached_handle:
            logger.info("Resuming session %s with cached handle", session_id)
        else:
            logger.info("Starting fresh session %s (no cached handle)", session_id)

        vad_preset = get_lod_vad_preset(lod)

        # Only pass language_code if it's supported by the native audio model.
        # Unsupported languages (e.g. zh-CN) are handled via system instructions
        # in prompt_builder.build_user_profile_block() instead.
        effective_lang = None
        if language_code and language_code in self._NATIVE_AUDIO_LANGUAGES:
            effective_lang = language_code

        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=vad_preset["voice_name"],
                    )
                ),
                language_code=effective_lang,
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
                # Server-side VAD disabled: echo residual from speakerphone
                # triggers Gemini's automatic VAD → self-interruption loop.
                # All speech detection is handled client-side (Silero VAD)
                # and forwarded as explicit ActivityStart/End signals.
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=True,
                ),
                activity_handling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
                turn_coverage=types.TurnCoverage.TURN_INCLUDES_ALL_INPUT,
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
            self._user_profile_access_times[user_id] = time.monotonic()
            return self._user_profiles[user_id]

        profile = UserProfile.default()
        profile.user_id = user_id

        db = _get_firestore()
        if db:
            try:
                doc = db.collection("user_profiles").document(user_id).get()
                if doc.exists:
                    profile = UserProfile.from_firestore(doc.to_dict(), user_id=user_id)
                    logger.info("Loaded UserProfile from Firestore for user %s", user_id)
                else:
                    logger.info("No Firestore profile for user %s; using defaults", user_id)
            except Exception:
                logger.exception("Failed to load profile for user %s; using defaults", user_id)

        self._user_profiles[user_id] = profile
        self._user_profile_access_times[user_id] = time.monotonic()
        return profile

    def invalidate_user_profile(self, user_id: str) -> None:
        """Remove cached profile so next load_user_profile fetches fresh data."""
        self._user_profiles.pop(user_id, None)
        self._user_profile_access_times.pop(user_id, None)

    def get_user_profile(self, user_id: str) -> UserProfile:
        """Get cached UserProfile (sync). Use load_user_profile for initial load."""
        if user_id not in self._user_profiles:
            self._user_profiles[user_id] = UserProfile.default()
            self._user_profiles[user_id].user_id = user_id
        self._user_profile_access_times[user_id] = time.monotonic()
        return self._user_profiles[user_id]

    def evict_stale_profiles(self) -> int:
        """Remove cached profiles not accessed within _USER_PROFILE_TTL_SEC.

        Returns the number of evicted profiles.
        """
        now = time.monotonic()
        stale = [
            uid for uid, ts in self._user_profile_access_times.items()
            if (now - ts) > self._USER_PROFILE_TTL_SEC
        ]
        for uid in stale:
            self._user_profiles.pop(uid, None)
            self._user_profile_access_times.pop(uid, None)
        if stale:
            logger.info("Evicted %d stale user profile(s)", len(stale))
        return len(stale)

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
        """Remove all cached state for a session and evict stale profiles."""
        self._session_handles.pop(session_id, None)
        self._session_contexts.pop(session_id, None)
        self._ephemeral_contexts.pop(session_id, None)
        self.evict_stale_profiles()
        logger.debug("Removed session state for %s", session_id)
