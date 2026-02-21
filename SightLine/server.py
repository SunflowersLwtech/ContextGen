"""SightLine backend server.

FastAPI application with WebSocket endpoint for real-time bidirectional
communication between the iOS client and the Gemini Live API via Google ADK.
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
from telemetry.telemetry_parser import parse_telemetry

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

app = FastAPI(title="SightLine Backend", version="0.1.0")

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
    return {"status": "ok", "model": LIVE_MODEL}


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, session_id: str) -> None:
    """Main WebSocket endpoint for bidirectional audio/vision streaming.

    Manages the lifecycle of a Gemini Live API session through the ADK runner,
    forwarding upstream messages from the iOS client and downstream events
    from the model.
    """
    await websocket.accept()
    logger.info("WebSocket connected: user=%s session=%s", user_id, session_id)

    stop_downstream = asyncio.Event()

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
            # The websocket may close between state check and send.
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
            # The websocket may close between state check and send.
            stop_downstream.set()
            return False

    # Notify client immediately so the iOS layer knows the
    # WebSocket is live before the Gemini connection is ready.
    if not await _safe_send_json({"type": "session_ready"}):
        logger.info("WebSocket closed before session_ready: user=%s session=%s", user_id, session_id)
        return

    live_request_queue = LiveRequestQueue()
    run_config = session_manager.get_run_config(session_id)

    # Start the ADK live session
    live_events = runner.run_live(
        session_id=session_id,
        user_id=user_id,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )

    async def _upstream() -> None:
        """Read messages from the iOS client and forward to the Live API.

        Handles 5 upstream message types: audio, image, telemetry,
        activity_start, activity_end.
        """
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("Received non-JSON text message, ignoring")
                    continue

                if message.get("type") == "audio":
                    audio_bytes = base64.b64decode(message["data"])
                    blob = types.Blob(
                        data=audio_bytes,
                        mime_type="audio/pcm;rate=16000",
                    )
                    live_request_queue.send_realtime(blob)

                elif message.get("type") == "image":
                    image_bytes = base64.b64decode(message["data"])
                    mime_type = message.get("mimeType", "image/jpeg")
                    blob = types.Blob(
                        data=image_bytes,
                        mime_type=mime_type,
                    )
                    live_request_queue.send_realtime(blob)

                elif message.get("type") == "telemetry":
                    telemetry_data = message.get("data", {})
                    semantic_text = parse_telemetry(telemetry_data)
                    content = types.Content(
                        parts=[types.Part(text=semantic_text)],
                        role="user",
                    )
                    live_request_queue.send_content(content)

                elif message.get("type") == "activity_start":
                    # Native audio models use automatic VAD; skip explicit
                    # activity signals to avoid 1007 errors.
                    logger.debug("Ignored activity_start (native audio VAD active)")

                elif message.get("type") == "activity_end":
                    logger.debug("Ignored activity_end (native audio VAD active)")

                else:
                    logger.warning("Unknown upstream message type: %s", message.get("type"))

        except WebSocketDisconnect:
            stop_downstream.set()
            logger.info("Client disconnected (upstream): user=%s session=%s", user_id, session_id)
        except Exception:
            stop_downstream.set()
            logger.exception("Error in upstream handler: user=%s session=%s", user_id, session_id)

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
                    # Always notify the client; the first event with
                    # newHandle=None acts as a "connection ready" signal.
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
        logger.info("Session cleaned up: user=%s session=%s", user_id, session_id)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
