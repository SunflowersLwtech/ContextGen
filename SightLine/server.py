"""SightLine backend server.

FastAPI application with WebSocket endpoint for real-time bidirectional
communication between the iOS client and the Gemini Live API via Google ADK.

Phase 3 additions:
- Vision Sub-Agent (async scene analysis with LOD-adaptive prompting)
- OCR Sub-Agent (async text extraction)
- Face recognition pipeline (InsightFace + Firestore face library)
- Function calling tools (navigation, search, face ID)
- Tool behavior strategy (INTERRUPT / WHEN_IDLE / SILENT)
- Firestore UserProfile loading on session start
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
from lod.telemetry_aggregator import TelemetryAggregator
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

app = FastAPI(title="SightLine Backend", version="0.3.0")

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
# Sub-agent & tool imports (lazy to handle missing deps gracefully)
# ---------------------------------------------------------------------------

_vision_available = False
_ocr_available = False
_face_available = False

try:
    from agents.vision_agent import analyze_scene
    _vision_available = True
except ImportError:
    logger.warning("Vision agent not available (missing dependencies)")

try:
    from agents.ocr_agent import extract_text
    _ocr_available = True
except ImportError:
    logger.warning("OCR agent not available (missing dependencies)")

try:
    from agents.face_agent import identify_persons_in_frame
    from tools.face_tools import load_face_library
    _face_available = True
except ImportError:
    logger.warning("Face agent not available (missing dependencies)")

from tools.navigation import NAVIGATION_FUNCTIONS
from tools.search import SEARCH_FUNCTIONS


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    """Health check endpoint for Cloud Run readiness probes."""
    return {
        "status": "ok",
        "model": LIVE_MODEL,
        "phase": 3,
        "capabilities": {
            "vision": _vision_available,
            "ocr": _ocr_available,
            "face": _face_available,
        },
    }


# ---------------------------------------------------------------------------
# Function calling dispatcher
# ---------------------------------------------------------------------------


async def _dispatch_function_call(
    func_name: str,
    func_args: dict,
    session_id: str,
    user_id: str,
) -> dict:
    """Dispatch a function call from Gemini to the appropriate tool.

    Returns the tool result as a dict to be sent back as function response.
    """
    logger.info("Function call: %s(%s)", func_name, func_args)

    # Navigation tools
    if func_name in NAVIGATION_FUNCTIONS:
        func = NAVIGATION_FUNCTIONS[func_name]
        # Inject current GPS/heading from ephemeral context if available
        ephemeral = session_manager.get_ephemeral_context(session_id)
        if func_name == "navigate_to" and ephemeral.gps:
            func_args.setdefault("origin_lat", ephemeral.gps.lat)
            func_args.setdefault("origin_lng", ephemeral.gps.lng)
            func_args.setdefault("user_heading", ephemeral.heading)
        elif func_name in ("get_location_info", "nearby_search", "reverse_geocode") and ephemeral.gps:
            func_args.setdefault("lat", ephemeral.gps.lat)
            func_args.setdefault("lng", ephemeral.gps.lng)
        return func(**func_args)

    # Search tool
    if func_name in SEARCH_FUNCTIONS:
        func = SEARCH_FUNCTIONS[func_name]
        return func(**func_args)

    # Face identification (SILENT behavior)
    if func_name == "identify_person":
        return {"note": "Face identification runs automatically via vision pipeline."}

    logger.warning("Unknown function call: %s", func_name)
    return {"error": f"Unknown function: {func_name}"}


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, session_id: str) -> None:
    """Main WebSocket endpoint for bidirectional audio/vision streaming.

    Manages the lifecycle of a Gemini Live API session through the ADK runner,
    forwarding upstream messages from the iOS client and downstream events
    from the model.

    Phase 3: Integrates sub-agents (vision, OCR, face), function calling
    tools (navigation, search), and Firestore UserProfile loading.
    """
    await websocket.accept()
    logger.info("WebSocket connected: user=%s session=%s", user_id, session_id)

    stop_downstream = asyncio.Event()

    # -- Per-session LOD state -----------------------------------------------
    panic_handler = PanicHandler()
    telemetry_agg = TelemetryAggregator()
    session_ctx = session_manager.get_session_context(session_id)
    user_profile = await session_manager.load_user_profile(user_id)

    # -- Per-session face library cache (Phase 3) ----------------------------
    face_library: list[dict] = []
    if _face_available:
        try:
            face_library = load_face_library(user_id)
            logger.info("Loaded %d face(s) for user %s", len(face_library), user_id)
        except Exception:
            logger.exception("Failed to load face library for user %s", user_id)

    # -- Vision analysis state -----------------------------------------------
    _vision_lock = asyncio.Lock()
    _vision_in_progress = False
    _last_vision_time = 0.0

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
        logger.info("Injected [LOD UPDATE] -> LOD %d (%s)", new_lod, reason)

    async def _notify_ios_lod_change(new_lod: int, reason: str, debug_dict: dict) -> None:
        """Send LOD change notification to iOS client."""
        await _safe_send_json({
            "type": "lod_update",
            "lod": new_lod,
            "reason": reason,
        })
        await _safe_send_json({
            "type": "debug_lod",
            "data": debug_dict,
        })

    async def _handle_panic(ephemeral_ctx) -> None:
        """Handle a new PANIC event: flush TTS, force LOD 1, notify iOS."""
        await _safe_send_json({
            "type": "panic",
            "message": "PANIC detected. Entering safety mode.",
        })

        old_lod = session_ctx.current_lod
        session_ctx.current_lod = 1
        on_lod_change(session_ctx, old_lod, 1)

        panic_reason = "PANIC: safety mode activated"
        await _notify_ios_lod_change(
            1,
            panic_reason,
            {
                "lod": 1,
                "prev": old_lod,
                "reason": panic_reason,
                "rules": ["Rule0:PANIC_flag->LOD1"],
                "panic": True,
            },
        )
        await _send_lod_update(1, ephemeral_ctx, panic_reason)
        logger.warning("PANIC activated for session %s: LOD %d -> 1", session_id, old_lod)

    # -- Sub-agent helpers (Phase 3) -----------------------------------------

    async def _run_vision_analysis(image_base64: str) -> None:
        """Run async vision analysis and inject results into Live session."""
        nonlocal _vision_in_progress
        if not _vision_available:
            return

        async with _vision_lock:
            if _vision_in_progress:
                return
            _vision_in_progress = True

        try:
            ctx_dict = {
                "space_type": session_ctx.space_type,
                "trip_purpose": session_ctx.trip_purpose,
                "active_task": session_ctx.active_task,
                "motion_state": session_manager.get_ephemeral_context(session_id).motion_state,
            }
            result = await analyze_scene(image_base64, session_ctx.current_lod, ctx_dict)

            if result.get("confidence", 0) > 0:
                # Inject vision result into Gemini context
                vision_text = _format_vision_result(result, session_ctx.current_lod)
                content = types.Content(
                    parts=[types.Part(text=vision_text)],
                    role="user",
                )
                live_request_queue.send_content(content)
                logger.info("Injected [VISION ANALYSIS] (LOD %d, confidence %.2f)",
                            session_ctx.current_lod, result.get("confidence", 0))
        except Exception:
            logger.exception("Vision analysis failed")
        finally:
            async with _vision_lock:
                _vision_in_progress = False

    async def _run_face_recognition(image_base64: str) -> None:
        """Run face recognition and inject results as SILENT context."""
        if not _face_available or not face_library:
            return

        try:
            results = identify_persons_in_frame(image_base64, user_id, face_library)
            known = [r for r in results if r["person_name"] != "unknown"]
            if known:
                face_text = _format_face_results(known)
                content = types.Content(
                    parts=[types.Part(text=face_text)],
                    role="user",
                )
                live_request_queue.send_content(content)
                logger.info("Injected [FACE ID]: %s",
                            ", ".join(r["person_name"] for r in known))
        except Exception:
            logger.exception("Face recognition failed")

    async def _run_ocr_analysis(image_base64: str) -> None:
        """Run OCR and inject results into Live session context."""
        if not _ocr_available:
            return

        try:
            # Build context hint from session state
            hint = ""
            if session_ctx.space_type:
                hint = f"User is in a {session_ctx.space_type} environment."
            if session_ctx.active_task:
                hint += f" Currently: {session_ctx.active_task}."

            result = await extract_text(image_base64, context_hint=hint)

            if result.get("confidence", 0) > 0.3 and result.get("text"):
                ocr_text = _format_ocr_result(result)
                content = types.Content(
                    parts=[types.Part(text=ocr_text)],
                    role="user",
                )
                live_request_queue.send_content(content)
                logger.info("Injected [OCR RESULT] (%s, confidence %.2f)",
                            result.get("text_type", "unknown"), result.get("confidence", 0))
        except Exception:
            logger.exception("OCR analysis failed")

    # -- Upstream handler ----------------------------------------------------

    async def _upstream() -> None:
        """Read messages from the iOS client and forward to the Live API.

        Handles upstream message types: audio, image, telemetry,
        activity_start, activity_end, gesture.
        """
        nonlocal _last_vision_time

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
                    # Send raw frame to Gemini Live API
                    live_request_queue.send_realtime(blob)

                    # Phase 3: Trigger async sub-agents on image frames
                    import time as _time
                    now = _time.monotonic()
                    lod = session_ctx.current_lod

                    # Vision analysis: LOD-aware frequency
                    # LOD 1: every 5s, LOD 2: every 3s, LOD 3: every 2s
                    vision_interval = {1: 5.0, 2: 3.0, 3: 2.0}.get(lod, 3.0)
                    if now - _last_vision_time >= vision_interval:
                        _last_vision_time = now
                        image_b64 = message["data"]
                        # Fire-and-forget async tasks
                        asyncio.create_task(_run_vision_analysis(image_b64))

                        # Face recognition: only at LOD 2/3 and if library exists
                        if lod >= 2 and face_library:
                            asyncio.create_task(_run_face_recognition(image_b64))

                        # OCR: only at LOD 3 (detailed mode)
                        if lod == 3:
                            asyncio.create_task(_run_ocr_analysis(image_b64))

                elif msg_type == "telemetry":
                    telemetry_data = message.get("data", {})
                    await _process_telemetry(telemetry_data)

                elif msg_type == "activity_start":
                    logger.debug("Ignored activity_start (native audio VAD active)")

                elif msg_type == "activity_end":
                    logger.debug("Ignored activity_end (native audio VAD active)")

                elif msg_type == "gesture":
                    gesture = message.get("gesture")
                    if gesture in ("lod_up", "lod_down"):
                        ephemeral_ctx = session_manager.get_ephemeral_context(session_id)
                        ephemeral_ctx.user_gesture = gesture
                        await _process_lod_decision(ephemeral_ctx)
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
        """Process a telemetry tick: semantic text + LOD decision."""
        import time as _time

        ephemeral_ctx = parse_telemetry_to_ephemeral(telemetry_data)
        session_manager.update_ephemeral_context(session_id, ephemeral_ctx)

        # Check PANIC first
        is_panic = panic_handler.evaluate(
            heart_rate=ephemeral_ctx.heart_rate,
            panic_flag=ephemeral_ctx.panic,
        )
        if is_panic:
            semantic_text = parse_telemetry(telemetry_data)
            content = types.Content(
                parts=[types.Part(text=semantic_text)],
                role="user",
            )
            live_request_queue.send_content(content)
            await _handle_panic(ephemeral_ctx)
            return

        # Semantic text injection (LOD-aware throttle)
        now = _time.monotonic()
        if telemetry_agg.should_send(now):
            semantic_text = parse_telemetry(telemetry_data)
            content = types.Content(
                parts=[types.Part(text=semantic_text)],
                role="user",
            )
            live_request_queue.send_content(content)
            telemetry_agg.mark_sent(now)

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
            logger.info(
                "LOD transition: %d -> %d (%s) session=%s",
                old_lod, new_lod, decision_log.reason, session_id,
            )

            resume_prompt = on_lod_change(session_ctx, old_lod, new_lod)
            session_ctx.current_lod = new_lod
            telemetry_agg.update_lod(new_lod)

            await _send_lod_update(new_lod, ephemeral_ctx, decision_log.reason)

            if resume_prompt:
                resume_content = types.Content(
                    parts=[types.Part(text=resume_prompt)],
                    role="user",
                )
                live_request_queue.send_content(resume_content)
                logger.info("Injected [RESUME] prompt for session %s", session_id)

            await _notify_ios_lod_change(
                new_lod, decision_log.reason, decision_log.to_debug_dict(),
            )

    # -- Downstream handler --------------------------------------------------

    async def _downstream() -> None:
        """Read events from the Live API and forward to the iOS client.

        Processes session_resumption_update events, transcriptions,
        function calls, and content parts (audio binary / text JSON).
        """
        live_events = await asyncio.to_thread(
            runner.run_live,
            session_id=session_id,
            user_id=user_id,
            live_request_queue=live_request_queue,
            run_config=run_config,
        )
        try:
            async for event in live_events:
                if stop_downstream.is_set():
                    break

                # --- Session resumption update ---
                if event.live_session_resumption_update:
                    update = event.live_session_resumption_update
                    if update.newHandle:
                        session_manager.update_handle(session_id, update.newHandle)
                    if not await _safe_send_json({
                        "type": "session_resumption",
                        "handle": update.newHandle,
                    }):
                        break

                # --- GoAway / connection lifecycle signals ---
                if hasattr(event, "server_content") and event.server_content:
                    sc = event.server_content
                    if hasattr(sc, "interrupted") and sc.interrupted:
                        await _safe_send_json({
                            "type": "interrupted",
                            "message": "Model output was interrupted.",
                        })

                # --- Function calls from Gemini (Phase 3) ---
                if hasattr(event, "actions") and event.actions and event.actions.function_calls:
                    for fc in event.actions.function_calls:
                        result = await _dispatch_function_call(
                            fc.name,
                            dict(fc.args) if fc.args else {},
                            session_id,
                            user_id,
                        )
                        # Send function response back to the model
                        from google.genai.types import FunctionResponse
                        fr = FunctionResponse(
                            name=fc.name,
                            response=result,
                        )
                        content = types.Content(
                            parts=[types.Part(function_response=fr)],
                            role="user",
                        )
                        live_request_queue.send_content(content)
                        logger.info("Sent function response for %s", fc.name)

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
        await asyncio.gather(_upstream(), _downstream())
    except Exception:
        logger.exception("Session error: user=%s session=%s", user_id, session_id)
    finally:
        live_request_queue.close()
        session_manager.remove_session(session_id)
        logger.info("Session cleaned up: user=%s session=%s", user_id, session_id)


# ---------------------------------------------------------------------------
# Sub-agent result formatters
# ---------------------------------------------------------------------------


def _format_vision_result(result: dict, lod: int) -> str:
    """Format vision analysis result for Gemini context injection."""
    parts = ["[VISION ANALYSIS]"]

    warnings = result.get("safety_warnings", [])
    if warnings:
        parts.append("SAFETY WARNINGS: " + "; ".join(warnings))

    nav = result.get("navigation_info", {})
    if lod >= 2:
        entrances = nav.get("entrances", [])
        if entrances:
            parts.append("Entrances: " + ", ".join(entrances))
        paths = nav.get("paths", [])
        if paths:
            parts.append("Paths: " + ", ".join(paths))
        landmarks = nav.get("landmarks", [])
        if landmarks:
            parts.append("Landmarks: " + ", ".join(landmarks))

    desc = result.get("scene_description", "")
    if desc:
        parts.append(f"Scene: {desc}")

    text = result.get("detected_text")
    if text and lod >= 2:
        parts.append(f"Visible text: {text}")

    count = result.get("people_count", 0)
    if count > 0 and lod >= 2:
        parts.append(f"People visible: {count}")

    return "\n".join(parts)


def _format_face_results(known_faces: list[dict]) -> str:
    """Format face recognition results for SILENT context injection."""
    parts = ["[FACE ID]"]
    for face in known_faces:
        name = face["person_name"]
        rel = face.get("relationship", "")
        sim = face.get("similarity", 0)
        position = face.get("bbox", [])
        desc = f"{name}"
        if rel:
            desc += f" ({rel})"
        desc += f" (confidence: {sim:.0%})"
        parts.append(desc)
    return "\n".join(parts)


def _format_ocr_result(result: dict) -> str:
    """Format OCR result for Gemini context injection."""
    parts = ["[OCR RESULT]"]

    text_type = result.get("text_type", "unknown")
    parts.append(f"Type: {text_type}")

    items = result.get("items", [])
    if items:
        parts.append("Items:")
        for item in items:
            parts.append(f"  - {item}")
    else:
        text = result.get("text", "")
        if text:
            parts.append(f"Text: {text}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
