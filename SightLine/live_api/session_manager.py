"""Session manager for SightLine Live API connections.

Manages session state, resumption handles, and RunConfig construction
for the Gemini Live API via Google ADK.
"""

import logging
from typing import Optional

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import types

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages Live API session state and RunConfig construction.

    Tracks session resumption handles so that dropped connections can be
    transparently resumed without losing conversational context.
    """

    def __init__(self) -> None:
        self._session_handles: dict[str, str] = {}

    def get_run_config(self, session_id: str) -> RunConfig:
        """Build a RunConfig for the given session.

        Includes all baseline settings plus session resumption if a
        cached handle exists for this session.

        Args:
            session_id: The session identifier.

        Returns:
            Fully configured RunConfig for runner.run_live().
        """
        cached_handle = self._session_handles.get(session_id)

        session_resumption = types.SessionResumptionConfig(
            handle=cached_handle,
        )
        if cached_handle:
            logger.info("Resuming session %s with cached handle", session_id)
        else:
            logger.info("Starting fresh session %s (no cached handle)", session_id)

        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Aoede"
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
        )

        return run_config

    def update_handle(self, session_id: str, handle: str) -> None:
        """Cache a session resumption handle.

        Args:
            session_id: The session identifier.
            handle: The resumption handle from the server.
        """
        self._session_handles[session_id] = handle
        logger.debug("Cached resumption handle for session %s", session_id)

    def get_handle(self, session_id: str) -> Optional[str]:
        """Retrieve a cached resumption handle.

        Args:
            session_id: The session identifier.

        Returns:
            The cached handle, or None if no handle exists.
        """
        return self._session_handles.get(session_id)

    def remove_session(self, session_id: str) -> None:
        """Remove all cached state for a session.

        Args:
            session_id: The session identifier to clean up.
        """
        self._session_handles.pop(session_id, None)
        logger.debug("Removed session state for %s", session_id)
