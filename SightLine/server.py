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
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.runners import Runner
from google.genai import types
from starlette.websockets import WebSocketState

from agents.orchestrator import create_orchestrator_agent
from live_api.session_manager import (
    SessionManager,
    build_vad_runtime_update_message,
    build_vad_runtime_update_payload,
    create_session_service,
    supports_runtime_vad_reconfiguration,
)
from lod import (
    PanicHandler,
    build_full_dynamic_prompt,
    build_lod_update_message,
    decide_lod,
    on_lod_change,
)
from lod.lod_engine import should_speak
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

session_service = create_session_service()
session_manager = SessionManager()

# Create the ADK agent and runner once at module level.
agent = create_orchestrator_agent(model_name=LIVE_MODEL)
runner = Runner(
    agent=agent,
    app_name="sightline",
    session_service=session_service,
    auto_create_session=True,
)


def _coerce_bool(value: object, default: bool = False) -> bool:
    """Parse bool-like JSON values safely for request handling."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return value != 0
    return default


TELEMETRY_FORCE_REFRESH_SEC = 60.0
AGENT_TEXT_REPEAT_SUPPRESS_SEC = 14.0
VISION_REPEAT_SUPPRESS_SEC = 18.0
VISION_SAFETY_REPEAT_SUPPRESS_SEC = 6.0
OCR_REPEAT_SUPPRESS_SEC = 20.0
OCR_SAFETY_REPEAT_SUPPRESS_SEC = 8.0
VISION_PREFEEDBACK_COOLDOWN_SEC = 12.0
OCR_PREFEEDBACK_COOLDOWN_SEC = 15.0

_MEANINGFUL_TELEMETRY_FIELDS = {
    "motion_state",
    "hr_bucket",
    "noise_bucket",
    "cadence_bucket",
    "heading_bucket",
    "gps_bucket",
    "device_type",
}


def _normalize_text_for_dedupe(text: str) -> str:
    """Normalize free text for repeat suppression checks."""
    lowered = (text or "").strip().lower()
    if not lowered:
        return ""
    compact = re.sub(r"\s+", " ", lowered)
    compact = re.sub(r"[^\w\s]", "", compact, flags=re.UNICODE)
    return compact.strip()


def _is_repeated_text(
    text: str,
    *,
    previous_text: str,
    now_ts: float,
    previous_ts: float,
    cooldown_sec: float,
    min_chars: int = 20,
) -> bool:
    """Return True when the same meaningful text repeats inside cooldown."""
    if not previous_text:
        return False
    if now_ts < previous_ts:
        return False
    normalized = _normalize_text_for_dedupe(text)
    previous_normalized = _normalize_text_for_dedupe(previous_text)
    if len(normalized) < min_chars or len(previous_normalized) < min_chars:
        return False
    if normalized != previous_normalized:
        return False
    return (now_ts - previous_ts) < cooldown_sec


def _heart_rate_bucket(heart_rate: float | None) -> str:
    if heart_rate is None or heart_rate <= 0:
        return "unknown"
    if heart_rate > 120:
        return "panic"
    if heart_rate > 100:
        return "elevated"
    return "normal"


def _noise_bucket(noise_db: float) -> str:
    if noise_db < 40:
        return "quiet"
    if noise_db < 65:
        return "moderate"
    if noise_db < 80:
        return "noisy"
    return "very_loud"


def _cadence_bucket(step_cadence: float) -> str:
    if step_cadence <= 0:
        return "still"
    if step_cadence < 60:
        return "slow"
    if step_cadence < 120:
        return "walk"
    return "fast"


def _heading_bucket(heading: float | None) -> int | None:
    if heading is None:
        return None
    return int((heading % 360) // 30)


def _gps_bucket(gps) -> tuple[float, float] | None:
    if gps is None:
        return None
    try:
        return (round(float(gps.lat), 3), round(float(gps.lng), 3))
    except (TypeError, ValueError, AttributeError):
        return None


def _build_telemetry_signature(ephemeral_ctx) -> dict[str, object]:
    """Build coarse signature to detect meaningful telemetry changes."""
    heading_value = getattr(ephemeral_ctx, "heading", None)
    heading_bucket = _heading_bucket(heading_value if heading_value not in (None, 0.0) else None)
    return {
        "motion_state": getattr(ephemeral_ctx, "motion_state", "unknown"),
        "hr_bucket": _heart_rate_bucket(getattr(ephemeral_ctx, "heart_rate", None)),
        "noise_bucket": _noise_bucket(float(getattr(ephemeral_ctx, "ambient_noise_db", 50.0) or 50.0)),
        "cadence_bucket": _cadence_bucket(float(getattr(ephemeral_ctx, "step_cadence", 0.0) or 0.0)),
        "heading_bucket": heading_bucket,
        "gps_bucket": _gps_bucket(getattr(ephemeral_ctx, "gps", None)),
        "time_context": getattr(ephemeral_ctx, "time_context", "unknown"),
        "device_type": getattr(ephemeral_ctx, "device_type", "phone_only"),
    }


def _changed_signature_fields(
    previous_signature: dict[str, object] | None,
    current_signature: dict[str, object],
) -> list[str]:
    if previous_signature is None:
        return ["initial"]
    changed: list[str] = []
    for key, value in current_signature.items():
        if previous_signature.get(key) != value:
            changed.append(key)
    return changed


def _should_inject_telemetry_context(
    *,
    previous_signature: dict[str, object] | None,
    current_signature: dict[str, object],
    last_injected_ts: float,
    now_ts: float,
    force_refresh_sec: float = TELEMETRY_FORCE_REFRESH_SEC,
) -> tuple[bool, list[str]]:
    """Decide if telemetry context should be injected into the model."""
    changed = _changed_signature_fields(previous_signature, current_signature)
    if previous_signature is None:
        return True, changed

    meaningful_change = [field for field in changed if field in _MEANINGFUL_TELEMETRY_FIELDS]
    if meaningful_change:
        return True, meaningful_change

    if now_ts - last_injected_ts >= force_refresh_sec:
        return True, ["periodic_refresh"]

    return False, changed

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

FACE_LIBRARY_REFRESH_SEC: float = 60.0

from tools import ALL_FUNCTIONS
from tools.navigation import NAVIGATION_FUNCTIONS
from tools.search import SEARCH_FUNCTIONS
from memory.memory_tools import MEMORY_FUNCTIONS
from tools.tool_behavior import ToolBehavior, behavior_to_text, resolve_tool_behavior

# ---------------------------------------------------------------------------
# Memory system (Phase 4, SL-71)
# ---------------------------------------------------------------------------

_memory_available = False
_memory_extractor_available = False
try:
    from memory.memory_bank import load_relevant_memories, MemoryBankService
    from memory.memory_budget import MemoryBudgetTracker, MEMORY_WRITE_BUDGET
    _memory_available = True
except ImportError:
    logger.warning("Memory module not available")

    def load_relevant_memories(user_id: str, context: str, top_k: int = 3) -> list[str]:
        return []

try:
    from memory.memory_extractor import MemoryExtractor
    _memory_extractor_available = True
except ImportError:
    logger.warning("Memory extractor not available")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    """Health check endpoint for Cloud Run readiness probes."""
    return {
        "status": "ok",
        "model": LIVE_MODEL,
        "phase": 4,
        "capabilities": {
            "vision": _vision_available,
            "ocr": _ocr_available,
            "face": _face_available,
        },
    }


# ---------------------------------------------------------------------------
# REST API — Face Registration (Phase 5, SL-P2-①)
# ---------------------------------------------------------------------------


@app.post("/api/face/register")
async def api_register_face(request: Request) -> JSONResponse:
    """Register a face via REST (for iOS FaceRegistrationView).

    Body JSON:
        user_id: str
        person_name: str
        relationship: str
        image_base64: str  (JPEG base64-encoded)
        photo_index: int (optional, default 0)
        consent_confirmed: bool (optional, default false)
        store_reference_photo: bool (optional, default false)

    Returns the face_id and metadata on success.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    user_id = body.get("user_id")
    person_name = body.get("person_name")
    relationship = body.get("relationship", "")
    image_base64 = body.get("image_base64")
    photo_index = body.get("photo_index", 0)
    consent_confirmed = _coerce_bool(body.get("consent_confirmed"), default=False)
    store_reference_photo = _coerce_bool(body.get("store_reference_photo"), default=False)

    if not all([user_id, person_name, image_base64]):
        return JSONResponse(
            {"error": "Missing required fields: user_id, person_name, image_base64"},
            status_code=400,
        )

    if store_reference_photo and not consent_confirmed:
        return JSONResponse(
            {"error": "consent_confirmed must be true when store_reference_photo is enabled"},
            status_code=400,
        )

    if not _face_available:
        return JSONResponse(
            {"error": "Face recognition is not available on this server"},
            status_code=503,
        )

    try:
        from tools.face_tools import register_face
        result = await asyncio.to_thread(
            register_face,
            user_id=user_id,
            person_name=person_name,
            relationship=relationship,
            image_base64=image_base64,
            photo_index=photo_index,
            consent_confirmed=consent_confirmed,
            store_reference_photo=store_reference_photo,
        )
        logger.info("REST face register: %s for user %s", result.get("face_id"), user_id)
        return JSONResponse(result, status_code=201)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=422)
    except Exception as e:
        logger.exception("Face registration failed")
        return JSONResponse({"error": f"Registration failed: {str(e)}"}, status_code=500)


@app.get("/api/face/list/{user_id}")
async def api_list_faces(user_id: str) -> JSONResponse:
    """List all registered faces for a user (without embeddings)."""
    if not _face_available:
        return JSONResponse({"error": "Face recognition not available"}, status_code=503)

    try:
        from tools.face_tools import list_faces
        faces = await asyncio.to_thread(list_faces, user_id)
        return JSONResponse({"faces": faces, "count": len(faces)})
    except Exception as e:
        logger.exception("List faces failed for user %s", user_id)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/face/{user_id}/{face_id}")
async def api_delete_face(user_id: str, face_id: str) -> JSONResponse:
    """Delete a single face entry from the library."""
    if not _face_available:
        return JSONResponse({"error": "Face recognition not available"}, status_code=503)

    try:
        from tools.face_tools import delete_face
        deleted = await asyncio.to_thread(delete_face, user_id, face_id)
        if deleted:
            return JSONResponse({"status": "deleted", "face_id": face_id})
        return JSONResponse({"error": "Face not found"}, status_code=404)
    except Exception as e:
        logger.exception("Delete face failed")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/face/{user_id}")
async def api_clear_face_library(user_id: str) -> JSONResponse:
    """Clear all faces in the user's library."""
    if not _face_available:
        return JSONResponse({"error": "Face recognition not available"}, status_code=503)

    try:
        from tools.face_tools import clear_face_library
        count = await asyncio.to_thread(clear_face_library, user_id)
        return JSONResponse({"status": "cleared", "deleted_count": count})
    except Exception as e:
        logger.exception("Clear face library failed")
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# REST API — User Profile (Phase 5, SL-P2-③)
# ---------------------------------------------------------------------------


@app.get("/api/profile/{user_id}")
async def api_get_profile(user_id: str) -> JSONResponse:
    """Get the UserProfile from Firestore."""
    try:
        from google.cloud import firestore as _fs
        db = _fs.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT", "sightline-hackathon"))
        doc = db.collection("users").document(user_id).get()
        if not doc.exists:
            return JSONResponse({"error": "Profile not found"}, status_code=404)
        data = doc.to_dict()
        # Convert timestamps to ISO strings
        for key in ("created_at", "updated_at"):
            if key in data and hasattr(data[key], "isoformat"):
                data[key] = data[key].isoformat()
        return JSONResponse(data)
    except Exception as e:
        logger.exception("Get profile failed for %s", user_id)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/profile/{user_id}")
async def api_save_profile(user_id: str, request: Request) -> JSONResponse:
    """Create or update a UserProfile in Firestore.

    Body JSON — any of:
        vision_status: str (totally_blind / low_vision)
        blindness_onset: str (congenital / acquired)
        onset_age: int | null
        has_guide_dog: bool
        has_white_cane: bool
        tts_speed: float
        verbosity_preference: str (concise / detailed)
        language: str
        description_priority: str (spatial / object)
        color_description: bool
        om_level: str (beginner / intermediate / advanced)
        travel_frequency: str (daily / weekly / rarely)
        preferred_name: str
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    ALLOWED_FIELDS = {
        "vision_status", "blindness_onset", "onset_age",
        "has_guide_dog", "has_white_cane", "tts_speed",
        "verbosity_preference", "language", "description_priority",
        "color_description", "om_level", "travel_frequency", "preferred_name",
    }
    filtered = {k: v for k, v in body.items() if k in ALLOWED_FIELDS}
    if not filtered:
        return JSONResponse({"error": "No valid fields provided"}, status_code=400)

    try:
        from google.cloud import firestore as _fs
        db = _fs.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT", "sightline-hackathon"))
        doc_ref = db.collection("users").document(user_id)
        filtered["updated_at"] = _fs.SERVER_TIMESTAMP
        # Merge so we don't overwrite fields not included in this request
        doc_ref.set(filtered, merge=True)
        logger.info("REST profile save for user %s: %s", user_id, list(filtered.keys()))
        return JSONResponse({"status": "saved", "user_id": user_id, "fields": list(filtered.keys())})
    except Exception as e:
        logger.exception("Save profile failed for %s", user_id)
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# User list endpoint (for demo user switching)
# ---------------------------------------------------------------------------


@app.get("/api/users")
async def api_list_users() -> JSONResponse:
    """List all user IDs from Firestore."""
    try:
        from google.cloud import firestore as _fs
        db = _fs.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT", "sightline-hackathon"))
        docs = db.collection("users").stream()
        user_ids = sorted(doc.id for doc in docs)
        return JSONResponse({"users": user_ids, "count": len(user_ids)})
    except Exception as e:
        logger.exception("List users failed")
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Voice intent detection (detail / stop flags for LOD engine)
# ---------------------------------------------------------------------------

_DETAIL_PHRASES = {"tell me more", "more detail", "describe more", "what else", "elaborate"}
_STOP_PHRASES = {"stop", "be quiet", "shut up", "enough", "stop talking", "quiet"}


def _detect_voice_intent(text: str) -> str | None:
    """Detect user intent from transcribed speech for LOD flag setting."""
    lower = text.strip().lower()
    for phrase in _DETAIL_PHRASES:
        if phrase in lower:
            return "detail"
    for phrase in _STOP_PHRASES:
        if phrase in lower:
            return "stop"
    return None


# ---------------------------------------------------------------------------
# Function calling dispatcher
# ---------------------------------------------------------------------------


def _json_safe(value):
    """Best-effort conversion for JSON payloads sent over WebSocket."""
    try:
        json.dumps(value)
        return value
    except TypeError:
        return json.loads(json.dumps(value, default=str))


def _extract_function_calls(event) -> list:
    """Extract function calls from ADK event objects across SDK schema changes."""
    getter = getattr(event, "get_function_calls", None)
    if callable(getter):
        try:
            calls = getter() or []
            if calls:
                return list(calls)
        except Exception:
            logger.debug("event.get_function_calls() failed; trying legacy access path", exc_info=True)

    # Legacy fallback (older assumptions in downstream loop).
    actions = getattr(event, "actions", None)
    if not actions:
        return []
    legacy_calls = getattr(actions, "function_calls", None)
    if not legacy_calls:
        return []
    return list(legacy_calls)


async def _dispatch_function_call(
    func_name: str,
    func_args: dict,
    session_id: str,
    user_id: str,
) -> dict:
    """Dispatch a function call from Gemini to the appropriate tool.

    Uses the unified ALL_FUNCTIONS dict for dispatch.  Navigation tools
    get automatic GPS/heading injection from ephemeral context.

    Returns the tool result as a dict to be sent back as function response.
    """
    logger.info("Function call: %s(%s)", func_name, func_args)

    if func_name not in ALL_FUNCTIONS:
        logger.warning("Unknown function call: %s", func_name)
        return {"error": f"Unknown function: {func_name}"}

    # Navigation tools: inject current GPS/heading from ephemeral context
    if func_name in NAVIGATION_FUNCTIONS:
        ephemeral = session_manager.get_ephemeral_context(session_id)
        if func_name == "navigate_to" and ephemeral.gps:
            func_args.setdefault("origin_lat", ephemeral.gps.lat)
            func_args.setdefault("origin_lng", ephemeral.gps.lng)
            func_args.setdefault("user_heading", ephemeral.heading)
        elif func_name in ("get_location_info", "nearby_search", "reverse_geocode") and ephemeral.gps:
            func_args.setdefault("lat", ephemeral.gps.lat)
            func_args.setdefault("lng", ephemeral.gps.lng)

    # Memory tools: hard-set user_id from session (security: prevents cross-user access)
    if func_name in MEMORY_FUNCTIONS:
        func_args["user_id"] = user_id

    return await asyncio.to_thread(ALL_FUNCTIONS[func_name], **func_args)


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
    raw_session_id = session_id
    session_id = session_id.strip().lower()
    if session_id != raw_session_id:
        logger.info(
            "Normalized session id for backend compatibility: %s -> %s",
            raw_session_id,
            session_id,
        )
    logger.info("WebSocket connected: user=%s session=%s", user_id, session_id)

    stop_downstream = asyncio.Event()
    resume_handle = (websocket.query_params.get("resume_handle") or "").strip()
    if resume_handle:
        session_manager.update_handle(session_id, resume_handle)
        logger.info("Received resume handle from client for session %s", session_id)

    # -- Per-session LOD state -----------------------------------------------
    panic_handler = PanicHandler()
    telemetry_agg = TelemetryAggregator()
    session_ctx = session_manager.get_session_context(session_id)
    user_profile = await session_manager.load_user_profile(user_id)

    # -- Per-session face library cache (Phase 3) ----------------------------
    face_library: list[dict] = []
    _face_library_loaded_at: float = 0.0
    if _face_available:
        try:
            face_library = load_face_library(user_id)
            _face_library_loaded_at = time.monotonic()
            logger.info("Loaded %d face(s) for user %s", len(face_library), user_id)
        except Exception:
            logger.exception("Failed to load face library for user %s", user_id)

    # -- Vision analysis state -----------------------------------------------
    _vision_lock = asyncio.Lock()
    _vision_in_progress = False
    _last_vision_time = 0.0
    _frame_seq = 0
    _is_client_muted = False
    _last_vision_context_text = ""
    _last_vision_context_sent_at = 0.0
    _last_vision_prefeedback_at = 0.0
    _last_ocr_context_text = ""
    _last_ocr_context_sent_at = 0.0
    _last_ocr_prefeedback_at = 0.0
    _last_telemetry_signature: dict[str, object] | None = None
    _last_telemetry_context_sent_at = 0.0
    _last_agent_text = ""
    _last_agent_text_sent_at = 0.0
    _allow_agent_repeat_until = 0.0

    # Echo detection state (P0_FIX_3)
    _recent_agent_texts: list[tuple[float, str]] = []

    # Model audio staleness for injection suppression (P2_FIX_3)
    _model_audio_last_seen_at: float = 0.0
    _MODEL_AUDIO_STALENESS_SEC = 2.0

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

    async def _forward_agent_transcript(text: str) -> bool:
        """Forward agent transcript with short-window duplicate suppression."""
        nonlocal _last_agent_text, _last_agent_text_sent_at
        now_mono = time.monotonic()
        can_repeat = now_mono <= _allow_agent_repeat_until
        is_repeat = _is_repeated_text(
            text,
            previous_text=_last_agent_text,
            now_ts=now_mono,
            previous_ts=_last_agent_text_sent_at,
            cooldown_sec=AGENT_TEXT_REPEAT_SUPPRESS_SEC,
        )
        if is_repeat and not can_repeat:
            logger.debug("Suppressed repeated downstream transcript: %s", text[:120])
            return True
        sent = await _safe_send_json({
            "type": "transcript",
            "text": text,
            "role": "agent",
        })
        if sent:
            _last_agent_text = text
            _last_agent_text_sent_at = now_mono
        return sent

    def _is_likely_echo(candidate: str, now_ts: float) -> bool:
        """Check if candidate text is likely an echo of recent agent output.

        Uses Jaccard word similarity >0.6 within a 5s window. Requires
        at least 3 words in candidate to avoid false positives on short
        utterances like "yes" or "what?".
        """
        words_candidate = set(candidate.lower().split())
        if len(words_candidate) < 3:
            return False
        cutoff = now_ts - 5.0
        for ts, agent_text in reversed(_recent_agent_texts):
            if ts < cutoff:
                break
            words_agent = set(agent_text.lower().split())
            if not words_agent:
                continue
            intersection = words_candidate & words_agent
            union = words_candidate | words_agent
            jaccard = len(intersection) / len(union) if union else 0.0
            if jaccard > 0.6:
                return True
        return False

    async def _emit_tool_event(
        tool: str,
        behavior: ToolBehavior | str,
        *,
        status: str,
        data: dict | None = None,
    ) -> None:
        payload: dict = {
            "type": "tool_event",
            "tool": tool,
            "behavior": behavior_to_text(behavior),
            "status": status,
        }
        if data:
            payload["data"] = _json_safe(data)
        await _safe_send_json(payload)

    async def _emit_capability_degraded(
        capability: str,
        reason: str,
        recoverable: bool = True,
    ) -> None:
        """Notify iOS client that a sub-agent capability is degraded."""
        await _safe_send_json({
            "type": "capability_degraded",
            "capability": capability,
            "reason": reason,
            "recoverable": recoverable,
        })

    async def _emit_identity_event(
        *,
        person_name: str,
        matched: bool,
        similarity: float = 0.0,
        source: str = "face_pipeline",
    ) -> None:
        payload = {
            "type": "identity_update",
            "person_name": person_name,
            "matched": matched,
            "similarity": similarity,
            "source": source,
            "behavior": behavior_to_text(ToolBehavior.SILENT),
        }
        await _safe_send_json(payload)
        if matched:
            await _safe_send_json({
                "type": "person_identified",
                "person_name": person_name,
                "similarity": similarity,
                "source": source,
                "behavior": behavior_to_text(ToolBehavior.SILENT),
            })

    # Notify client immediately so the iOS layer knows the
    # WebSocket is live before the Gemini connection is ready.
    if not await _safe_send_json({"type": "session_ready"}):
        logger.info("WebSocket closed before session_ready: user=%s session=%s", user_id, session_id)
        return

    live_request_queue = LiveRequestQueue()
    run_config = session_manager.get_run_config(session_id, lod=session_ctx.current_lod)

    # -- E-7: Initial LOD context injection at session start -----------------
    # Inject the full dynamic system prompt so the model has LOD context
    # immediately, rather than waiting for the first telemetry tick.
    _initial_ephemeral = session_manager.get_ephemeral_context(session_id)
    _initial_memories = load_relevant_memories(
        user_id,
        session_ctx.active_task or session_ctx.trip_purpose or "",
        top_k=3,
    )
    _initial_prompt = build_full_dynamic_prompt(
        lod=session_ctx.current_lod,
        profile=user_profile,
        ephemeral_semantic="",
        session=session_ctx,
        memories=_initial_memories if _initial_memories else None,
    )
    _initial_content = types.Content(
        parts=[types.Part(text=_initial_prompt)],
        role="user",
    )
    live_request_queue.send_content(_initial_content)
    logger.info(
        "Injected initial full dynamic prompt (LOD %d) for session %s",
        session_ctx.current_lod, session_id,
    )

    # -- Greeting prompt: Gemini speaks first so the user knows the app is ready --
    _greeting_parts: list[str] = [
        "[SESSION START] Greet the user briefly (1-2 sentences).",
        "Let them know you're ready to help.",
    ]
    if user_profile and user_profile.preferred_name:
        _greeting_parts.append(
            f"Address them as '{user_profile.preferred_name}'."
        )
    _greeting_parts.append(
        "Mention that the camera is off and they can swipe sideways to turn it on "
        "when they need visual assistance. Keep the greeting warm and concise."
    )
    _greeting_content = types.Content(
        parts=[types.Part(text=" ".join(_greeting_parts))],
        role="user",
    )
    live_request_queue.send_content(_greeting_content)
    logger.info("Injected greeting prompt for session %s", session_id)

    # -- Track client camera state for context injection ----------------------
    _client_camera_active = False

    # -- LOD engine helpers --------------------------------------------------

    async def _send_lod_update(
        new_lod: int,
        ephemeral_ctx,
        reason: str,
    ) -> None:
        """Build and inject a [LOD UPDATE] message into the Live session."""
        # SL-71: Preload relevant memories for prompt injection
        memories = await _load_session_memories(
            context_hint=session_ctx.active_task or session_ctx.trip_purpose or ""
        )
        lod_message = build_lod_update_message(
            lod=new_lod,
            ephemeral=ephemeral_ctx,
            session=session_ctx,
            profile=user_profile,
            reason=reason,
            memories=memories,
        )
        content = types.Content(
            parts=[types.Part(text=lod_message)],
            role="user",
        )
        live_request_queue.send_content(content)
        logger.info("Injected [LOD UPDATE] -> LOD %d (%s)", new_lod, reason)

    # -- Per-session memory state (Phase 4) -----------------------------------
    memory_top3: list[str] = []
    memory_top3_detailed: list[dict] = []
    memory_budget = MemoryBudgetTracker() if _memory_available else None
    transcript_history: list[dict] = []

    async def _load_session_memories(context_hint: str = "") -> list[str]:
        """Load relevant memories for this user session."""
        nonlocal memory_top3, memory_top3_detailed
        try:
            if _memory_available:
                bank = MemoryBankService(user_id)
                raw_results = bank.retrieve_memories(context_hint, top_k=3)
                memory_top3 = [m["content"] for m in raw_results][:3]
                memory_top3_detailed = [{
                    "content": m.get("content", "")[:120],
                    "category": m.get("category", "general"),
                    "importance": round(float(m.get("importance", 0.5)), 2),
                    "score": round(float(m.get("_composite_score", 0)), 3),
                } for m in raw_results][:3]
                return memory_top3
            return []
        except Exception:
            logger.exception("Failed to load memories for user %s", user_id)
            return []

    async def _sync_runtime_vad_update(new_lod: int) -> dict:
        """Inject a best-effort runtime VAD update marker into the live session."""
        supported, reason = supports_runtime_vad_reconfiguration()
        payload = build_vad_runtime_update_payload(new_lod)
        payload["runtime_hot_reconfig_supported"] = supported
        payload["runtime_note"] = "transport_hot_update_applied" if supported else reason

        content = types.Content(
            parts=[types.Part(text=build_vad_runtime_update_message(new_lod))],
            role="user",
        )
        live_request_queue.send_content(content)

        if supported:
            logger.info("Injected runtime VAD update payload for LOD %d: %s", new_lod, payload)
        else:
            logger.warning(
                "Runtime VAD transport hot-update unavailable (%s); injected sync marker only: %s",
                reason,
                payload,
            )
        return payload

    async def _notify_ios_lod_change(
        new_lod: int,
        reason: str,
        debug_dict: dict,
        vad_update: dict | None = None,
    ) -> None:
        """Send LOD change notification to iOS client."""
        await _safe_send_json({
            "type": "lod_update",
            "lod": new_lod,
            "reason": reason,
        })
        # SL-77: Include memory_top3 in debug_lod for DebugOverlay
        debug_dict["memory_top3"] = memory_top3
        debug_dict["memory_top3_detailed"] = memory_top3_detailed
        if vad_update:
            debug_dict["vad_update"] = vad_update
        await _safe_send_json({
            "type": "debug_lod",
            "data": debug_dict,
        })

    async def _emit_activity_debug_event(
        *,
        event_name: str,
        queue_status: str,
        queue_note: str = "",
        source: str = "ios_client",
    ) -> None:
        """Emit an observable activity event for iOS debug overlay."""
        ts = datetime.now(timezone.utc)
        is_activity_start = event_name == "activity_start"
        session_ctx.current_activity_state = "user_speaking" if is_activity_start else "idle"
        session_ctx.last_activity_event = event_name
        session_ctx.last_activity_event_ts = ts
        session_ctx.last_activity_source = source
        session_ctx.activity_event_count += 1

        await _safe_send_json({
            "type": "debug_activity",
            "data": {
                "event": event_name,
                "state": session_ctx.current_activity_state,
                "source": source,
                "queue_status": queue_status,
                "queue_note": queue_note,
                "timestamp": ts.isoformat(),
                "event_count": session_ctx.activity_event_count,
            },
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
        vad_update = await _sync_runtime_vad_update(1)
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
            vad_update=vad_update,
        )
        await _send_lod_update(1, ephemeral_ctx, panic_reason)
        logger.warning("PANIC activated for session %s: LOD %d -> 1", session_id, old_lod)

    # -- Sub-agent helpers (Phase 3) -----------------------------------------

    async def _run_vision_analysis(image_base64: str) -> None:
        """Run async vision analysis and inject results into Live session."""
        nonlocal _vision_in_progress, _last_vision_context_text
        nonlocal _last_vision_context_sent_at, _last_vision_prefeedback_at
        if not _vision_available:
            await _emit_tool_event(
                "analyze_scene",
                ToolBehavior.WHEN_IDLE,
                status="unavailable",
                data={"reason": "vision_agent_unavailable"},
            )
            return

        async with _vision_lock:
            if _vision_in_progress:
                return
            _vision_in_progress = True

        # B-5: Pre-feedback — immediate audio cue before analysis starts
        now_mono = time.monotonic()
        if now_mono - _last_vision_prefeedback_at >= VISION_PREFEEDBACK_COOLDOWN_SEC:
            await _forward_agent_transcript("Let me look at that for you...")
            _last_vision_prefeedback_at = now_mono

        try:
            ctx_dict = {
                "space_type": session_ctx.space_type,
                "trip_purpose": session_ctx.trip_purpose,
                "active_task": session_ctx.active_task,
                "motion_state": session_manager.get_ephemeral_context(session_id).motion_state,
            }
            result = await analyze_scene(image_base64, session_ctx.current_lod, ctx_dict)
            warnings = result.get("safety_warnings", [])
            vision_text = _format_vision_result(result, session_ctx.current_lod)
            vision_repeat_window = (
                VISION_SAFETY_REPEAT_SUPPRESS_SEC
                if warnings
                else VISION_REPEAT_SUPPRESS_SEC
            )
            now_mono = time.monotonic()
            repeated = _is_repeated_text(
                vision_text,
                previous_text=_last_vision_context_text,
                now_ts=now_mono,
                previous_ts=_last_vision_context_sent_at,
                cooldown_sec=vision_repeat_window,
            )
            if not repeated:
                await _safe_send_json({
                    "type": "vision_result",
                    "summary": result.get("scene_description", ""),
                    "behavior": behavior_to_text(ToolBehavior.WHEN_IDLE),
                    "data": _json_safe(result),
                })
                _last_vision_context_text = vision_text
                _last_vision_context_sent_at = now_mono
            else:
                logger.debug("Suppressed repeated vision summary within %.1fs window", vision_repeat_window)

            await _safe_send_json({
                "type": "vision_debug",
                "data": {
                    "bounding_boxes": _json_safe(result.get("bounding_boxes", [])),
                    "confidence": float(result.get("confidence", 0.0)),
                    "lod": session_ctx.current_lod,
                },
            })
            await _emit_tool_event(
                "analyze_scene",
                ToolBehavior.WHEN_IDLE,
                status="completed",
                data={
                    "confidence": float(result.get("confidence", 0.0)),
                    "repeat_suppressed": repeated,
                },
            )

            if result.get("confidence", 0) > 0 and not repeated:
                # Determine info_type for should_speak gate
                info_type = "safety_warning" if warnings else "spatial_description"
                ephemeral = session_manager.get_ephemeral_context(session_id)
                speak = should_speak(
                    info_type=info_type,
                    current_lod=session_ctx.current_lod,
                    step_cadence=getattr(ephemeral, "step_cadence", 0.0) or 0.0,
                    ambient_noise_db=getattr(ephemeral, "ambient_noise_db", 50.0) or 50.0,
                )

                if not speak:
                    vision_text = "[SILENT - context only, do not speak aloud]\n" + vision_text
                content = types.Content(
                    parts=[types.Part(text=vision_text)],
                    role="user",
                )
                live_request_queue.send_content(content)
                logger.info("Injected [VISION ANALYSIS] (LOD %d, confidence %.2f, speak=%s)",
                            session_ctx.current_lod, result.get("confidence", 0), speak)
        except Exception as exc:
            logger.exception("Vision analysis failed")
            await _emit_tool_event(
                "analyze_scene",
                ToolBehavior.WHEN_IDLE,
                status="error",
                data={"reason": "vision_analysis_failed"},
            )
            await _emit_capability_degraded("vision", str(exc)[:200])
        finally:
            async with _vision_lock:
                _vision_in_progress = False

    async def _run_face_recognition(image_base64: str) -> None:
        """Run face recognition and inject results as SILENT context."""
        nonlocal face_library, _face_library_loaded_at
        if not _face_available:
            await _emit_tool_event(
                "identify_person",
                ToolBehavior.SILENT,
                status="unavailable",
                data={"reason": "face_agent_unavailable"},
            )
            return

        # Periodic refresh of face library
        now_mono = time.monotonic()
        if now_mono - _face_library_loaded_at >= FACE_LIBRARY_REFRESH_SEC:
            try:
                face_library = load_face_library(user_id)
                _face_library_loaded_at = now_mono
                logger.info("Refreshed face library (%d faces) for user %s", len(face_library), user_id)
            except Exception:
                logger.exception("Failed to refresh face library for user %s", user_id)

        try:
            results = await asyncio.to_thread(
                identify_persons_in_frame,
                image_base64,
                user_id,
                face_library,
                ToolBehavior.SILENT,
            )
            await _safe_send_json({
                "type": "face_debug",
                "data": {
                    "face_boxes": _json_safe([
                        {
                            "bbox": item.get("bbox", []),
                            "label": item.get("person_name", "unknown"),
                            "score": float(item.get("score", 0.0)),
                            "similarity": float(item.get("similarity", 0.0)),
                        }
                        for item in results
                    ]),
                },
            })
            known = [r for r in results if r["person_name"] != "unknown"]
            await _emit_tool_event(
                "identify_person",
                ToolBehavior.SILENT,
                status="completed",
                data={"detections": len(results), "known": len(known)},
            )
            if known:
                ephemeral = session_manager.get_ephemeral_context(session_id)
                speak = should_speak(
                    info_type="face_recognition",
                    current_lod=session_ctx.current_lod,
                    step_cadence=getattr(ephemeral, "step_cadence", 0.0) or 0.0,
                    ambient_noise_db=getattr(ephemeral, "ambient_noise_db", 50.0) or 50.0,
                )

                face_text = _format_face_results(known)
                if _memory_available:
                    for person in known:
                        pname = person.get("person_name", "")
                        if pname and pname != "unknown":
                            try:
                                person_memories = load_relevant_memories(user_id, f"person {pname}", top_k=2)
                                if person_memories:
                                    face_text += f"\nMemories about {pname}:"
                                    for mem in person_memories:
                                        face_text += f"\n- {mem}"
                            except Exception:
                                logger.debug("Failed to load memories for person %s", pname, exc_info=True)
                if not speak:
                    face_text = "[SILENT - context only, do not speak aloud]\n" + face_text
                content = types.Content(
                    parts=[types.Part(text=face_text)],
                    role="user",
                )
                live_request_queue.send_content(content)
                logger.info("Injected [FACE ID] (speak=%s): %s",
                            speak, ", ".join(r["person_name"] for r in known))
                best = max(known, key=lambda item: float(item.get("similarity", 0.0)))
                await _emit_identity_event(
                    person_name=str(best.get("person_name", "unknown")),
                    matched=True,
                    similarity=float(best.get("similarity", 0.0)),
                    source="face_match",
                )
            elif results:
                await _emit_identity_event(
                    person_name="unknown",
                    matched=False,
                    similarity=0.0,
                    source="face_detected_no_match",
                )
        except Exception as exc:
            logger.exception("Face recognition failed")
            await _emit_tool_event(
                "identify_person",
                ToolBehavior.SILENT,
                status="error",
                data={"reason": "face_recognition_failed"},
            )
            await _emit_capability_degraded("face", str(exc)[:200])

    async def _run_ocr_analysis(image_base64: str, safety_only: bool = False) -> None:
        """Run OCR and inject results into Live session context."""
        nonlocal _last_ocr_context_text, _last_ocr_context_sent_at, _last_ocr_prefeedback_at
        if not _ocr_available:
            await _emit_tool_event(
                "extract_text",
                ToolBehavior.WHEN_IDLE,
                status="unavailable",
                data={"reason": "ocr_agent_unavailable"},
            )
            return

        # B-5: Pre-feedback — immediate audio cue before analysis starts
        # Skip pre-feedback for safety-only scans (LOD 1/2)
        if not safety_only:
            now_mono = time.monotonic()
            if now_mono - _last_ocr_prefeedback_at >= OCR_PREFEEDBACK_COOLDOWN_SEC:
                await _forward_agent_transcript("Reading the text for you...")
                _last_ocr_prefeedback_at = now_mono

        try:
            # Build context hint from session state
            hint = ""
            if session_ctx.space_type:
                hint = f"User is in a {session_ctx.space_type} environment."
            if session_ctx.active_task:
                hint += f" Currently: {session_ctx.active_task}."

            result = await extract_text(image_base64, context_hint=hint, safety_only=safety_only)
            ocr_text = _format_ocr_result(result)
            repeat_window = OCR_SAFETY_REPEAT_SUPPRESS_SEC if safety_only else OCR_REPEAT_SUPPRESS_SEC
            now_mono = time.monotonic()
            repeated = _is_repeated_text(
                ocr_text,
                previous_text=_last_ocr_context_text,
                now_ts=now_mono,
                previous_ts=_last_ocr_context_sent_at,
                cooldown_sec=repeat_window,
            )
            if not repeated:
                await _safe_send_json({
                    "type": "ocr_result",
                    "summary": result.get("text", ""),
                    "behavior": behavior_to_text(ToolBehavior.WHEN_IDLE),
                    "data": _json_safe(result),
                })
                _last_ocr_context_text = ocr_text
                _last_ocr_context_sent_at = now_mono
            else:
                logger.debug("Suppressed repeated OCR summary within %.1fs window", repeat_window)

            await _safe_send_json({
                "type": "ocr_debug",
                "data": {
                    "text_regions": _json_safe(result.get("text_regions", [])),
                    "text_type": result.get("text_type", "unknown"),
                    "confidence": float(result.get("confidence", 0.0)),
                },
            })
            await _emit_tool_event(
                "extract_text",
                ToolBehavior.WHEN_IDLE,
                status="completed",
                data={
                    "confidence": float(result.get("confidence", 0.0)),
                    "repeat_suppressed": repeated,
                },
            )

            if result.get("confidence", 0) > 0.3 and result.get("text") and not repeated:
                ephemeral = session_manager.get_ephemeral_context(session_id)
                info_type = "safety_warning" if safety_only else "object_enumeration"
                speak = should_speak(
                    info_type=info_type,
                    current_lod=session_ctx.current_lod,
                    step_cadence=getattr(ephemeral, "step_cadence", 0.0) or 0.0,
                    ambient_noise_db=getattr(ephemeral, "ambient_noise_db", 50.0) or 50.0,
                )

                if not speak:
                    ocr_text = "[SILENT - context only, do not speak aloud]\n" + ocr_text
                content = types.Content(
                    parts=[types.Part(text=ocr_text)],
                    role="user",
                )
                live_request_queue.send_content(content)
                logger.info("Injected [OCR RESULT] (%s, confidence %.2f, speak=%s)",
                            result.get("text_type", "unknown"), result.get("confidence", 0), speak)
        except Exception as exc:
            logger.exception("OCR analysis failed")
            await _emit_tool_event(
                "extract_text",
                ToolBehavior.WHEN_IDLE,
                status="error",
                data={"reason": "ocr_analysis_failed"},
            )
            await _emit_capability_degraded("ocr", str(exc)[:200])

    # -- Upstream handler ----------------------------------------------------

    # Binary frame magic bytes for audio/image binary protocol (Phase 5)
    _MAGIC_AUDIO = 0x01
    _MAGIC_IMAGE = 0x02

    async def _upstream() -> None:
        """Read messages from the iOS client and forward to the Live API.

        Supports both legacy JSON text messages and optimized binary frames.
        Binary protocol: first byte is magic byte (0x01=audio, 0x02=image),
        remaining bytes are raw payload. This eliminates ~33% Base64 overhead.

        Handles upstream message types: audio, image, telemetry,
        activity_start, activity_end, gesture.
        """
        nonlocal _last_vision_time, _frame_seq, _allow_agent_repeat_until, _client_camera_active

        try:
            while True:
                # Use low-level receive() to handle both text and binary
                ws_message = await websocket.receive()

                # --- Binary frame (optimized path) ---
                if "bytes" in ws_message and ws_message["bytes"]:
                    raw_bytes: bytes = ws_message["bytes"]
                    if len(raw_bytes) < 2:
                        continue

                    magic = raw_bytes[0]
                    payload = raw_bytes[1:]

                    if magic == _MAGIC_AUDIO:
                        blob = types.Blob(
                            data=payload,
                            mime_type="audio/pcm;rate=16000",
                        )
                        live_request_queue.send_realtime(blob)
                        continue

                    elif magic == _MAGIC_IMAGE:
                        blob = types.Blob(
                            data=payload,
                            mime_type="image/jpeg",
                        )
                        live_request_queue.send_realtime(blob)
                        _frame_seq += 1

                        # Trigger async sub-agents (same logic as JSON path)
                        import time as _time
                        now = _time.monotonic()
                        lod = session_ctx.current_lod
                        vision_interval = {1: 8.0, 2: 5.0, 3: 3.0}.get(lod, 5.0)
                        queued_agents: list[str] = []
                        if now - _last_vision_time >= vision_interval:
                            _last_vision_time = now
                            image_b64 = base64.b64encode(payload).decode("ascii")
                            await _emit_tool_event(
                                "analyze_scene", ToolBehavior.WHEN_IDLE, status="queued",
                            )
                            queued_agents.append("vision")
                            asyncio.create_task(_run_vision_analysis(image_b64))

                            # Face recognition: only at LOD 2/3 (match JSON path)
                            if lod >= 2:
                                await _emit_tool_event(
                                    "identify_person", ToolBehavior.SILENT, status="queued",
                                )
                                queued_agents.append("face")
                                await _emit_identity_event(
                                    person_name="unknown",
                                    matched=False,
                                    similarity=0.0,
                                    source="queued",
                                )
                                asyncio.create_task(_run_face_recognition(image_b64))

                            # OCR: safety-only at LOD 1-2, full at LOD 3
                            if lod >= 1:
                                await _emit_tool_event(
                                    "extract_text", ToolBehavior.WHEN_IDLE, status="queued",
                                )
                                queued_agents.append("ocr")
                                asyncio.create_task(_run_ocr_analysis(image_b64, safety_only=(lod < 3)))
                        await _safe_send_json({
                            "type": "frame_ack",
                            "frame_id": _frame_seq,
                            "queued_agents": queued_agents,
                        })
                        continue

                    else:
                        logger.warning("Unknown binary magic byte: 0x%02x", magic)
                        continue

                # --- Text frame (JSON, legacy + control messages) ---
                raw_text = ws_message.get("text")
                if not raw_text:
                    # Check for disconnect
                    if ws_message.get("type") == "websocket.disconnect":
                        break
                    continue

                try:
                    message = json.loads(raw_text)
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
                    # Send raw frame to Gemini Live API
                    live_request_queue.send_realtime(blob)
                    _frame_seq += 1

                    # Phase 3: Trigger async sub-agents on image frames
                    import time as _time
                    now = _time.monotonic()
                    lod = session_ctx.current_lod

                    # Vision analysis: LOD-aware frequency
                    # LOD 1: every 5s, LOD 2: every 3s, LOD 3: every 2s
                    vision_interval = {1: 8.0, 2: 5.0, 3: 3.0}.get(lod, 5.0)
                    queued_agents: list[str] = []
                    if now - _last_vision_time >= vision_interval:
                        _last_vision_time = now
                        image_b64 = message["data"]
                        await _emit_tool_event(
                            "analyze_scene",
                            ToolBehavior.WHEN_IDLE,
                            status="queued",
                        )
                        queued_agents.append("vision")
                        # Fire-and-forget async tasks
                        asyncio.create_task(_run_vision_analysis(image_b64))

                        # Face recognition: only at LOD 2/3
                        if lod >= 2:
                            await _emit_tool_event(
                                "identify_person",
                                ToolBehavior.SILENT,
                                status="queued",
                            )
                            queued_agents.append("face")
                            # Emit an early SILENT identity update for edge contracts.
                            await _emit_identity_event(
                                person_name="unknown",
                                matched=False,
                                similarity=0.0,
                                source="queued",
                            )
                            asyncio.create_task(_run_face_recognition(image_b64))

                        # OCR: safety-only at LOD 1-2, full at LOD 3
                        if lod >= 1:
                            await _emit_tool_event(
                                "extract_text",
                                ToolBehavior.WHEN_IDLE,
                                status="queued",
                            )
                            queued_agents.append("ocr")
                            asyncio.create_task(_run_ocr_analysis(image_b64, safety_only=(lod < 3)))
                    await _safe_send_json({
                        "type": "frame_ack",
                        "frame_id": _frame_seq,
                        "queued_agents": queued_agents,
                    })

                elif message.get("type") == "camera_failure":
                    # SL-76: Camera hardware failure path
                    camera_error = (
                        message.get("error")
                        or message.get("reason")
                        or "camera_unavailable"
                    )
                    logger.warning("Camera failure reported: %s", camera_error)
                    await _emit_capability_degraded(
                        "camera",
                        camera_error,
                        recoverable=message.get("recoverable", True),
                    )

                elif message.get("type") == "telemetry":
                    telemetry_data = message.get("data", {})
                    await _process_telemetry(telemetry_data)

                elif message.get("type") == "activity_start":
                    queue_status = "forwarded"
                    queue_note = ""
                    try:
                        live_request_queue.send_activity_start()
                        logger.info("Forwarded activity_start to LiveRequestQueue")
                    except Exception as exc:
                        queue_status = "forward_failed"
                        queue_note = str(exc)[:200]
                        logger.warning(
                            "Failed to forward activity_start to LiveRequestQueue: %s",
                            queue_note,
                        )
                    await _emit_activity_debug_event(
                        event_name="activity_start",
                        queue_status=queue_status,
                        queue_note=queue_note,
                    )

                elif message.get("type") == "activity_end":
                    queue_status = "forwarded"
                    queue_note = ""
                    try:
                        live_request_queue.send_activity_end()
                        logger.info("Forwarded activity_end to LiveRequestQueue")
                    except Exception as exc:
                        queue_status = "forward_failed"
                        queue_note = str(exc)[:200]
                        logger.warning(
                            "Failed to forward activity_end to LiveRequestQueue: %s",
                            queue_note,
                        )
                    await _emit_activity_debug_event(
                        event_name="activity_end",
                        queue_status=queue_status,
                        queue_note=queue_note,
                    )

                elif message.get("type") == "gesture":
                    gesture = message.get("gesture")
                    if gesture in ("lod_up", "lod_down"):
                        ephemeral_ctx = session_manager.get_ephemeral_context(session_id)
                        ephemeral_ctx.user_gesture = gesture
                        await _process_lod_decision(ephemeral_ctx)
                        ephemeral_ctx.user_gesture = None
                        session_manager.update_ephemeral_context(session_id, ephemeral_ctx)

                    elif isinstance(gesture, str) and gesture.startswith("force_lod_"):
                        try:
                            forced_lod = int(gesture.rsplit("_", 1)[-1])
                        except (TypeError, ValueError):
                            logger.warning("Invalid force_lod gesture payload: %s", gesture)
                            continue

                        if forced_lod not in (1, 2, 3):
                            logger.warning("force_lod gesture out of range: %s", gesture)
                            continue

                        old_lod = session_ctx.current_lod
                        if forced_lod == old_lod:
                            await _safe_send_json({
                                "type": "lod_update",
                                "lod": forced_lod,
                                "reason": "force_lod_no_change",
                            })
                            continue

                        reason = f"manual_force_lod_{forced_lod}"
                        logger.info("Force LOD gesture received: %d -> %d", old_lod, forced_lod)
                        resume_prompt = on_lod_change(session_ctx, old_lod, forced_lod)
                        session_ctx.current_lod = forced_lod
                        telemetry_agg.update_lod(forced_lod)

                        vad_update = await _sync_runtime_vad_update(forced_lod)
                        await _send_lod_update(
                            forced_lod,
                            session_manager.get_ephemeral_context(session_id),
                            reason,
                        )
                        await _notify_ios_lod_change(
                            forced_lod,
                            reason,
                            {
                                "lod": forced_lod,
                                "prev": old_lod,
                                "reason": reason,
                                "rules": [f"manual:{gesture}"],
                                "forced": True,
                            },
                            vad_update=vad_update,
                        )

                        if resume_prompt:
                            resume_content = types.Content(
                                parts=[types.Part(text=resume_prompt)],
                                role="user",
                            )
                            live_request_queue.send_content(resume_content)

                    elif gesture == "interrupt":
                        logger.info("User interrupt gesture received")
                        content = types.Content(
                            parts=[types.Part(text="[USER INTERRUPT] The user has interrupted. Stop current output immediately and wait for their next input.")],
                            role="user",
                        )
                        live_request_queue.send_content(content)

                    elif gesture == "repeat_last":
                        _allow_agent_repeat_until = time.monotonic() + 12.0
                        last_agent = None
                        for entry in reversed(transcript_history):
                            if entry.get("role") == "agent":
                                last_agent = entry.get("text", "")
                                break
                        if last_agent:
                            logger.info("Repeat last gesture: replaying last agent utterance")
                            content = types.Content(
                                parts=[types.Part(text=f'[REPEAT REQUEST] The user wants you to repeat your last response. Please repeat: "{last_agent}"')],
                                role="user",
                            )
                            live_request_queue.send_content(content)
                        else:
                            logger.info("Repeat last gesture: no previous agent utterance found")
                            content = types.Content(
                                parts=[types.Part(text="[REPEAT REQUEST] The user wants you to repeat your last response, but no previous response was found. Let the user know.")],
                                role="user",
                            )
                            live_request_queue.send_content(content)

                    elif gesture == "mute_toggle":
                        # Support explicit state from iOS and legacy toggle-only payloads.
                        if "muted" in message:
                            _is_client_muted = _coerce_bool(message.get("muted"), default=False)
                        else:
                            _is_client_muted = not _is_client_muted
                        logger.info("Mute toggle: muted=%s", _is_client_muted)

                    elif gesture == "sos":
                        logger.warning("SOS gesture received for session %s", session_id)
                        ephemeral_ctx = session_manager.get_ephemeral_context(session_id)
                        ephemeral_ctx.panic = True
                        await _handle_panic(ephemeral_ctx)

                    elif gesture == "emergency_pause":
                        paused = _coerce_bool(message.get("paused", True), default=True)
                        if paused:
                            old_lod = session_ctx.current_lod
                            logger.warning("Emergency pause activated: LOD %d -> 1", old_lod)
                            on_lod_change(session_ctx, old_lod, 1)
                            session_ctx.current_lod = 1
                            content = types.Content(
                                parts=[types.Part(text="[EMERGENCY PAUSE] The user has activated emergency pause. Switch to LOD 1 (safety-only mode). Go silent and only respond to direct safety-critical queries until further notice.")],
                                role="user",
                            )
                            live_request_queue.send_content(content)
                            await _safe_send_json({
                                "type": "lod_update",
                                "lod": 1,
                                "reason": "emergency_pause",
                            })
                        else:
                            resume_lod = 2
                            old_lod = session_ctx.current_lod
                            logger.info("Emergency pause resumed: LOD %d -> %d", old_lod, resume_lod)
                            on_lod_change(session_ctx, old_lod, resume_lod)
                            session_ctx.current_lod = resume_lod
                            content = types.Content(
                                parts=[types.Part(text="[EMERGENCY RESUME] The user has deactivated emergency pause. Resume normal operation at LOD 2 (balanced mode). You may speak again.")],
                                role="user",
                            )
                            live_request_queue.send_content(content)
                            await _safe_send_json({
                                "type": "lod_update",
                                "lod": resume_lod,
                                "reason": "emergency_resume",
                            })

                    elif gesture == "camera_toggle":
                        nonlocal _client_camera_active
                        _client_camera_active = _coerce_bool(
                            message.get("active"), default=not _client_camera_active,
                        )
                        logger.info("Camera toggle: active=%s", _client_camera_active)
                        if _client_camera_active:
                            content = types.Content(
                                parts=[types.Part(
                                    text=(
                                        "[CAMERA ACTIVATED] The user has turned on the rear camera. "
                                        "You can now see their surroundings via image frames. "
                                        "Briefly acknowledge and describe what you see when the first image arrives."
                                    )
                                )],
                                role="user",
                            )
                            live_request_queue.send_content(content)
                        else:
                            content = types.Content(
                                parts=[types.Part(
                                    text=(
                                        "[CAMERA DEACTIVATED] The user has turned off the camera. "
                                        "You are now in audio-only mode. Do not reference visual information "
                                        "unless recalling something previously seen."
                                    )
                                )],
                                role="user",
                            )
                            live_request_queue.send_content(content)

                    else:
                        logger.debug("Unhandled gesture type: %s", gesture)

                elif message.get("type") == "reload_face_library":
                    logger.info("Reload face library requested for user=%s", user_id)
                    if _face_available:
                        try:
                            face_library.clear()
                            face_library.extend(await asyncio.to_thread(load_face_library, user_id))
                            await _safe_send_json({
                                "type": "face_library_reloaded",
                                "count": len(face_library),
                            })
                            logger.info("Reloaded %d face(s) for user %s", len(face_library), user_id)
                        except Exception:
                            logger.exception("Failed to reload face library")
                            await _safe_send_json({
                                "type": "error",
                                "error": "Failed to reload face library",
                            })
                    else:
                        await _safe_send_json({
                            "type": "error",
                            "error": "Face recognition not available",
                        })

                elif message.get("type") == "clear_face_library":
                    logger.info("Clear face library requested for user=%s", user_id)
                    if _face_available:
                        try:
                            from tools.face_tools import clear_face_library
                            count = await asyncio.to_thread(clear_face_library, user_id)
                            face_library.clear()
                            await _safe_send_json({
                                "type": "face_library_cleared",
                                "deleted_count": count,
                            })
                            logger.info("Cleared %d face(s) for user %s", count, user_id)
                        except Exception:
                            logger.exception("Failed to clear face library")
                            await _safe_send_json({
                                "type": "error",
                                "error": "Failed to clear face library",
                            })
                    else:
                        await _safe_send_json({
                            "type": "error",
                            "error": "Face recognition not available",
                        })

                else:
                    logger.warning("Unknown upstream message type: %s", message.get("type"))

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
        nonlocal _last_telemetry_signature, _last_telemetry_context_sent_at

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
                parts=[types.Part(
                    text=(
                        "<<<SENSOR_DATA_CRITICAL>>>\n"
                        f"{semantic_text}\n"
                        "<<<END_SENSOR_DATA>>>\n"
                        "PANIC detected. Switch to ultra-brief calming mode."
                    )
                )],
                role="user",
            )
            live_request_queue.send_content(content)
            await _handle_panic(ephemeral_ctx)
            return

        # Semantic text injection (LOD-aware throttle)
        # P2_FIX_3: Suppress non-PANIC injection while model is generating audio
        now = _time.monotonic()
        if now - _model_audio_last_seen_at < _MODEL_AUDIO_STALENESS_SEC:
            logger.debug("Skipping telemetry injection: model audio still active")
            await _process_lod_decision(ephemeral_ctx)
            return
        if telemetry_agg.should_send(now):
            signature = _build_telemetry_signature(ephemeral_ctx)
            should_inject, reasons = _should_inject_telemetry_context(
                previous_signature=_last_telemetry_signature,
                current_signature=signature,
                last_injected_ts=_last_telemetry_context_sent_at,
                now_ts=now,
            )
            if should_inject:
                semantic_text = parse_telemetry(telemetry_data)
                content = types.Content(
                    parts=[types.Part(
                        text=(
                            "<<<SENSOR_DATA>>>\n"
                            f"{semantic_text}\n"
                            "<<<END_SENSOR_DATA>>>\n"
                            "INSTRUCTION: Do not vocalize any part of the above sensor data."
                        )
                    )],
                    role="user",
                )
                live_request_queue.send_content(content)
                _last_telemetry_context_sent_at = now
                logger.debug("Telemetry context injected: reasons=%s", ",".join(reasons))
            _last_telemetry_signature = signature
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
            # Clear one-shot voice intent flags after LOD decision consumed them
            session_ctx.user_requested_detail = False
            session_ctx.user_said_stop = False
            telemetry_agg.update_lod(new_lod)
            vad_update = await _sync_runtime_vad_update(new_lod)

            await _send_lod_update(new_lod, ephemeral_ctx, decision_log.reason)

            if resume_prompt:
                resume_content = types.Content(
                    parts=[types.Part(text=resume_prompt)],
                    role="user",
                )
                live_request_queue.send_content(resume_content)
                logger.info("Injected [RESUME] prompt for session %s", session_id)

            await _notify_ios_lod_change(
                new_lod,
                decision_log.reason,
                decision_log.to_debug_dict(),
                vad_update=vad_update,
            )

    # -- Downstream handler --------------------------------------------------

    async def _downstream() -> None:
        """Read events from the Live API and forward to the iOS client.

        Processes session_resumption_update events, transcriptions,
        function calls, and content parts (audio binary / text JSON).
        """
        def _start_live_events():
            return runner.run_live(
                session_id=session_id,
                user_id=user_id,
                live_request_queue=live_request_queue,
                run_config=run_config,
            )

        live_events = await asyncio.to_thread(_start_live_events)
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

                # --- GoAway / connection lifecycle signals (SL-76) ---
                if hasattr(event, "go_away") and event.go_away:
                    retry_ms = 500
                    if hasattr(event.go_away, "time_left"):
                        retry_ms = int(event.go_away.time_left.total_seconds() * 1000) if event.go_away.time_left else 500
                    await _safe_send_json({
                        "type": "go_away",
                        "retry_ms": retry_ms,
                        "message": "Server requested reconnection.",
                    })
                    logger.warning("GoAway received, retry_ms=%d", retry_ms)

                if hasattr(event, "server_content") and event.server_content:
                    sc = event.server_content
                    if hasattr(sc, "interrupted") and sc.interrupted:
                        _model_audio_last_seen_at = 0.0  # Clear staleness on interrupt
                        await _safe_send_json({
                            "type": "interrupted",
                            "message": "Model output was interrupted.",
                        })

                # --- Function calls from Gemini (Phase 3) ---
                function_calls = _extract_function_calls(event)
                if function_calls:
                    for fc in function_calls:
                        user_speaking = session_ctx.current_activity_state == "user_speaking"
                        behavior = resolve_tool_behavior(
                            tool_name=fc.name,
                            lod=session_ctx.current_lod,
                            is_user_speaking=user_speaking,
                        )
                        await _emit_tool_event(
                            fc.name,
                            behavior,
                            status="invoked",
                            data={"args": _json_safe(dict(fc.args) if fc.args else {})},
                        )
                        result = await _dispatch_function_call(
                            fc.name,
                            dict(fc.args) if fc.args else {},
                            session_id,
                            user_id,
                        )
                        await _safe_send_json({
                            "type": "tool_result",
                            "tool": fc.name,
                            "behavior": behavior_to_text(behavior),
                            "data": _json_safe(result),
                        })

                        if fc.name in NAVIGATION_FUNCTIONS:
                            await _safe_send_json({
                                "type": "navigation_result",
                                "summary": str(result.get("destination_direction") or result.get("destination") or ""),
                                "behavior": behavior_to_text(behavior),
                                "data": _json_safe(result),
                            })
                        elif fc.name == "google_search":
                            await _safe_send_json({
                                "type": "search_result",
                                "summary": str(result.get("answer") or ""),
                                "behavior": behavior_to_text(behavior),
                                "data": _json_safe(result),
                            })
                        elif fc.name == "identify_person":
                            await _emit_identity_event(
                                person_name=str(result.get("person_name", "unknown")),
                                matched=bool(result.get("matched", False)),
                                similarity=float(result.get("similarity", 0.0)),
                                source="tool_call",
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

                # --- Output transcription (agent speech-to-text) — process BEFORE input ---
                if event.output_transcription and event.output_transcription.text:
                    now_mono = time.monotonic()
                    transcript_history.append({
                        "role": "agent",
                        "text": event.output_transcription.text,
                    })
                    # Track for echo detection
                    _recent_agent_texts.append((now_mono, event.output_transcription.text))
                    # Prune entries older than 10s
                    cutoff = now_mono - 10.0
                    while _recent_agent_texts and _recent_agent_texts[0][0] < cutoff:
                        _recent_agent_texts.pop(0)
                    if not await _forward_agent_transcript(event.output_transcription.text):
                        break

                # --- Input transcription (user speech-to-text) with echo detection ---
                if event.input_transcription and event.input_transcription.text:
                    now_mono = time.monotonic()
                    input_text = event.input_transcription.text
                    if _is_likely_echo(input_text, now_mono):
                        logger.debug("Echo detected, reclassifying: %s", input_text[:120])
                        transcript_history.append({
                            "role": "echo",
                            "text": input_text,
                        })
                        await _safe_send_json({
                            "type": "transcript",
                            "text": input_text,
                            "role": "echo",
                        })
                    else:
                        transcript_history.append({
                            "role": "user",
                            "text": input_text,
                        })
                        if not await _safe_send_json({
                            "type": "transcript",
                            "text": input_text,
                            "role": "user",
                        }):
                            break

                        # Voice intent → LOD session flags
                        intent = _detect_voice_intent(input_text)
                        if intent == "detail":
                            session_ctx.user_requested_detail = True
                            session_ctx.user_said_stop = False
                        elif intent == "stop":
                            session_ctx.user_said_stop = True
                            session_ctx.user_requested_detail = False

                # --- Content parts (audio / text) ---
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if stop_downstream.is_set():
                            break

                        if part.inline_data and part.inline_data.data:
                            _model_audio_last_seen_at = time.monotonic()
                            audio_data = part.inline_data.data
                            if isinstance(audio_data, str):
                                audio_data = base64.b64decode(audio_data)
                            if not await _safe_send_bytes(audio_data):
                                break

                        elif part.text:
                            if not await _forward_agent_transcript(part.text):
                                break

                    if stop_downstream.is_set():
                        break

        except WebSocketDisconnect:
            stop_downstream.set()
            logger.info("Client disconnected (downstream): user=%s session=%s", user_id, session_id)
        except Exception:
            stop_downstream.set()
            logger.exception("Error in downstream handler: user=%s session=%s", user_id, session_id)
            await _safe_send_json({
                "type": "error",
                "error": "Live session failed. Reconnecting...",
            })
            try:
                await websocket.close(code=1011, reason="downstream_error")
            except Exception:
                pass

    try:
        await asyncio.gather(_upstream(), _downstream())
    except Exception:
        logger.exception("Session error: user=%s session=%s", user_id, session_id)
    finally:
        # Phase 5: Auto-extract memories from session transcript
        if _memory_extractor_available and _memory_available and transcript_history:
            try:
                extractor = MemoryExtractor()
                bank = MemoryBankService(user_id)
                budget = memory_budget or MemoryBudgetTracker()
                count = extractor.extract_and_store(
                    user_id=user_id,
                    session_id=session_id,
                    transcript_history=transcript_history,
                    memory_bank=bank,
                    budget=budget,
                )
                logger.info(
                    "Auto-extracted %d memories for user=%s session=%s",
                    count, user_id, session_id,
                )
            except Exception:
                logger.exception(
                    "Memory auto-extraction failed for user=%s session=%s",
                    user_id, session_id,
                )

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
