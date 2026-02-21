"""SightLine backend server.

FastAPI application with WebSocket endpoint for real-time bidirectional
communication between the iOS client and the Gemini Live API via Google ADK.

Phase 2 additions:
- LOD engine integration (decide_lod on every telemetry tick)
- PANIC handler with TTS flush
- Dynamic system prompt injection via [LOD UPDATE] messages
- Narrative snapshot save/restore on LOD transitions
- LOD debug events for iOS DebugOverlay
"""

import asyncio
import base64
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from starlette.websockets import WebSocketState

from agents.orchestrator import create_orchestrator_agent
from live_api.session_manager import SessionManager
from lod import (
    PanicHandler,
    build_lod_update_message,
    decide_lod,
    on_lod_change,
)
from telemetry.telemetry_parser import parse_telemetry, parse_telemetry_to_ephemeral

# ---------------------------------------------------------------------------
# Environment & logging
# ---------------------------------------------------------------------------

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sightline.server")

# ---------------------------------------------------------------------------
# App globals
# ---------------------------------------------------------------------------

LIVE_MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025")
PORT = int(os.getenv("PORT", "8080"))

app = FastAPI(title="SightLine Backend", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

session_service = InMemorySessionService()
session_manager = SessionManager()

# Create the ADK agent and runner once at module level.
agent = create_orchestrator_agent(model_name=LIVE_MODEL)
runner = Runner(
    agent=agent,
    app_name="sightline",
    session_service=session_service,
    auto_create_session=True,
)

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    """Health check endpoint for Cloud Run readiness probes."""
    return {"status": "ok", "model": LIVE_MODEL, "phase": 2}


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, session_id: str) -> None:
    """Main WebSocket endpoint for bidirectional audio/vision streaming.

    Manages the lifecycle of a Gemini Live API session through the ADK runner,
    forwarding upstream messages from the iOS client and downstream events
    from the model.

    Phase 2: Integrates LOD engine, PANIC handler, and dynamic prompt injection.
    """
    await websocket.accept()
    logger.info("WebSocket connected: user=%s session=%s", user_id, session_id)

    stop_downstream = asyncio.Event()

    # -- Per-session LOD state -----------------------------------------------
    panic_handler = PanicHandler()
    session_ctx = session_manager.get_session_context(session_id)
    user_profile = session_manager.get_user_profile(user_id)

    def _is_websocket_open() -> bool:
        return (
            websocket.client_state == WebSocketState.CONNECTED
            and websocket.application_state == WebSocketState.CONNECTED
        )

    async def _safe_send_json(payload: dict) -> bool:
        if not _is_websocket_open():
            stop_downstream.set()
            return False
        try:
            await websocket.send_json(payload)
            return True
        except (WebSocketDisconnect, RuntimeError):
            stop_downstream.set()
            return False

    async def _safe_send_bytes(payload: bytes) -> bool:
        if not _is_websocket_open():
            stop_downstream.set()
            return False
        try:
            await websocket.send_bytes(payload)
            return True
        except (WebSocketDisconnect, RuntimeError):
            stop_downstream.set()
            return False

    # Notify client immediately so the iOS layer knows the
    # WebSocket is live before the Gemini connection is ready.
    if not await _safe_send_json({"type": "session_ready"}):
        logger.info("WebSocket closed before session_ready: user=%s session=%s", user_id, session_id)
        return

    live_request_queue = LiveRequestQueue()
    run_config = session_manager.get_run_config(session_id, lod=session_ctx.current_lod)

    # Start the ADK live session
    live_events = runner.run_live(
        session_id=session_id,
        user_id=user_id,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )

    # -- LOD engine helpers --------------------------------------------------

    async def _send_lod_update(
        new_lod: int,
        ephemeral_ctx,
        reason: str,
    ) -> None:
        """Build and inject a [LOD UPDATE] message into the Live session."""
        lod_message = build_lod_update_message(
            lod=new_lod,
            ephemeral=ephemeral_ctx,
            session=session_ctx,
            profile=user_profile,
            reason=reason,
        )
        content = types.Content(
            parts=[types.Part(text=lod_message)],
            role="user",
        )
        live_request_queue.send_content(content)
        logger.info("Injected [LOD UPDATE] → LOD %d (%s)", new_lod, reason)

    async def _notify_ios_lod_change(new_lod: int, reason: str, debug_dict: dict) -> None:
        """Send LOD change notification to iOS client."""
        await _safe_send_json({
            "type": "lodUpdate",
            "lod": new_lod,
            "reason": reason,
        })
        # Debug overlay event (separate message for optional consumption)
        await _safe_send_json({
            "type": "debug_lod",
            **debug_dict,
        })

    async def _handle_panic(ephemeral_ctx) -> None:
        """Handle a new PANIC event: flush TTS, force LOD 1, notify iOS."""
        # Notify iOS to flush audio queue and enter PANIC mode
        await _safe_send_json({
            "type": "panic",
            "message": "PANIC detected. Entering safety mode.",
        })

        # Force LOD 1 in session context
        old_lod = session_ctx.current_lod
        session_ctx.current_lod = 1

        # Handle narrative snapshot on LOD downgrade
        on_lod_change(session_ctx, old_lod, 1)

        # Inject PANIC-level LOD update into Live session
        await _send_lod_update(1, ephemeral_ctx, "PANIC: safety mode activated")

        logger.warning(
            "PANIC activated for session %s: LOD %d → 1",
            session_id,
            old_lod,
        )

    # -- Upstream handler ----------------------------------------------------

    async def _upstream() -> None:
        """Read messages from the iOS client and forward to the Live API.

        Handles upstream message types: audio, image, telemetry,
        activity_start, activity_end, gesture.
        """
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("Received non-JSON text message, ignoring")
                    continue

                msg_type = message.get("type")

                if msg_type == "audio":
                    audio_bytes = base64.b64decode(message["data"])
                    blob = types.Blob(
                        data=audio_bytes,
                        mime_type="audio/pcm;rate=16000",
                    )
                    live_request_queue.send_realtime(blob)

                elif msg_type == "image":
                    image_bytes = base64.b64decode(message["data"])
                    mime_type = message.get("mimeType", "image/jpeg")
                    blob = types.Blob(
                        data=image_bytes,
                        mime_type=mime_type,
                    )
                    live_request_queue.send_realtime(blob)

                elif msg_type == "telemetry":
                    telemetry_data = message.get("data", {})
                    await _process_telemetry(telemetry_data)

                elif msg_type == "activity_start":
                    # Native audio models use automatic VAD; skip explicit
                    # activity signals to avoid 1007 errors.
                    logger.debug("Ignored activity_start (native audio VAD active)")

                elif msg_type == "activity_end":
                    logger.debug("Ignored activity_end (native audio VAD active)")

                elif msg_type == "gesture":
                    # Direct LOD gesture from iOS (lod_up / lod_down)
                    gesture = message.get("gesture")
                    if gesture in ("lod_up", "lod_down"):
                        ephemeral_ctx = session_manager.get_ephemeral_context(session_id)
                        ephemeral_ctx.user_gesture = gesture
                        await _process_lod_decision(ephemeral_ctx)
                        # Clear gesture after processing
                        ephemeral_ctx.user_gesture = None
                        session_manager.update_ephemeral_context(session_id, ephemeral_ctx)

                else:
                    logger.warning("Unknown upstream message type: %s", msg_type)

        except WebSocketDisconnect:
            stop_downstream.set()
            logger.info("Client disconnected (upstream): user=%s session=%s", user_id, session_id)
        except Exception:
            stop_downstream.set()
            logger.exception("Error in upstream handler: user=%s session=%s", user_id, session_id)

    # -- Telemetry processing ------------------------------------------------

    async def _process_telemetry(telemetry_data: dict) -> None:
        """Process a telemetry tick: semantic text + LOD decision.

        Dual-path processing:
        1. Parse into semantic text → inject as [TELEMETRY UPDATE] for Gemini
        2. Parse into EphemeralContext → run LOD decision engine
        """
        # Path 1: Semantic text for Gemini context
        semantic_text = parse_telemetry(telemetry_data)
        content = types.Content(
            parts=[types.Part(text=semantic_text)],
            role="user",
        )
        live_request_queue.send_content(content)

        # Path 2: EphemeralContext for LOD engine
        ephemeral_ctx = parse_telemetry_to_ephemeral(telemetry_data)
        session_manager.update_ephemeral_context(session_id, ephemeral_ctx)

        # Check PANIC first (takes absolute priority)
        is_panic = panic_handler.evaluate(
            heart_rate=ephemeral_ctx.heart_rate,
            panic_flag=ephemeral_ctx.panic,
        )
        if is_panic:
            await _handle_panic(ephemeral_ctx)
            return  # PANIC overrides normal LOD processing

        # Run LOD decision
        await _process_lod_decision(ephemeral_ctx)

    async def _process_lod_decision(ephemeral_ctx) -> None:
        """Run the LOD decision engine and handle transitions."""
        new_lod, decision_log = decide_lod(
            ephemeral=ephemeral_ctx,
            session=session_ctx,
            profile=user_profile,
        )

        old_lod = session_ctx.current_lod

        if new_lod != old_lod:
            # LOD changed — handle transition
            logger.info(
                "LOD transition: %d → %d (%s) session=%s",
                old_lod,
                new_lod,
                decision_log.reason,
                session_id,
            )

            # Handle narrative snapshot (save on downgrade, restore on upgrade)
            resume_prompt = on_lod_change(session_ctx, old_lod, new_lod)

            # Update session state
            session_ctx.current_lod = new_lod

            # Inject [LOD UPDATE] into Live session
            await _send_lod_update(new_lod, ephemeral_ctx, decision_log.reason)

            # If there's a resume prompt from narrative snapshot, inject it
            if resume_prompt:
                resume_content = types.Content(
                    parts=[types.Part(text=resume_prompt)],
                    role="user",
                )
                live_request_queue.send_content(resume_content)
                logger.info("Injected [RESUME] prompt for session %s", session_id)

            # Notify iOS client of LOD change
            await _notify_ios_lod_change(
                new_lod,
                decision_log.reason,
                decision_log.to_debug_dict(),
            )

    # -- Downstream handler --------------------------------------------------

    async def _downstream() -> None:
        """Read events from the Live API and forward to the iOS client.

        Processes session_resumption_update events, transcriptions, and
        content parts (audio binary / text JSON).
        """
        try:
            async for event in live_events:
                if stop_downstream.is_set():
                    break

                # --- Session resumption update (cache handle for reconnection) ---
                if event.live_session_resumption_update:
                    update = event.live_session_resumption_update
                    if update.newHandle:
                        session_manager.update_handle(session_id, update.newHandle)
                    if not await _safe_send_json({
                        "type": "session_resumption",
                        "handle": update.newHandle,
                    }):
                        break

                # --- Input transcription (user speech-to-text) ---
                if event.input_transcription and event.input_transcription.text:
                    if not await _safe_send_json({
                        "type": "transcript",
                        "text": event.input_transcription.text,
                        "role": "user",
                    }):
                        break

                # --- Output transcription (agent speech-to-text) ---
                if event.output_transcription and event.output_transcription.text:
                    if not await _safe_send_json({
                        "type": "transcript",
                        "text": event.output_transcription.text,
                        "role": "agent",
                    }):
                        break

                # --- Content parts (audio / text) ---
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if stop_downstream.is_set():
                            break

                        if part.inline_data and part.inline_data.data:
                            # Audio data - send as binary bytes to iOS
                            audio_data = part.inline_data.data
                            if isinstance(audio_data, str):
                                audio_data = base64.b64decode(audio_data)
                            if not await _safe_send_bytes(audio_data):
                                break

                        elif part.text:
                            if not await _safe_send_json({
                                "type": "transcript",
                                "text": part.text,
                                "role": "agent",
                            }):
                                break

                    if stop_downstream.is_set():
                        break

        except WebSocketDisconnect:
            stop_downstream.set()
            logger.info("Client disconnected (downstream): user=%s session=%s", user_id, session_id)
        except Exception:
            logger.exception("Error in downstream handler: user=%s session=%s", user_id, session_id)

    try:
        # Run upstream and downstream concurrently
        await asyncio.gather(_upstream(), _downstream())
    except Exception:
        logger.exception("Session error: user=%s session=%s", user_id, session_id)
    finally:
        live_request_queue.close()
        session_manager.remove_session(session_id)
        logger.info("Session cleaned up: user=%s session=%s", user_id, session_id)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
