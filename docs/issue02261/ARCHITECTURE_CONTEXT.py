"""
SightLine — Architecture Context for Issue 02261 Fixes
======================================================
This file provides the architectural context the implementing agent needs.
Read this BEFORE reading ROOT_CAUSE_ANALYSIS.py.

All paths are relative to the project root: /Users/sunfl/Documents/study/ContextGen/
"""

# =============================================================================
# HIGH-LEVEL ARCHITECTURE
# =============================================================================
#
# iOS App (SwiftUI)
#   ↕ WebSocket (binary audio 0x01 / binary image 0x02 / JSON text)
# FastAPI Backend (server.py)
#   ↕ ADK LiveRequestQueue (send_content / send_realtime)
# Gemini Live API (native audio model)
#   → events: input_transcription, output_transcription, content.parts, function_calls
#
# Key insight: The backend is a BIDIRECTIONAL PROXY between iOS and Gemini.
# It also injects "system context" (telemetry, vision, LOD) into the Gemini
# session as role="user" messages, because Gemini Live API has no role="system".


# =============================================================================
# DATA FLOW: USER SPEAKS → MODEL RESPONDS
# =============================================================================
#
# 1. iOS AudioCaptureManager captures PCM 16kHz mono
# 2. Sent as binary frame (magic 0x01) via WebSocket
# 3. server.py _upstream() receives it → live_request_queue.send_realtime(blob)
# 4. Gemini processes audio, generates:
#    - event.input_transcription  (ASR of user speech)
#    - event.content.parts with inline_data (model audio response, PCM 24kHz)
#    - event.output_transcription (ASR of model speech)
# 5. server.py _downstream() forwards:
#    - input_transcription → iOS as {"type":"transcript","role":"user","text":...}
#    - audio data → iOS as binary WebSocket frame
#    - output_transcription → iOS as {"type":"transcript","role":"agent","text":...}
# 6. iOS AudioPlaybackManager plays PCM 24kHz audio


# =============================================================================
# DATA FLOW: CONTEXT INJECTION (THE PROBLEMATIC PATH)
# =============================================================================
#
# 1. iOS sends telemetry JSON every 2-3s: {"type":"telemetry","data":{...}}
# 2. server.py _process_telemetry():
#    a. parse_telemetry_to_ephemeral(data) → EphemeralContext (for LOD engine)
#    b. parse_telemetry(data) → semantic text string (for Gemini injection)
#    c. Wrap in "[TELEMETRY CONTEXT - INTERNAL ONLY]\n..."
#    d. live_request_queue.send_content(Content(text=..., role="user"))
#    e. Gemini sees this as a "user message" and may respond to it
#
# Same pattern for:
#   - [LOD UPDATE] messages (on LOD transitions)
#   - [VISION ANALYSIS] (from vision sub-agent, async)
#   - [OCR RESULT] (from OCR sub-agent, async)
#   - [FACE ID] (from face recognition pipeline, async)
#   - [VAD UPDATE] (on LOD transitions, text-only marker)


# =============================================================================
# KEY FILES — MUST READ BEFORE IMPLEMENTING
# =============================================================================

FILES = {
    # -- Backend (Python) --
    "server.py": {
        "path": "SightLine/server.py",
        "lines": 2100,
        "role": "Main WebSocket endpoint, all injection logic, downstream handler",
        "key_sections": {
            "constants": "105-112 (repeat suppression timings, force refresh)",
            "telemetry_sig": "203-252 (_should_inject_telemetry_context)",
            "initial_prompt": "785-800 (session start injection)",
            "lod_update": "804-827 (_send_lod_update)",
            "vad_update": "855-876 (_sync_runtime_vad_update)",
            "vision_inject": "1036-1055 (vision → send_content)",
            "ocr_inject": "1244-1262 (OCR → send_content)",
            "face_inject": "1129-1150 (face → send_content)",
            "upstream": "1279-1707 (_upstream handler)",
            "telemetry_proc": "1711-1769 (_process_telemetry)",
            "downstream": "1811-1967 (_downstream handler)",
            "transcription": "1926-1946 (input/output transcription → iOS)",
        },
    },
    "session_manager.py": {
        "path": "SightLine/live_api/session_manager.py",
        "role": "VAD presets, RunConfig construction, session state",
        "key_sections": {
            "vad_presets": "102-127 (LOD_VAD_PRESETS dict)",
            "runtime_vad": "139-152 (supports_runtime_vad_reconfiguration → False)",
            "vad_message": "154-166 (build_vad_runtime_update_message text marker)",
            "run_config": "218-261 (get_run_config with VAD, proactivity, etc.)",
        },
    },
    "telemetry_parser.py": {
        "path": "SightLine/telemetry/telemetry_parser.py",
        "role": "Converts raw telemetry dict → text for Gemini and EphemeralContext for LOD",
        "key_sections": {
            "parse_telemetry": "19-122 (dict → natural language text, NEEDS REWRITE)",
            "parse_to_ephemeral": "152-223 (dict → EphemeralContext, KEEP AS-IS)",
        },
    },
    "orchestrator.py": {
        "path": "SightLine/agents/orchestrator.py",
        "role": "Static system prompt for the Gemini model",
        "key_sections": {
            "system_prompt": "43-139 (SYSTEM_PROMPT constant)",
            "agent_creation": "142-171 (create_orchestrator_agent)",
        },
    },
    "prompt_builder.py": {
        "path": "SightLine/lod/prompt_builder.py",
        "role": "Dynamic LOD/telemetry prompt construction",
        "key_sections": {
            "lod_instructions": "36-62 (LOD 1/2/3 text)",
            "cot_prompt": "69-80 (LOD_COT_PROMPT with raw values)",
            "persona": "87-138 (_build_persona_block)",
            "lod_update_msg": "146-220 (build_lod_update_message)",
            "full_prompt": "228-319 (build_full_dynamic_prompt)",
        },
    },

    # -- iOS (Swift) --
    "MainView.swift": {
        "path": "SightLine/SightLine/UI/MainView.swift",
        "role": "Main UI, WebSocket callbacks, transcript handling",
        "key_sections": {
            "transcript_handling": "477-485 (handleDownstreamMessage .transcript)",
            "tool_behavior": "650-683 (INTERRUPT/WHEN_IDLE/SILENT dispatch)",
        },
    },
    "DeveloperConsoleView.swift": {
        "path": "SightLine/SightLine/UI/DeveloperConsoleView.swift",
        "role": "Debug console with System Log tab",
        "key_sections": {
            "entry_struct": "23-28 (TranscriptEntry with role field)",
            "role_coloring": "~520 (user=cyan, agent=green, other=white)",
            "capture": "248-254 (captureTranscript adds to array)",
        },
    },
    "MessageProtocol.swift": {
        "path": "SightLine/SightLine/Core/MessageProtocol.swift",
        "role": "WebSocket message encoding/decoding",
        "key_sections": {
            "transcript_parse": "155-159 (role defaults to 'agent' if missing)",
        },
    },
}


# =============================================================================
# CONSTRAINTS & GOTCHAS
# =============================================================================

CONSTRAINTS = [
    "Gemini Live API send_content() ONLY supports role='user' and role='model'."
    " There is NO role='system'. All context must go as role='user'.",

    "VAD configuration (start_sensitivity, end_sensitivity, silence_duration_ms)"
    " can ONLY be set at session creation via RunConfig.realtime_input_config."
    " It CANNOT be changed mid-session. ADK 1.25.x LiveRequestQueue does not"
    " expose transport-level config updates.",

    "proactive_audio=True is set in RunConfig and cannot be toggled mid-session.",

    "The model is 'gemini-2.5-flash-native-audio-preview-12-2025' — a native"
    " audio model. It processes audio directly (not ASR→LLM→TTS). Behavior"
    " around <think> blocks and text-level instructions may differ from"
    " text-only models.",

    "parse_telemetry() (model-facing) and parse_telemetry_to_ephemeral() (LOD"
    " engine-facing) are TWO SEPARATE functions. Only parse_telemetry() needs"
    " to change format. parse_telemetry_to_ephemeral() feeds the LOD decision"
    " engine and must remain structured dataclass output.",

    "numpy < 2.0 is required (insightface). Use google-genai not google-generativeai.",

    "Conda env: sightline (Python 3.12.12). Path: /opt/anaconda3/envs/sightline/",

    "Tests: SightLineTests (unit/integration, Swift Testing + XCTest)."
    " Run with xcodebuild or Xcode. Python tests via pytest.",
]


# =============================================================================
# EXISTING REPEAT-SUPPRESSION MECHANISMS (don't duplicate these)
# =============================================================================
#
# The codebase already has several dedup mechanisms. Be aware of them:
#
# 1. _forward_agent_transcript() — server.py:687-710
#    Suppresses repeated agent text within AGENT_TEXT_REPEAT_SUPPRESS_SEC (14s)
#    Uses _normalize_text_for_dedupe() for fuzzy matching.
#
# 2. _is_repeated_text() — server.py:135-155
#    Generic repeat checker used for vision (18s), OCR (20s), and agent text.
#    Normalizes text (lowercase, strip punctuation, collapse whitespace).
#
# 3. _should_inject_telemetry_context() — server.py:232-252
#    Only injects telemetry when meaningful fields change OR periodic refresh.
#    Uses bucket-based signatures (hr_bucket, noise_bucket, etc.).
#
# 4. TelemetryAggregator — lod/telemetry_aggregator.py
#    LOD-aware throttle: LOD 1 = 3-4s, LOD 2 = 2-3s, LOD 3 = 5-10s.
#
# These are INSUFFICIENT because:
#   - They prevent duplicate INJECTION but not duplicate MODEL OUTPUT
#   - The model can still parrot freshly-injected (non-duplicate) context
#   - No mechanism prevents the model from vocalizing context data
