"""
SightLine Interaction Issues — Root Cause Analysis & Fix Plan
=============================================================
Date: 2026-02-26
Author: Deep investigation session
Purpose: Self-contained context for the next agent to implement fixes.

Three issues reported:
  (a) Model can't accurately determine when to stop/start speaking
  (b) Context injection too invasive — model parrots scene/heart-rate data
  (c) Role identification errors — user speech labeled as model speech in System Log

This file is structured so an agent can read ONLY this file + the referenced
source locations and implement all fixes without any additional context.
"""

# =============================================================================
# ISSUE (a): MODEL CANNOT ACCURATELY DETERMINE WHEN TO STOP/START SPEAKING
# =============================================================================
#
# ROOT CAUSE 1: VAD is NOT hot-reconfigurable
# --------------------------------------------
# File: SightLine/live_api/session_manager.py
#
# Lines 139-152: supports_runtime_vad_reconfiguration() returns (False, ...).
# ADK 1.25.x LiveRequestQueue only supports content and activity signals,
# NOT realtime_input_config updates. This means:
#   - VAD params (start_sensitivity, end_sensitivity, silence_duration_ms)
#     are ONLY applied once at session creation via get_run_config().
#   - All [VAD UPDATE] text messages injected on LOD transitions (server.py:862-866)
#     have ZERO effect on actual VAD behavior — they're just text markers.
#   - Whatever LOD is active at session start determines VAD for the entire session.
#
# ROOT CAUSE 2: LOD 2 VAD preset is poorly balanced
# --------------------------------------------------
# File: SightLine/live_api/session_manager.py, lines 109-117
#
# Current LOD 2 preset:
#   start_sensitivity = START_SENSITIVITY_HIGH   (triggers easily on any sound)
#   end_sensitivity   = END_SENSITIVITY_LOW      (requires LONG silence to end)
#   silence_duration_ms = 800
#
# Problem: HIGH start + LOW end means the model:
#   - Easily starts listening (hears background noise as speech start)
#   - Takes too long to decide user finished speaking (waits for extended silence)
#   - Result: awkward pauses where model won't respond, or premature triggers
#
# ROOT CAUSE 3: proactive_audio=True + massive role="user" injections
# -------------------------------------------------------------------
# File: SightLine/live_api/session_manager.py, line 248
#   proactivity=types.ProactivityConfig(proactive_audio=True)
#
# Combined with every context injection being role="user" (see Issue b),
# the model interprets each injection as "user sent a message" and may
# proactively start speaking in response to telemetry/vision/LOD updates.


# =============================================================================
# ISSUE (b): CONTEXT INJECTION TOO INVASIVE — MODEL PARROTS SCENE/HR DATA
# =============================================================================
#
# ROOT CAUSE 1: ALL context injections use role="user"
# ----------------------------------------------------
# Gemini Live API's send_content() only supports role="user" or role="model".
# There is NO role="system". Every framework message looks like user speech:
#
# Injection point                  | File:Line                  | role
# ---------------------------------|----------------------------|------
# Initial full dynamic prompt      | server.py:792-796          | "user"
# LOD UPDATE                       | server.py:822-826          | "user"
# TELEMETRY (normal)               | server.py:1752-1763        | "user"
# TELEMETRY (PANIC)                | server.py:1726-1738        | "user"
# VISION ANALYSIS                  | server.py:1049-1053        | "user"
# OCR RESULT                       | server.py:1256-1260        | "user"
# FACE ID                          | server.py:1144-1148        | "user"
# VAD UPDATE                       | server.py:862-866          | "user"
# RESUME prompt                    | server.py:1795-1800        | "user"
# USER INTERRUPT                   | server.py:1574-1577        | "user"
# EMERGENCY PAUSE/RESUME           | server.py:1624-1642        | "user"
# Function responses               | server.py:1919-1923        | "user"
#
# ROOT CAUSE 2: Telemetry uses natural language format (easy to parrot)
# ---------------------------------------------------------------------
# File: SightLine/telemetry/telemetry_parser.py, lines 19-122
#
# parse_telemetry() generates complete sentences:
#   "The user is walking."
#   "Heart rate: 72 bpm (normal)."
#   "Environment is quiet (35 dB)."
#   "Facing North (350 degrees)."
#   "Location: (37.774929, -122.419416), accuracy 5m."
#   "Moving at 1.2 m/s."
#
# These natural language sentences are trivial for the model to echo.
# The "Do NOT speak, summarize, or repeat it aloud" instruction (server.py:1758)
# is unreliable because it's just a text-level instruction, not a hard constraint.
#
# ROOT CAUSE 3: Injection frequency is too high
# -----------------------------------------------
# File: SightLine/lod/telemetry_aggregator.py, lines 13-17
#   LOD 1: 3-4s interval
#   LOD 2: 2-3s interval  (midpoint 2.5s)
#   LOD 3: 5-10s interval
#
# File: SightLine/server.py, line 105
#   TELEMETRY_FORCE_REFRESH_SEC = 25.0  (forced refresh even if nothing changed)
#
# File: SightLine/server.py, line 1327
#   Vision interval at LOD 2 = 3.0s
#
# Combined: at LOD 2, the model receives ~1 context injection every 2-3 seconds
# (telemetry + vision + OCR overlapping). This floods the conversation context.
#
# ROOT CAUSE 4: CoT prompt leaks raw sensor values
# --------------------------------------------------
# File: SightLine/lod/prompt_builder.py, lines 69-80
#
# LOD_COT_PROMPT includes:
#   "1. User physical state: {motion_state} at {cadence:.0f} steps/min"
#   "2. Environment: {noise_db:.0f} dB, {space_type}"
#
# Despite "Do NOT output the <think> block", native audio models may leak
# these explicit numeric values (72 bpm, 35 dB, etc.) into speech output.


# =============================================================================
# ISSUE (c): ROLE IDENTIFICATION ERRORS (USER SPEECH LABELED AS MODEL SPEECH)
# =============================================================================
#
# ROOT CAUSE 1: No echo detection on the server
# -----------------------------------------------
# File: SightLine/server.py, lines 1926-1946
#
# The downstream loop checks input_transcription and output_transcription
# independently on EVERY event with no mutual exclusion:
#
#   if event.input_transcription and event.input_transcription.text:
#       → labeled "user", sent to iOS
#
#   if event.output_transcription and event.output_transcription.text:
#       → labeled "agent", sent to iOS
#
# Acoustic echo scenario:
#   1. Model generates audio → sent to iOS → played on speaker
#   2. Speaker audio picked up by iPhone microphone
#   3. Microphone audio sent to Gemini as input
#   4. Gemini's VAD classifies it as user speech
#   5. input_transcription contains MODEL's words → labeled "user"
#
# Reverse scenario (user speech labeled as model):
#   1. User speaks during model output (barge-in)
#   2. Audio streams overlap in Gemini's processing
#   3. Part of user's audio attributed to output_transcription
#   4. User's words labeled "agent" in the transcript
#
# ROOT CAUSE 2: No similarity check between input/output transcriptions
# ----------------------------------------------------------------------
# If the same text appears in both streams (due to echo), both are sent
# to iOS independently — one as "user", one as "agent". No deduplication.
#
# ROOT CAUSE 3: iOS client does no echo filtering
# -------------------------------------------------
# File: SightLine/SightLine/UI/MainView.swift, lines 477-485
#
#   case .transcript(let text, let role):
#       transcript = text
#       devConsoleModel.captureTranscript(text: text, role: role)
#
# No check for: "is audioPlayback.isPlaying when we receive role='user'?"
# A role="user" transcript while the model is playing audio is very likely echo.


# =============================================================================
# FIX PLAN — ORDERED BY PRIORITY
# =============================================================================

FIXES = {
    # =========================================================================
    # P0 — Critical (fixes root causes directly)
    # =========================================================================

    "P0_FIX_1": {
        "title": "Optimize LOD 2 VAD preset — end_sensitivity LOW→HIGH",
        "issue": "(a)",
        "file": "SightLine/live_api/session_manager.py",
        "location": "LOD_VAD_PRESETS dict, lines ~102-127",
        "change": """
Replace the LOD 2 preset:

BEFORE:
    2: {
        "voice_name": "Aoede",
        "start_sensitivity": types.StartSensitivity.START_SENSITIVITY_HIGH,
        "end_sensitivity": types.EndSensitivity.END_SENSITIVITY_LOW,
        "silence_duration_ms": 800,
        "prefix_padding_ms": 200,
    },

AFTER:
    2: {
        "voice_name": "Aoede",
        "start_sensitivity": types.StartSensitivity.START_SENSITIVITY_HIGH,
        "end_sensitivity": types.EndSensitivity.END_SENSITIVITY_HIGH,
        "silence_duration_ms": 1000,
        "prefix_padding_ms": 250,
    },

Also increase LOD 3 silence_duration_ms from 1300 to 1500.

Rationale:
  - end_sensitivity HIGH lets the model decide "user is done" faster
  - silence_duration_ms 800→1000 gives users natural pause room
  - Fixes the awkward "model won't respond" delay
""",
    },

    "P0_FIX_2": {
        "title": "Convert telemetry to structured KV format (anti-parrot)",
        "issue": "(b)",
        "file": "SightLine/telemetry/telemetry_parser.py",
        "location": "parse_telemetry() function, lines 19-122",
        "change": """
Replace the natural language output with a structured KV format that is
much harder for the model to echo verbatim.

BEFORE (example output):
    "[TELEMETRY UPDATE] The user is walking. Step cadence: 85 steps/min. "
    "Heart rate: 72 bpm (normal). Environment is quiet (35 dB). "
    "Facing North (350 degrees)."

AFTER (example output):
    "[TELEMETRY UPDATE] motion=walking cadence=85spm hr=72/normal "
    "noise=35dB/quiet heading=N/350 speed=1.2m/s loc=37.77,-122.42"

Implementation: rewrite parse_telemetry() to build KV pairs.
Key format rules:
  - Use key=value pairs separated by spaces
  - Bucket values where possible: hr=72/normal, noise=35dB/quiet
  - No complete sentences, no "The user is..."
  - Keep the [TELEMETRY UPDATE] prefix for model recognition

Full replacement code for parse_telemetry():

    def parse_telemetry(data: dict) -> str:
        parts: list[str] = []

        motion_state = data.get("motion_state")
        if motion_state:
            parts.append(f"motion={motion_state}")

        step_cadence = data.get("step_cadence")
        if step_cadence is not None:
            try:
                cadence = float(step_cadence)
                if cadence > 0:
                    parts.append(f"cadence={cadence:.0f}spm")
            except (ValueError, TypeError):
                pass

        ambient_noise_db = data.get("ambient_noise_db")
        if ambient_noise_db is not None:
            try:
                noise = float(ambient_noise_db)
                if noise < 40:
                    bucket = "quiet"
                elif noise < 65:
                    bucket = "moderate"
                elif noise < 80:
                    bucket = "noisy"
                else:
                    bucket = "very_loud"
                parts.append(f"noise={noise:.0f}dB/{bucket}")
            except (ValueError, TypeError):
                pass

        heart_rate = data.get("heart_rate")
        if heart_rate is not None:
            try:
                hr = float(heart_rate)
                if hr > 0:
                    if hr > 120:
                        bucket = "PANIC"
                    elif hr > 100:
                        bucket = "elevated"
                    else:
                        bucket = "normal"
                    parts.append(f"hr={hr:.0f}/{bucket}")
            except (ValueError, TypeError):
                pass

        gps = data.get("gps")
        if gps and isinstance(gps, dict):
            lat = gps.get("latitude")
            lon = gps.get("longitude")
            if lat is not None and lon is not None:
                parts.append(f"loc={lat:.4f},{lon:.4f}")
            speed = gps.get("speed")
            if speed is not None:
                try:
                    spd = float(speed)
                    if spd > 0:
                        parts.append(f"speed={spd:.1f}m/s")
                except (ValueError, TypeError):
                    pass

        heading = data.get("heading")
        if heading is not None:
            try:
                h = float(heading)
                cardinal = _degrees_to_cardinal(h)
                parts.append(f"heading={cardinal}/{h:.0f}")
            except (ValueError, TypeError):
                pass

        time_context = data.get("time_context")
        if time_context and time_context != "unknown":
            parts.append(f"time={time_context}")

        device_type = data.get("device_type")
        if device_type and device_type != "phone_only":
            parts.append(f"device={device_type}")

        if not parts:
            return "[TELEMETRY UPDATE] no_data"

        return "[TELEMETRY UPDATE] " + " ".join(parts)

NOTE: parse_telemetry_to_ephemeral() is UNCHANGED — it feeds the LOD engine,
not the model prompt. Only parse_telemetry() (model-facing text) needs changes.
""",
    },

    "P0_FIX_3": {
        "title": "Add server-side echo detection for transcription",
        "issue": "(c)",
        "file": "SightLine/server.py",
        "location": "Inside websocket_endpoint(), near downstream handler lines 1926-1946",
        "change": """
Add echo detection state and a similarity helper near the top of the
websocket_endpoint function (after the existing state variables around line 655):

    # -- Echo detection state (Issue c fix) --
    _recent_agent_texts: list[str] = []
    _ECHO_WINDOW_SIZE = 8                   # keep last N agent utterances
    _ECHO_SIMILARITY_THRESHOLD = 0.6        # suppress if > 60% similar
    _last_output_ts: float = 0.0
    _ECHO_TIME_WINDOW_SEC = 5.0             # only check within 5s of last output

Add a helper function (inside websocket_endpoint, near _forward_agent_transcript):

    def _is_likely_echo(candidate: str) -> bool:
        '''Check if candidate input_transcription is likely an echo of recent model output.'''
        if not _recent_agent_texts:
            return False
        now_mono = time.monotonic()
        if now_mono - _last_output_ts > _ECHO_TIME_WINDOW_SEC:
            return False
        candidate_lower = candidate.strip().lower()
        if len(candidate_lower) < 5:
            return False
        for recent in _recent_agent_texts:
            recent_lower = recent.strip().lower()
            # Substring containment check (catches partial echo)
            if candidate_lower in recent_lower or recent_lower in candidate_lower:
                return True
            # Word-level Jaccard similarity
            candidate_words = set(candidate_lower.split())
            recent_words = set(recent_lower.split())
            if not candidate_words or not recent_words:
                continue
            intersection = candidate_words & recent_words
            union = candidate_words | recent_words
            similarity = len(intersection) / len(union)
            if similarity > _ECHO_SIMILARITY_THRESHOLD:
                return True
        return False

Then modify the downstream transcription handling (lines 1926-1946):

BEFORE:
    # --- Input transcription (user speech-to-text) ---
    if event.input_transcription and event.input_transcription.text:
        transcript_history.append({
            "role": "user",
            "text": event.input_transcription.text,
        })
        if not await _safe_send_json({
            "type": "transcript",
            "text": event.input_transcription.text,
            "role": "user",
        }):
            break

    # --- Output transcription (agent speech-to-text) ---
    if event.output_transcription and event.output_transcription.text:
        transcript_history.append({
            "role": "agent",
            "text": event.output_transcription.text,
        })
        if not await _forward_agent_transcript(event.output_transcription.text):
            break

AFTER:
    # --- Output transcription FIRST (establishes echo baseline) ---
    if event.output_transcription and event.output_transcription.text:
        nonlocal _last_output_ts
        out_text = event.output_transcription.text
        transcript_history.append({
            "role": "agent",
            "text": out_text,
        })
        _recent_agent_texts.append(out_text)
        if len(_recent_agent_texts) > _ECHO_WINDOW_SIZE:
            _recent_agent_texts.pop(0)
        _last_output_ts = time.monotonic()
        if not await _forward_agent_transcript(out_text):
            break

    # --- Input transcription WITH echo detection ---
    if event.input_transcription and event.input_transcription.text:
        in_text = event.input_transcription.text
        if _is_likely_echo(in_text):
            logger.debug("Suppressed echo input_transcription: %s", in_text[:100])
        else:
            transcript_history.append({
                "role": "user",
                "text": in_text,
            })
            if not await _safe_send_json({
                "type": "transcript",
                "text": in_text,
                "role": "user",
            }):
                break

KEY CHANGES:
  1. Process output_transcription BEFORE input_transcription (establishes baseline)
  2. Maintain a sliding window of recent agent texts
  3. Compare each input_transcription against recent agent output
  4. Suppress input that is likely echo (>60% word similarity within 5s window)
  5. Log suppressed echoes for debugging
""",
    },

    # =========================================================================
    # P1 — Important (strengthens the fixes, reduces recurrence)
    # =========================================================================

    "P1_FIX_1": {
        "title": "Reduce telemetry injection frequency",
        "issue": "(b)",
        "file": "SightLine/server.py",
        "location": "Lines 105-107 (constants) and _process_telemetry() lines 1711-1769",
        "change": """
1. Increase force-refresh interval:
   TELEMETRY_FORCE_REFRESH_SEC = 25.0  →  TELEMETRY_FORCE_REFRESH_SEC = 60.0

2. In _should_inject_telemetry_context(), remove the periodic refresh fallback
   and only inject on actual meaningful changes. Replace lines 249-250:

   BEFORE:
       if now_ts - last_injected_ts >= force_refresh_sec:
           return True, ["periodic_refresh"]

   AFTER:
       # Periodic refresh only as emergency fallback after 2 minutes
       if now_ts - last_injected_ts >= 120.0:
           return True, ["emergency_refresh"]

3. Increase vision interval at LOD 2 from 3.0 to 5.0:
   In server.py lines 1327 and 1410:
   BEFORE: vision_interval = {1: 5.0, 2: 3.0, 3: 2.0}.get(lod, 3.0)
   AFTER:  vision_interval = {1: 8.0, 2: 5.0, 3: 3.0}.get(lod, 5.0)
""",
    },

    "P1_FIX_2": {
        "title": "Add NEVER ECHO CONTEXT rule to orchestrator system prompt",
        "issue": "(b)",
        "file": "SightLine/agents/orchestrator.py",
        "location": "SYSTEM_PROMPT constant, after line 66 (after principle 7)",
        "change": """
Add principle 8 after principle 7 in the SYSTEM_PROMPT:

8. NEVER ECHO CONTEXT — Messages tagged with [TELEMETRY UPDATE], \\
   [VISION ANALYSIS], [OCR RESULT], [FACE ID], [LOD UPDATE], [VAD UPDATE], \\
   or [CTX] are INTERNAL sensor data for your background awareness ONLY. \\
   NEVER read, summarize, paraphrase, or reference the raw data from these \\
   messages in your speech output. If the user asks about their heart rate, \\
   surroundings, or location, answer naturally using your understanding — \\
   but NEVER parrot the structured format (e.g., never say "motion equals \\
   walking" or "heart rate 72 bpm normal").
""",
    },

    "P1_FIX_3": {
        "title": "Remove raw sensor values from CoT prompt",
        "issue": "(b)",
        "file": "SightLine/lod/prompt_builder.py",
        "location": "LOD_COT_PROMPT constant, lines 69-80",
        "change": """
BEFORE:
    LOD_COT_PROMPT = (
        "Before responding, internally reason about the right response depth:\\n"
        "<think>\\n"
        "1. User physical state: {motion_state} at {cadence:.0f} steps/min\\n"
        "2. Environment: {noise_db:.0f} dB, {space_type}\\n"
        "3. Current task: {active_task}\\n"
        "4. Persona: {vision_status}, verbosity={verbosity}, O&M={om_level}\\n"
        "→ Respond at LOD {lod} because {reason}\\n"
        "</think>\\n"
        "Then respond according to LOD {lod}. "
        "Do NOT output the <think> block — it is for internal reasoning only."
    )

AFTER:
    LOD_COT_PROMPT = (
        "Before responding, silently decide response depth:\\n"
        "- Is the user moving or still?\\n"
        "- Is the environment noisy or quiet?\\n"
        "- What is the current task?\\n"
        "→ Respond at LOD {lod}.\\n"
        "Do NOT vocalize this reasoning."
    )

Also update the build_lod_update_message() call site (lines 206-218) to
stop passing raw sensor values. The new CoT_PROMPT only uses {lod},
so remove the .format() kwargs for motion_state, cadence, noise_db,
space_type, active_task, vision_status, verbosity, om_level, reason.

New format call:
    cot = LOD_COT_PROMPT.format(lod=lod)
""",
    },

    "P1_FIX_4": {
        "title": "Wrap telemetry injection with stronger boundary markers",
        "issue": "(b)",
        "file": "SightLine/server.py",
        "location": "Lines 1751-1763 (normal telemetry) and 1726-1738 (PANIC telemetry)",
        "change": """
BEFORE (normal telemetry, lines 1754-1760):
    text=(
        "[TELEMETRY CONTEXT - INTERNAL ONLY]\\n"
        "This is passive sensor context. Do NOT speak, summarize, or repeat it aloud.\\n"
        "Use it silently unless there is a new immediate safety hazard.\\n"
        f"{semantic_text}"
    )

AFTER:
    text=(
        "<<<SENSOR_DATA>>>\\n"
        f"{semantic_text}\\n"
        "<<<END_SENSOR_DATA>>>\\n"
        "INSTRUCTION: Do not vocalize any part of the above sensor data."
    )

BEFORE (PANIC telemetry, lines 1729-1733):
    text=(
        "[TELEMETRY CONTEXT - CRITICAL]\\n"
        "PANIC-related sensor context follows. Keep responses calming and brief.\\n"
        f"{semantic_text}"
    )

AFTER:
    text=(
        "<<<SENSOR_DATA_CRITICAL>>>\\n"
        f"{semantic_text}\\n"
        "<<<END_SENSOR_DATA>>>\\n"
        "PANIC detected. Switch to ultra-brief calming mode."
    )

Rationale: Angle-bracket delimiters are harder to accidentally vocalize
than English-word headers like "[TELEMETRY CONTEXT - INTERNAL ONLY]".
""",
    },

    # =========================================================================
    # P2 — Nice to have (defense in depth)
    # =========================================================================

    "P2_FIX_1": {
        "title": "Conditionally disable proactive_audio at LOD 1",
        "issue": "(a)",
        "file": "SightLine/live_api/session_manager.py",
        "location": "get_run_config() method, around line 248",
        "change": """
BEFORE:
    proactivity=types.ProactivityConfig(proactive_audio=True),

AFTER:
    proactivity=types.ProactivityConfig(proactive_audio=(lod >= 2)),

NOTE: Since VAD can't be hot-reconfigured, this only affects session start.
If most sessions start at LOD 2, this change has limited impact. But it
prevents LOD 1 sessions from having unwanted proactive model speech.
""",
    },

    "P2_FIX_2": {
        "title": "iOS-side echo filtering in transcript display",
        "issue": "(c)",
        "file": "SightLine/SightLine/UI/MainView.swift",
        "location": "handleDownstreamMessage(), around lines 477-485",
        "change": """
Add a simple echo filter: if model is currently playing audio and we
receive a role="user" transcript, mark it as suspicious.

BEFORE:
    case .transcript(let text, let role):
        DispatchQueue.main.async {
            transcript = text
            if role == "agent" {
                lastAgentTranscript = text
            }
            devConsoleModel.captureTranscript(text: text, role: role)
            drainWhenIdleToolQueueIfPossible()
        }

AFTER:
    case .transcript(let text, let role):
        DispatchQueue.main.async {
            // Echo filter: user transcript while model is playing = likely echo
            let effectiveRole: String
            if role == "user" && audioPlayback.isPlaying {
                effectiveRole = "echo"
                Self.logger.debug("Suppressed likely echo transcript: \\(text.prefix(80))")
            } else {
                effectiveRole = role
                transcript = text
            }
            if effectiveRole == "agent" {
                lastAgentTranscript = text
            }
            devConsoleModel.captureTranscript(text: text, role: effectiveRole)
            if effectiveRole != "echo" {
                drainWhenIdleToolQueueIfPossible()
            }
        }

Also update DeveloperConsoleView.swift to show "echo" role in a distinct color
(e.g., gray/dimmed) so it's visible in debug but clearly marked:

In the transcript display section (around line 520):
    .foregroundColor(
        entry.role == "user" ? .cyan :
        entry.role == "agent" ? .green :
        entry.role == "echo" ? .gray :
        .white
    )
""",
    },

    "P2_FIX_3": {
        "title": "Suppress context injection while model is generating audio",
        "issue": "(a)(b)",
        "file": "SightLine/server.py",
        "location": "_process_telemetry() and downstream handler",
        "change": """
Add a shared flag to track model speaking state:

    _model_is_generating_audio = False

In the downstream handler, set the flag when audio content is sent:
    if part.inline_data and part.inline_data.data:
        _model_is_generating_audio = True
        # ... send audio ...

Clear it when model output ends (e.g., when no audio parts in event).
Use an asyncio task with timeout as fallback.

In _process_telemetry(), skip non-critical injections when flag is True:
    if _model_is_generating_audio and not is_panic:
        logger.debug("Skipping telemetry injection: model is generating audio")
        return

This prevents context injections from interrupting model speech, which
reduces both the "model starts/stops awkwardly" and "model parrots context"
problems.
""",
    },
}


# =============================================================================
# IMPLEMENTATION ORDER
# =============================================================================
#
# Step 1: P0_FIX_1 — VAD preset (session_manager.py) — 5 min
# Step 2: P0_FIX_2 — Telemetry KV format (telemetry_parser.py) — 15 min
# Step 3: P0_FIX_3 — Echo detection (server.py) — 20 min
# Step 4: P1_FIX_1 — Reduce injection frequency (server.py) — 5 min
# Step 5: P1_FIX_2 — NEVER ECHO CONTEXT rule (orchestrator.py) — 5 min
# Step 6: P1_FIX_3 — CoT prompt cleanup (prompt_builder.py) — 10 min
# Step 7: P1_FIX_4 — Boundary markers (server.py) — 5 min
# Step 8: P2_FIX_1 — Conditional proactive_audio (session_manager.py) — 2 min
# Step 9: P2_FIX_2 — iOS echo filter (MainView.swift, DeveloperConsoleView.swift) — 10 min
# Step 10: P2_FIX_3 — Audio generation suppression (server.py) — 15 min
#
# Total estimated: ~90 min
#
# =============================================================================
# FILES TOUCHED (summary for quick reference)
# =============================================================================
#
# Python (backend):
#   SightLine/live_api/session_manager.py    — P0_FIX_1, P2_FIX_1
#   SightLine/telemetry/telemetry_parser.py  — P0_FIX_2
#   SightLine/server.py                      — P0_FIX_3, P1_FIX_1, P1_FIX_4, P2_FIX_3
#   SightLine/agents/orchestrator.py         — P1_FIX_2
#   SightLine/lod/prompt_builder.py          — P1_FIX_3
#
# Swift (iOS):
#   SightLine/SightLine/UI/MainView.swift              — P2_FIX_2
#   SightLine/SightLine/UI/DeveloperConsoleView.swift   — P2_FIX_2
#
# =============================================================================
# TESTING PLAN
# =============================================================================
#
# 1. Unit tests for echo detection:
#    - Test _is_likely_echo() with identical text → should return True
#    - Test with substring match → True
#    - Test with >60% Jaccard similarity → True
#    - Test with completely different text → False
#    - Test with expired time window → False
#
# 2. Unit tests for KV telemetry format:
#    - Test parse_telemetry() outputs KV format, not sentences
#    - Test all field types (motion, hr, noise, gps, heading)
#    - Test edge cases (None values, zero values)
#
# 3. Integration test:
#    - Start a session, verify VAD params in RunConfig match new presets
#    - Send telemetry, verify injected text is KV format
#    - Simulate echo scenario, verify suppression in transcript
#
# 4. Manual test (requires device):
#    - Check Developer Console Log tab for correct role labels
#    - Verify model no longer parrots "heart rate 72 bpm"
#    - Verify model responds promptly after user finishes speaking
