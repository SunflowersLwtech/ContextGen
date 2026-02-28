# Experience-First Refactor + Watch Context Expansion

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove all safety-oriented code (PANIC, SOS, safety guardrails) and reposition the system as an experience-enhancement companion, then expand Watch sensor context (motion, heading, SpO2, noise) to enrich AI responses.

**Architecture:** Three parallel tracks — (A) Backend: remove safety code, rewrite LOD/prompts to experience-first, expand telemetry parsing; (B) iOS: remove safety UI/messages, expand TelemetryData and WatchReceiver; (C) watchOS: add CMMotionManager, CLLocationManager heading, HealthKit SpO2/noise queries, expand PhoneConnector payload.

**Tech Stack:** Python 3.12 (FastAPI/ADK), Swift/SwiftUI (iOS 18+, watchOS 11+), HealthKit, CoreMotion, CoreLocation, WatchConnectivity

---

## Shared Interface Contracts

All three tracks depend on these contracts. Define them first so tracks can work independently.

### WCSession Payload (Watch → iPhone)

Current payload: `{"heartRate": Double, "ts": Double, "isMonitoring": Bool}`

New payload (backward compatible — iPhone checks for new keys):
```json
{
  "heartRate": 72.0,
  "ts": 1709136000.0,
  "isMonitoring": true,
  "motion": {
    "accelMagnitude": 1.02,
    "pitch": -0.15,
    "roll": 0.03,
    "yaw": 1.57,
    "stabilityScore": 0.85
  },
  "heading": 245.0,
  "headingAccuracy": 8.0,
  "spO2": 97.0,
  "noiseExposure": 72.0
}
```

- `motion`: Present only when CMMotionManager is active. `stabilityScore` = 1.0 (perfectly stable) to 0.0 (very unstable), computed on-watch from accel variance over 2s window.
- `heading` / `headingAccuracy`: Present only when CLLocationManager heading is available. Degrees 0-360.
- `spO2`: Latest from HealthKit, may be hours old. `null` if unavailable.
- `noiseExposure`: Latest from HealthKit `environmentalAudioExposure`, in dB. `null` if unavailable.

### TelemetryData JSON (iPhone → Backend)

New fields added to existing struct:
```json
{
  "...existing fields...",
  "watch_pitch": -0.15,
  "watch_roll": 0.03,
  "watch_yaw": 1.57,
  "watch_stability_score": 0.85,
  "watch_heading": 245.0,
  "watch_heading_accuracy": 8.0,
  "sp_o2": 97.0,
  "watch_noise_exposure": 72.0
}
```

### EphemeralContext (Backend Model)

New fields:
```python
watch_pitch: float = 0.0
watch_roll: float = 0.0
watch_yaw: float = 0.0
watch_stability_score: float = 1.0
watch_heading: Optional[float] = None
watch_heading_accuracy: Optional[float] = None
sp_o2: Optional[float] = None
watch_noise_exposure: Optional[float] = None
```

---

## Track A: Backend Refactor (Python)

### Task A1: Delete panic_handler.py and its test

**Files:**
- Delete: `SightLine/lod/panic_handler.py`
- Delete: `SightLine/tests/test_panic_handler.py`
- Modify: `SightLine/lod/__init__.py`

**Step 1: Remove PanicHandler from `__init__.py`**

In `SightLine/lod/__init__.py`, remove:
```python
from lod.panic_handler import PanicHandler
```
And remove `"PanicHandler"` from `__all__`.

**Step 2: Delete files**

```bash
rm SightLine/lod/panic_handler.py
rm SightLine/tests/test_panic_handler.py
```

**Step 3: Run tests to check no imports break**

```bash
cd SightLine && /opt/anaconda3/envs/sightline/bin/python -m pytest tests/ -x -q 2>&1 | head -30
```

**Step 4: Commit**

```bash
git add -A && git commit -m "refactor: remove PanicHandler module and tests"
```

---

### Task A2: Remove PANIC/safety rules from lod_engine.py

**Files:**
- Modify: `SightLine/lod/lod_engine.py`

**Step 1: Remove `safety_warning` override in `should_speak()`**

Replace lines 82-101 (`INFO_VALUES` dict and the `if info_value >= 10.0` bypass):

Old:
```python
INFO_VALUES: dict[str, float] = {
    "safety_warning": 10.0,
    "navigation": 8.0,
    "face_recognition": 7.0,
    "spatial_description": 5.0,
    "object_enumeration": 3.0,
    "atmosphere": 1.0,
}


def should_speak(
    info_type: str,
    current_lod: int,
    step_cadence: float = 0.0,
    ambient_noise_db: float = 70.0,
) -> bool:
    """Determine whether the agent should vocalise this information."""
    info_value = INFO_VALUES.get(info_type, 1.0)
    if info_value >= 10.0:
        return True  # safety always speaks
```

New:
```python
INFO_VALUES: dict[str, float] = {
    "navigation": 8.0,
    "face_recognition": 7.0,
    "spatial_description": 5.0,
    "object_enumeration": 3.0,
    "atmosphere": 1.0,
}


def should_speak(
    info_type: str,
    current_lod: int,
    step_cadence: float = 0.0,
    ambient_noise_db: float = 70.0,
) -> bool:
    """Determine whether the agent should vocalise this information."""
    info_value = INFO_VALUES.get(info_type, 1.0)
```

**Step 2: Remove Rule 0 (PANIC flag) and Rule 1 (HR > 120) from `decide_lod()`**

Delete lines 191-205 entirely (Rule 0 + Rule 1):
```python
    # ── Rule 0: Explicit PANIC flag from iOS ──────────────────────────
    if panic:
        ...
        return 1, log

    # ── Rule 1: Heart-rate PANIC (only if watch connected) ────────────
    if heart_rate is not None and heart_rate > 120:
        ...
        return 1, log
```

**Step 3: Rewrite Rule 2 motion mapping (walking → LOD 2, not LOD 1)**

Old (lines 207-226):
```python
    if motion_state == "running" or step_cadence >= 120:
        base_lod = 1
        log.triggered_rules.append("Rule2:running→LOD1")
    elif motion_state == "walking":
        if step_cadence < 60:
            base_lod = 2
            log.triggered_rules.append("Rule2:slow_walk(<60spm)→LOD2")
        else:
            base_lod = 1
            log.triggered_rules.append("Rule2:walking(≥60spm)→LOD1")
    elif motion_state == "in_vehicle":
        base_lod = 3
        log.triggered_rules.append("Rule2:in_vehicle→LOD3")
    elif motion_state == "cycling":
        base_lod = 1
        log.triggered_rules.append("Rule2:cycling→LOD1")
    else:  # stationary
        base_lod = 3
        log.triggered_rules.append("Rule2:stationary→LOD3")
```

New:
```python
    # ── Rule 1: Motion-state baseline (experience-driven) ───────────
    if motion_state == "running" or step_cadence >= 120:
        base_lod = 1  # brief — user is busy moving fast
        log.triggered_rules.append("Rule1:running→LOD1(brief)")
    elif motion_state == "walking":
        base_lod = 2  # standard — user can listen while walking
        log.triggered_rules.append("Rule1:walking→LOD2")
    elif motion_state == "cycling":
        base_lod = 1  # brief — user is busy
        log.triggered_rules.append("Rule1:cycling→LOD1(brief)")
    elif motion_state == "in_vehicle":
        base_lod = 3  # detailed — user has attention available
        log.triggered_rules.append("Rule1:in_vehicle→LOD3")
    else:  # stationary
        base_lod = 3  # detailed — user is relaxed
        log.triggered_rules.append("Rule1:stationary→LOD3")
```

**Step 4: Update docstring at top of file**

Replace the decision priority comment (lines 6-13):

Old:
```python
Decision priority (high -> low):
    1. PANIC interrupt (heart_rate > 120)
    2. Motion-state baseline
    3. Ambient noise override
    4. Space transition boost
    5. User verbosity preference
    6. O&M level adjustment
    7. Explicit user override (final)
```

New:
```python
Decision priority (high -> low):
    1. Motion-state baseline (experience-driven)
    2. Ambient noise adjustment
    3. Space transition boost
    4. User verbosity preference
    5. O&M level adjustment
    6. Explicit user override (final)
```

**Step 5: Renumber remaining rules in decide_lod() comments**

Update all `Rule3:` → `Rule2:`, `Rule4:` → `Rule3:`, etc. in the triggered_rules strings.

**Step 6: Remove `panic` field from `LODDecisionLog.to_debug_dict()`**

Remove `"panic": self.panic,` from the dict (line 71).

**Step 7: Run tests**

```bash
cd SightLine && /opt/anaconda3/envs/sightline/bin/python -m pytest tests/test_lod_engine.py -v
```

Fix any tests that assert PANIC behavior — they should be removed or rewritten.

**Step 8: Commit**

```bash
git add -A && git commit -m "refactor: remove PANIC/safety rules from LOD engine, rewrite motion→LOD as experience-driven"
```

---

### Task A3: Rewrite prompt_builder.py — remove safety guardrails

**Files:**
- Modify: `SightLine/lod/prompt_builder.py`

**Step 1: Rewrite LOD 1 instructions (line 37-43)**

Old:
```python
    1: (
        "LOD 1 -- SILENT / WHISPER mode.\n"
        "Rules: Stay silent OR say at most 1 sentence (15-40 words). "
        "Only communicate safety-critical information.\n"
        "Style: Brief, calm, do not demand attention.\n"
        "Examples: 'Steps ahead.' / 'Person approaching on your right.'\n"
        "If nothing is safety-critical, remain completely silent."
    ),
```

New:
```python
    1: (
        "LOD 1 -- BRIEF mode.\n"
        "Rules: Keep responses to 1-2 short sentences (15-40 words max).\n"
        "Style: Quick, clear, minimal. User is busy (moving fast or in a loud place).\n"
        "Examples: 'Cafe on your left, outdoor seating.' / 'Crosswalk ahead, sounds busy.'\n"
        "Focus on what's immediately useful. Skip atmosphere and detail."
    ),
```

**Step 2: Replace Safety Guardrails in `build_lod_update_message()` (lines 216-223)**

Old:
```python
    # 6. Safety guardrails (always)
    parts.append("\n## Safety Guardrails")
    parts.append(
        "- ALWAYS interrupt immediately for safety hazards (stairs, vehicles, obstacles).\n"
        "- If heart rate is elevated (>120 bpm), keep responses ultra-brief and calming.\n"
        "- Treat telemetry refreshes as silent context; do not speak them unless user asks.\n"
        "- Never describe colours to congenital-blind users unless explicitly asked."
    )
```

New:
```python
    # 6. Interaction guidelines
    parts.append("\n## Interaction Guidelines")
    parts.append(
        "- Treat telemetry refreshes as silent context; do not speak them unless user asks.\n"
        "- Never describe colours to congenital-blind users unless explicitly asked.\n"
        "- Match your verbosity to the LOD level. Do not over-explain at LOD 1."
    )
```

**Step 3: Replace Safety Guardrails in `build_full_dynamic_prompt()` (lines 317-326)**

Old:
```python
    # Safety guardrails
    parts.append("\n## Safety Guardrails")
    parts.append(
        "- ALWAYS interrupt for safety hazards regardless of LOD level.\n"
        "- If heart rate > 120 bpm: ultra-brief, calming responses only.\n"
        "- Treat telemetry/context refreshes as silent input; do not narrate them unless user asks.\n"
        "- Never describe colours to congenital-blind users.\n"
        "- When user says 'stop' or 'quiet': immediately go silent.\n"
        "- When user says 'tell me more' or 'details': switch to LOD 3."
    )
```

New:
```python
    # Interaction guidelines
    parts.append("\n## Interaction Guidelines")
    parts.append(
        "- Treat telemetry/context refreshes as silent input; do not narrate them unless user asks.\n"
        "- Never describe colours to congenital-blind users.\n"
        "- When user says 'stop' or 'quiet': immediately go silent.\n"
        "- When user says 'tell me more' or 'details': switch to LOD 3.\n"
        "- Match your verbosity to the LOD level. Do not over-explain at LOD 1."
    )
```

**Step 4: Replace "SAFETY FIRST" in `build_full_dynamic_prompt()` Core Principles (lines 261-268)**

Old:
```python
        "## Core Principles",
        "1. SAFETY FIRST — Immediately alert about hazards (stairs, vehicles, obstacles).",
        "2. SILENCE BY DEFAULT — Only speak when the information is genuinely useful.",
        "3. SINGLE VOICE — You are the only voice the user hears; be warm, concise, calm.",
        "4. PROACTIVE BUT EVENT-DRIVEN — alert on meaningful new changes, "
        "not periodic duplicate context updates.",
        "5. ADAPTIVE — Follow the LOD level set by the context engine.",
```

New:
```python
        "## Core Principles",
        "1. EXPERIENCE FIRST — Enrich the user's understanding of their surroundings.",
        "2. SILENCE BY DEFAULT — Only speak when the information is genuinely useful.",
        "3. SINGLE VOICE — You are the only voice the user hears; be warm, concise, calm.",
        "4. PROACTIVE BUT EVENT-DRIVEN — Alert on meaningful new changes, "
        "not periodic duplicate context updates.",
        "5. ADAPTIVE — Follow the LOD level set by the context engine.",
```

**Step 5: Run tests**

```bash
cd SightLine && /opt/anaconda3/envs/sightline/bin/python -m pytest tests/ -x -q 2>&1 | head -30
```

**Step 6: Commit**

```bash
git add -A && git commit -m "refactor: rewrite prompts from safety-first to experience-first"
```

---

### Task A4: Rewrite orchestrator.py SYSTEM_PROMPT

**Files:**
- Modify: `SightLine/agents/orchestrator.py`

**Step 1: Rewrite Core Principles (lines 59-61)**

Old:
```python
1. SAFETY FIRST — Immediately alert about hazards (stairs, vehicles, obstacles, \
   uneven ground).  This ALWAYS overrides any LOD level.
```

New:
```python
1. EXPERIENCE FIRST — Enrich the user's understanding of their surroundings. \
   Describe what matters most for the current moment and context.
```

**Step 2: Remove PANIC Protocol (lines 109-114)**

Delete the entire `## PANIC Protocol` section:
```python
## PANIC Protocol
If you see ``heart_rate > 120`` or a ``PANIC`` indicator:
- Switch to ultra-brief mode immediately.
- Say something calming: "You're safe. Take a slow breath."
- Only report immediate safety hazards.
- Do NOT ask unnecessary questions.
```

**Step 3: Rewrite Video Frame Analysis priority (lines 117-123)**

Old:
```python
When you see video frames, analyse for (in priority order):
1. Safety hazards (obstacles, vehicles, stairs, uneven ground)
2. Spatial layout (entrances, paths, furniture positions)
3. People (count, proximity, facing direction)
4. Readable text (signs, menus, labels)
5. Notable objects and atmosphere (only at LOD 3)
```

New:
```python
When you see video frames, analyse for (in priority order):
1. Spatial layout (entrances, paths, furniture positions)
2. People (count, proximity, facing direction)
3. Readable text (signs, menus, labels)
4. Notable objects and atmosphere (at LOD 2+)
```

**Step 4: Clean up "safety-critical" references in PROACTIVE rule (line 70)**

Old: `Alert only on meaningful new changes (especially safety-critical ones).`
New: `Alert only on meaningful new changes.`

**Step 5: Run tests**

```bash
cd SightLine && /opt/anaconda3/envs/sightline/bin/python -m pytest tests/ -x -q 2>&1 | head -30
```

**Step 6: Commit**

```bash
git add -A && git commit -m "refactor: rewrite orchestrator system prompt to experience-first"
```

---

### Task A5: Remove PANIC handling from server.py

**Files:**
- Modify: `SightLine/server.py`

**Step 1: Remove `_heart_rate_bucket` "panic" return (lines 487-494)**

Old:
```python
def _heart_rate_bucket(heart_rate: float | None) -> str:
    if heart_rate is None or heart_rate <= 0:
        return "unknown"
    if heart_rate > 120:
        return "panic"
    if heart_rate > 100:
        return "elevated"
    return "normal"
```

New:
```python
def _heart_rate_bucket(heart_rate: float | None) -> str:
    if heart_rate is None or heart_rate <= 0:
        return "unknown"
    if heart_rate > 100:
        return "elevated"
    return "normal"
```

**Step 2: Remove `_handle_panic` function (lines 1542-1569)**

Delete the entire function.

**Step 3: Remove SOS gesture handler (lines 2292-2296)**

Old:
```python
      elif gesture == "sos":
          logger.warning("SOS gesture received for session %s", session_id)
          ephemeral_ctx = session_manager.get_ephemeral_context(session_id)
          ephemeral_ctx.panic = True
          await _handle_panic(ephemeral_ctx)
```

Replace with: (just remove the block, the elif chain continues)

**Step 4: Rewrite emergency_pause handler (lines 2298-2310)**

Old:
```python
      elif gesture == "emergency_pause":
          paused = _coerce_bool(message.get("paused", True), default=True)
          ctx_queue.set_ios_playback_drained(True)
          if paused:
              old_lod = session_ctx.current_lod
              logger.warning("Emergency pause activated: LOD %d -> 1", old_lod)
              on_lod_change(session_ctx, old_lod, 1)
              session_ctx.current_lod = 1
              session_meta.record_lod_time(1)
              content = types.Content(
                  parts=[types.Part(text="[EMERGENCY PAUSE] The user has activated emergency pause. Switch to LOD 1 (safety-only mode). Go silent and only respond to direct safety-critical queries until further notice.")],
                  role="user",
```

New:
```python
      elif gesture == "pause":
          paused = _coerce_bool(message.get("paused", True), default=True)
          ctx_queue.set_ios_playback_drained(True)
          if paused:
              logger.info("Pause activated for session %s", session_id)
              content = types.Content(
                  parts=[types.Part(text="[PAUSE] The user has paused the session. Go silent until the user resumes.")],
                  role="user",
```

Note: The pause handler should NOT force LOD 1. It just silences the agent.

**Step 5: Remove PANIC check from `_process_telemetry` (lines 2500-2520)**

Delete the entire PANIC check block:
```python
      # Check PANIC first
      is_panic = panic_handler.evaluate(
          heart_rate=ephemeral_ctx.heart_rate,
          panic_flag=ephemeral_ctx.panic,
      )
      if is_panic:
          ...
          return
```

Also remove the `panic_handler` instantiation (search for `panic_handler = PanicHandler()` near the top of the WebSocket handler closure).

**Step 6: Remove `panic_handler` import**

Search for `from lod import PanicHandler` or `from lod.panic_handler import PanicHandler` and remove.

**Step 7: Clean up vision safety priority (lines 1672, 1686)**

Old:
```python
              info_type = "safety_warning" if warnings else "spatial_description"
              ...
              priority=2 if warnings else 5,
```

New:
```python
              info_type = "spatial_description"
              ...
              priority=5,
```

Remove the `warnings` variable and any `result.get("safety_warnings", [])` references in the vision handling section.

**Step 8: Run tests**

```bash
cd SightLine && /opt/anaconda3/envs/sightline/bin/python -m pytest tests/ -x -q 2>&1 | head -30
```

**Step 9: Commit**

```bash
git add -A && git commit -m "refactor: remove all PANIC handling from server"
```

---

### Task A6: Remove panic field from EphemeralContext model

**Files:**
- Modify: `SightLine/lod/models.py`

**Step 1: Remove `panic: bool = False` from EphemeralContext (line 47)**

Just delete the line. This may cause downstream references to break.

**Step 2: Search and fix all references to `ephemeral_ctx.panic` or `.panic`**

```bash
cd SightLine && grep -rn "\.panic" --include="*.py" | grep -v __pycache__ | grep -v test_panic
```

Remove or update each reference. Most should already be gone from Task A5.

**Step 3: Update telemetry_parser.py**

In `parse_telemetry_to_ephemeral()`, remove the line that sets `ctx.panic`:
```python
    # Remove: ctx.panic = bool(data.get("panic", False))
```

**Step 4: Run tests**

```bash
cd SightLine && /opt/anaconda3/envs/sightline/bin/python -m pytest tests/ -x -q 2>&1 | head -30
```

**Step 5: Commit**

```bash
git add -A && git commit -m "refactor: remove panic field from EphemeralContext"
```

---

### Task A7: Expand EphemeralContext with Watch context fields

**Files:**
- Modify: `SightLine/lod/models.py`
- Modify: `SightLine/telemetry/telemetry_parser.py`

**Step 1: Add new fields to EphemeralContext**

After the existing fields in `EphemeralContext`, add:
```python
    # Watch extended context
    watch_pitch: float = 0.0
    watch_roll: float = 0.0
    watch_yaw: float = 0.0
    watch_stability_score: float = 1.0  # 1.0 = stable, 0.0 = unstable
    watch_heading: Optional[float] = None  # magnetic heading from watch compass
    watch_heading_accuracy: Optional[float] = None
    sp_o2: Optional[float] = None  # blood oxygen %
    watch_noise_exposure: Optional[float] = None  # dB from watch HealthKit
```

**Step 2: Parse new fields in `parse_telemetry_to_ephemeral()`**

Add after existing field parsing:
```python
    # Watch extended context
    ctx.watch_pitch = _to_float(data.get("watch_pitch"), 0.0)
    ctx.watch_roll = _to_float(data.get("watch_roll"), 0.0)
    ctx.watch_yaw = _to_float(data.get("watch_yaw"), 0.0)
    ctx.watch_stability_score = _to_float(data.get("watch_stability_score"), 1.0)
    ctx.watch_heading = _to_optional_float(data.get("watch_heading"))
    ctx.watch_heading_accuracy = _to_optional_float(data.get("watch_heading_accuracy"))
    ctx.sp_o2 = _to_optional_float(data.get("sp_o2"))
    ctx.watch_noise_exposure = _to_optional_float(data.get("watch_noise_exposure"))
```

Add helper if not exists:
```python
def _to_optional_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
```

**Step 3: Add new fields to `parse_telemetry()` semantic text**

Add after existing fields:
```python
    # Watch extended context
    stability = data.get("watch_stability_score")
    if stability is not None:
        pairs.append(f"stability={float(stability):.2f}")

    w_heading = data.get("watch_heading")
    if w_heading is not None:
        cardinal = _degrees_to_cardinal(float(w_heading))
        pairs.append(f"watch_heading={cardinal}({float(w_heading):.0f}°)")

    sp_o2 = data.get("sp_o2")
    if sp_o2 is not None:
        pairs.append(f"spO2={float(sp_o2):.0f}%")

    w_noise = data.get("watch_noise_exposure")
    if w_noise is not None:
        pairs.append(f"watch_noise={float(w_noise):.0f}dB")
```

**Step 4: Run tests**

```bash
cd SightLine && /opt/anaconda3/envs/sightline/bin/python -m pytest tests/test_telemetry_parser.py tests/test_lod_engine.py -v
```

**Step 5: Commit**

```bash
git add -A && git commit -m "feat: expand EphemeralContext and telemetry parser with Watch context fields"
```

---

### Task A8: Update LOD engine to use watch_stability_score

**Files:**
- Modify: `SightLine/lod/lod_engine.py`

**Step 1: Add stability-based LOD adjustment**

After the motion-state rule, add:
```python
    # ── Rule 1b: Watch stability adjustment (experience-driven) ─────
    stability = _to_float(getattr(ephemeral, "watch_stability_score", 1.0), 1.0)
    if stability < 0.4 and base_lod > 1:
        base_lod = max(1, base_lod - 1)
        log.triggered_rules.append(f"Rule1b:unstable({stability:.2f})→-1(brief)")
```

This means: if the user's gait is unstable (they might be on rough terrain, navigating obstacles), reduce verbosity so they can focus.

**Step 2: Add watch_heading to debug dict**

In `LODDecisionLog.to_debug_dict()`, add:
```python
"watch_heading": getattr(self, "watch_heading", None),
"stability": getattr(self, "stability_score", None),
```

**Step 3: Run tests**

```bash
cd SightLine && /opt/anaconda3/envs/sightline/bin/python -m pytest tests/test_lod_engine.py -v
```

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: add watch stability score to LOD engine as experience signal"
```

---

### Task A9: Update telemetry_parser HR bucket and update tests

**Files:**
- Modify: `SightLine/telemetry/telemetry_parser.py`
- Modify: `SightLine/tests/test_telemetry_parser.py`
- Modify: `SightLine/tests/test_lod_engine.py`

**Step 1: Remove "high" HR bucket (line 32)**

Old:
```python
def _hr_bucket(hr: float) -> str:
    if hr > 120: return "high"
    elif hr > 100: return "elevated"
    else: return "normal"
```

New:
```python
def _hr_bucket(hr: float) -> str:
    if hr > 100: return "elevated"
    return "normal"
```

**Step 2: Update test_telemetry_parser.py**

Remove any test cases that assert `"high"` HR bucket. Update to match new behavior.

**Step 3: Update test_lod_engine.py**

Remove any test cases related to:
- PANIC detection
- HR > 120 forcing LOD 1
- `panic=True` flag behavior

Update motion→LOD test assertions:
- Walking (any cadence) should now → LOD 2 (not LOD 1)

**Step 4: Run full test suite**

```bash
cd SightLine && /opt/anaconda3/envs/sightline/bin/python -m pytest tests/ -v
```

**Step 5: Commit**

```bash
git add -A && git commit -m "refactor: update HR bucket and fix tests for experience-first model"
```

---

## Track B: iOS Refactor (Swift)

### Task B1: Remove SOS gesture and rename emergency_pause to pause

**Files:**
- Modify: `SightLine/SightLine/UI/MainView.swift`

**Step 1: Remove `handleShake()` method (lines 446-453)**

Delete the entire method.

**Step 2: Remove shake detection**

Search for any `motionEnded` override or shake gesture recognizer that calls `handleShake()` and remove it.

**Step 3: Rename emergency pause**

In `handleLongPress()` (lines 402-422):
- Rename `isEmergencyPaused` → `isPaused` throughout the file
- Change gesture type from `"emergency_pause"` to `"pause"`
- Change accessibility announcement from `"Emergency pause activated/released"` to `"Session paused/resumed"`
- Change log message similarly

**Step 4: Build to verify compilation**

```bash
xcodebuild build -project SightLine/SightLine.xcodeproj -scheme SightLine -destination 'generic/platform=iOS' -quiet 2>&1 | tail -5
```

**Step 5: Commit**

```bash
git add -A && git commit -m "refactor: remove SOS gesture, rename emergency pause to session pause"
```

---

### Task B2: Remove panic message type from MessageProtocol

**Files:**
- Modify: `SightLine/SightLine/Core/MessageProtocol.swift`

**Step 1: Remove `panic` case from DownstreamMessage enum (line 141)**

Delete:
```swift
    case panic(message: String)
```

**Step 2: Remove panic parsing from `DownstreamMessage.parse()` switch**

Search for `case "panic":` in the switch statement and remove the case.

**Step 3: Remove panic handling from MainView**

Search for `.panic` in MainView.swift and remove the case handler.

**Step 4: Remove `sos()` from HapticManager**

In `SightLine/SightLine/UI/HapticManager.swift`, delete lines 100-109:
```swift
    /// SOS: three warning haptics in rapid succession.
    func sos() { ... }
```

**Step 5: Build to verify**

```bash
xcodebuild build -project SightLine/SightLine.xcodeproj -scheme SightLine -destination 'generic/platform=iOS' -quiet 2>&1 | tail -5
```

**Step 6: Commit**

```bash
git add -A && git commit -m "refactor: remove panic message type and SOS haptic"
```

---

### Task B3: Expand TelemetryData with Watch context fields

**Files:**
- Modify: `SightLine/SightLine/Core/MessageProtocol.swift`

**Step 1: Add new fields to TelemetryData struct**

After existing fields, add:
```swift
    // Watch extended context
    var watchPitch: Double?
    var watchRoll: Double?
    var watchYaw: Double?
    var watchStabilityScore: Double?
    var watchHeading: Double?
    var watchHeadingAccuracy: Double?
    var spO2: Double?
    var watchNoiseExposure: Double?
```

**Step 2: Add CodingKeys**

Add to the existing CodingKeys enum:
```swift
    case watchPitch = "watch_pitch"
    case watchRoll = "watch_roll"
    case watchYaw = "watch_yaw"
    case watchStabilityScore = "watch_stability_score"
    case watchHeading = "watch_heading"
    case watchHeadingAccuracy = "watch_heading_accuracy"
    case spO2 = "sp_o2"
    case watchNoiseExposure = "watch_noise_exposure"
```

**Step 3: Build to verify**

```bash
xcodebuild build -project SightLine/SightLine.xcodeproj -scheme SightLine -destination 'generic/platform=iOS' -quiet 2>&1 | tail -5
```

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: expand TelemetryData with Watch context fields"
```

---

### Task B4: Expand WatchReceiver to handle new Watch data

**Files:**
- Modify: `SightLine/SightLine/Sensors/WatchReceiver.swift`

**Step 1: Add new published properties**

After existing properties, add:
```swift
    // Watch extended context
    @Published var watchPitch: Double?
    @Published var watchRoll: Double?
    @Published var watchYaw: Double?
    @Published var watchStabilityScore: Double?
    @Published var watchHeading: Double?
    @Published var watchHeadingAccuracy: Double?
    @Published var spO2: Double?
    @Published var watchNoiseExposure: Double?
```

**Step 2: Expand `processHeartRateMessage()` (or rename to `processWatchMessage()`)**

Extract new fields from the payload dict:
```swift
    private func processWatchMessage(_ payload: [String: Any]) {
        // Existing heart rate handling...
        if let hr = payload["heartRate"] as? Double, hr > 0 {
            heartRate = hr
            lastUpdateTime = Date()
        }
        isWatchMonitoring = payload["isMonitoring"] as? Bool ?? false

        // New: motion data
        if let motion = payload["motion"] as? [String: Any] {
            watchPitch = motion["pitch"] as? Double
            watchRoll = motion["roll"] as? Double
            watchYaw = motion["yaw"] as? Double
            watchStabilityScore = motion["stabilityScore"] as? Double
        }

        // New: heading
        watchHeading = payload["heading"] as? Double
        watchHeadingAccuracy = payload["headingAccuracy"] as? Double

        // New: health data
        spO2 = payload["spO2"] as? Double
        watchNoiseExposure = payload["noiseExposure"] as? Double
    }
```

**Step 3: Build to verify**

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: expand WatchReceiver to handle motion, heading, SpO2, noise"
```

---

### Task B5: Expand SensorManager to aggregate new Watch data

**Files:**
- Modify: `SightLine/SightLine/Sensors/SensorManager.swift`

**Step 1: Expand `snapshot()` method**

After existing heart rate aggregation, add:
```swift
    // Watch extended context
    data.watchPitch = watchReceiver.watchPitch
    data.watchRoll = watchReceiver.watchRoll
    data.watchYaw = watchReceiver.watchYaw
    data.watchStabilityScore = watchReceiver.watchStabilityScore
    data.watchHeading = watchReceiver.watchHeading
    data.watchHeadingAccuracy = watchReceiver.watchHeadingAccuracy
    data.spO2 = watchReceiver.spO2
    data.watchNoiseExposure = watchReceiver.watchNoiseExposure
```

**Step 2: Add Combine subscribers for new Watch data**

Add a new publisher merge for watch extended context:
```swift
    // Group 4: Watch extended context
    Publishers.CombineLatest4(
        watchReceiver.$watchPitch,
        watchReceiver.$watchHeading,
        watchReceiver.$spO2,
        watchReceiver.$watchStabilityScore
    )
    .debounce(for: .milliseconds(500), scheduler: RunLoop.main)
    .sink { [weak self] _ in
        guard let self else { return }
        self.currentTelemetry = self.snapshot()
    }
    .store(in: &cancellables)
```

**Step 3: Build to verify**

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: aggregate Watch extended context in SensorManager"
```

---

## Track C: watchOS Expansion (Swift)

### Task C1: Add CMMotionManager to Watch

**Files:**
- Create: `SightLine/SightLineWatch/WatchMotionManager.swift`

**Step 1: Create WatchMotionManager**

```swift
import CoreMotion
import Foundation
import Combine
import os

/// Collects accelerometer and device-motion data on watchOS.
/// Requires an active HKWorkoutSession for background delivery.
class WatchMotionManager: ObservableObject {
    @Published var pitch: Double = 0.0
    @Published var roll: Double = 0.0
    @Published var yaw: Double = 0.0
    @Published var stabilityScore: Double = 1.0  // 1.0 = stable

    private static let logger = Logger(subsystem: "com.sightline.watch", category: "Motion")
    private let motionManager = CMMotionManager()
    private var recentAccelMagnitudes: [Double] = []
    private let stabilityWindowSize = 20  // ~2 seconds at 10 Hz

    func startUpdates() {
        guard motionManager.isDeviceMotionAvailable else {
            Self.logger.warning("Device motion unavailable")
            return
        }

        motionManager.deviceMotionUpdateInterval = 0.1  // 10 Hz (power-friendly)
        motionManager.startDeviceMotionUpdates(to: .main) { [weak self] motion, error in
            guard let self, let motion else { return }

            self.pitch = motion.attitude.pitch
            self.roll = motion.attitude.roll
            self.yaw = motion.attitude.yaw

            // Compute stability score from acceleration variance
            let accel = motion.userAcceleration
            let magnitude = sqrt(accel.x * accel.x + accel.y * accel.y + accel.z * accel.z)
            self.recentAccelMagnitudes.append(magnitude)
            if self.recentAccelMagnitudes.count > self.stabilityWindowSize {
                self.recentAccelMagnitudes.removeFirst()
            }
            self.stabilityScore = self.computeStability()
        }
        Self.logger.info("Device motion updates started at 10 Hz")
    }

    func stopUpdates() {
        motionManager.stopDeviceMotionUpdates()
        recentAccelMagnitudes.removeAll()
        Self.logger.info("Device motion updates stopped")
    }

    private func computeStability() -> Double {
        guard recentAccelMagnitudes.count >= 5 else { return 1.0 }
        let mean = recentAccelMagnitudes.reduce(0, +) / Double(recentAccelMagnitudes.count)
        let variance = recentAccelMagnitudes.reduce(0) { $0 + ($1 - mean) * ($1 - mean) }
            / Double(recentAccelMagnitudes.count)
        // Map variance to 0-1: low variance = high stability
        // variance ~0 → score 1.0, variance > 0.5 → score ~0
        return max(0.0, min(1.0, 1.0 - (variance * 2.0)))
    }
}
```

**Step 2: Build to verify**

**Step 3: Commit**

```bash
git add -A && git commit -m "feat: add WatchMotionManager for accelerometer/gyro on watchOS"
```

---

### Task C2: Add compass heading to Watch

**Files:**
- Create: `SightLine/SightLineWatch/WatchHeadingManager.swift`

**Step 1: Create WatchHeadingManager**

```swift
import CoreLocation
import Foundation
import Combine
import os

/// Reads compass heading on watchOS. Requires location permission.
class WatchHeadingManager: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published var heading: Double?
    @Published var headingAccuracy: Double?

    private static let logger = Logger(subsystem: "com.sightline.watch", category: "Heading")
    private let locationManager = CLLocationManager()

    override init() {
        super.init()
        locationManager.delegate = self
    }

    func startUpdates() {
        guard CLLocationManager.headingAvailable() else {
            Self.logger.warning("Heading not available on this device")
            return
        }
        locationManager.requestWhenInUseAuthorization()
        locationManager.startUpdatingHeading()
        Self.logger.info("Heading updates started")
    }

    func stopUpdates() {
        locationManager.stopUpdatingHeading()
        Self.logger.info("Heading updates stopped")
    }

    func locationManager(_ manager: CLLocationManager, didUpdateHeading newHeading: CLHeading) {
        let h = newHeading.magneticHeading
        guard h >= 0 else { return }  // -1 means invalid
        heading = h
        headingAccuracy = newHeading.headingAccuracy
    }
}
```

**Step 2: Add Location permission to Watch Info.plist**

Add `NSLocationWhenInUseUsageDescription` to the watchOS target (via Xcode build settings or Info.plist generation).

**Step 3: Build to verify**

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: add WatchHeadingManager for compass on watchOS"
```

---

### Task C3: Add HealthKit SpO2 and noise queries

**Files:**
- Create: `SightLine/SightLineWatch/WatchHealthContext.swift`

**Step 1: Create WatchHealthContext**

```swift
import HealthKit
import Foundation
import Combine
import os

/// Reads SpO2 and environmental noise exposure from HealthKit on watch.
/// These are system-measured values — we cannot trigger measurements.
class WatchHealthContext: ObservableObject {
    @Published var spO2: Double?
    @Published var noiseExposure: Double?

    private static let logger = Logger(subsystem: "com.sightline.watch", category: "HealthContext")
    private let healthStore = HKHealthStore()
    private var spO2Query: HKAnchoredObjectQuery?
    private var noiseQuery: HKAnchoredObjectQuery?

    func requestAuthorizationAndStart() async {
        let types: Set<HKSampleType> = [
            HKQuantityType(.oxygenSaturation),
            HKQuantityType(.environmentalAudioExposure),
        ]

        do {
            try await healthStore.requestAuthorization(toShare: [], read: types)
            startObserving()
            Self.logger.info("HealthContext authorized and observing")
        } catch {
            Self.logger.error("HealthContext authorization failed: \(error.localizedDescription)")
        }
    }

    private func startObserving() {
        // SpO2
        let spO2Type = HKQuantityType(.oxygenSaturation)
        spO2Query = HKAnchoredObjectQuery(
            type: spO2Type,
            predicate: nil,
            anchor: nil,
            limit: HKObjectQueryNoLimit
        ) { [weak self] _, samples, _, _, _ in
            self?.processSpO2(samples)
        }
        spO2Query?.updateHandler = { [weak self] _, samples, _, _, _ in
            self?.processSpO2(samples)
        }
        if let q = spO2Query { healthStore.execute(q) }

        // Environmental noise
        let noiseType = HKQuantityType(.environmentalAudioExposure)
        noiseQuery = HKAnchoredObjectQuery(
            type: noiseType,
            predicate: nil,
            anchor: nil,
            limit: HKObjectQueryNoLimit
        ) { [weak self] _, samples, _, _, _ in
            self?.processNoise(samples)
        }
        noiseQuery?.updateHandler = { [weak self] _, samples, _, _, _ in
            self?.processNoise(samples)
        }
        if let q = noiseQuery { healthStore.execute(q) }
    }

    private func processSpO2(_ samples: [HKSample]?) {
        guard let latest = samples?.compactMap({ $0 as? HKQuantitySample }).last else { return }
        let value = latest.quantity.doubleValue(for: .percent()) * 100.0
        DispatchQueue.main.async { self.spO2 = value }
        Self.logger.debug("SpO2 updated: \(value)%")
    }

    private func processNoise(_ samples: [HKSample]?) {
        guard let latest = samples?.compactMap({ $0 as? HKQuantitySample }).last else { return }
        let value = latest.quantity.doubleValue(for: .decibelAWeightedSoundPressureLevel())
        DispatchQueue.main.async { self.noiseExposure = value }
        Self.logger.debug("Noise exposure updated: \(value) dB")
    }

    func stop() {
        if let q = spO2Query { healthStore.stop(q) }
        if let q = noiseQuery { healthStore.stop(q) }
    }
}
```

**Step 2: Update Watch entitlements to include HealthKit types**

In `SightLineWatch.entitlements`, the existing `com.apple.developer.healthkit` should suffice. But verify the Info.plist has:
- `NSHealthShareUsageDescription` for read access

**Step 3: Build to verify**

**Step 4: Commit**

```bash
git add -A && git commit -m "feat: add WatchHealthContext for SpO2 and noise from HealthKit"
```

---

### Task C4: Expand PhoneConnector to send all Watch context

**Files:**
- Modify: `SightLine/SightLineWatch/PhoneConnector.swift`

**Step 1: Add new send method**

Replace `sendHeartRate()` with a more comprehensive `sendWatchContext()`:

```swift
    /// Send full watch context to iPhone.
    func sendWatchContext(
        heartRate: Double,
        isMonitoring: Bool = true,
        motion: (pitch: Double, roll: Double, yaw: Double, stabilityScore: Double)? = nil,
        heading: Double? = nil,
        headingAccuracy: Double? = nil,
        spO2: Double? = nil,
        noiseExposure: Double? = nil
    ) {
        var payload: [String: Any] = [
            "heartRate": heartRate,
            "ts": Date().timeIntervalSince1970,
            "isMonitoring": isMonitoring,
        ]

        if let m = motion {
            payload["motion"] = [
                "pitch": m.pitch,
                "roll": m.roll,
                "yaw": m.yaw,
                "stabilityScore": m.stabilityScore,
            ]
        }

        if let h = heading {
            payload["heading"] = h
            if let acc = headingAccuracy {
                payload["headingAccuracy"] = acc
            }
        }

        if let spo2 = spO2 {
            payload["spO2"] = spo2
        }

        if let noise = noiseExposure {
            payload["noiseExposure"] = noise
        }

        let session = WCSession.default
        guard session.activationState == .activated else {
            Self.logger.warning("WCSession not activated, dropping watch context")
            return
        }

        if session.isReachable {
            session.sendMessage(payload, replyHandler: nil) { error in
                Self.logger.error("sendMessage failed: \(error.localizedDescription)")
                session.transferUserInfo(payload)
            }
        } else {
            session.transferUserInfo(payload)
        }
    }
```

Keep `sendHeartRate()` as a convenience wrapper for backward compatibility:
```swift
    func sendHeartRate(_ bpm: Double, isMonitoring: Bool = true) {
        sendWatchContext(heartRate: bpm, isMonitoring: isMonitoring)
    }
```

**Step 2: Build to verify**

**Step 3: Commit**

```bash
git add -A && git commit -m "feat: expand PhoneConnector to send full Watch context"
```

---

### Task C5: Wire everything in WorkoutManager and ContentView

**Files:**
- Modify: `SightLine/SightLineWatch/WorkoutManager.swift`
- Modify: `SightLine/SightLineWatch/ContentView.swift`
- Modify: `SightLine/SightLineWatch/SightLineWatchApp.swift`

**Step 1: Add motion and heading managers to WorkoutManager**

```swift
    let watchMotion = WatchMotionManager()
    let watchHeading = WatchHeadingManager()
    let watchHealth = WatchHealthContext()
```

**Step 2: Start/stop new managers with workout**

In `startWorkout()`, after session starts:
```swift
    watchMotion.startUpdates()
    watchHeading.startUpdates()
    Task { await watchHealth.requestAuthorizationAndStart() }
```

In `stopWorkout()`:
```swift
    watchMotion.stopUpdates()
    watchHeading.stopUpdates()
    watchHealth.stop()
```

**Step 3: Update HR send to include all context**

In `workoutBuilder(didCollectDataOf:)`, change the heart rate send:

Old:
```swift
    PhoneConnector.shared.sendHeartRate(bpm, isMonitoring: true)
```

New:
```swift
    PhoneConnector.shared.sendWatchContext(
        heartRate: bpm,
        isMonitoring: true,
        motion: (
            pitch: watchMotion.pitch,
            roll: watchMotion.roll,
            yaw: watchMotion.yaw,
            stabilityScore: watchMotion.stabilityScore
        ),
        heading: watchHeading.heading,
        headingAccuracy: watchHeading.headingAccuracy,
        spO2: watchHealth.spO2,
        noiseExposure: watchHealth.noiseExposure
    )
```

**Step 4: Update ContentView to show new data**

Add a compact display below heart rate:
```swift
    if workoutManager.watchMotion.stabilityScore < 1.0 {
        Text("Stability: \(workoutManager.watchMotion.stabilityScore, specifier: "%.0f%%")")
            .font(.caption)
            .foregroundColor(.secondary)
    }
    if let heading = workoutManager.watchHeading.heading {
        Text("Heading: \(Int(heading))°")
            .font(.caption)
            .foregroundColor(.secondary)
    }
```

**Step 5: Build to verify**

**Step 6: Commit**

```bash
git add -A && git commit -m "feat: wire Watch motion, heading, and health context into workout session"
```

---

## Final: Run Full Test Suite

```bash
cd SightLine && /opt/anaconda3/envs/sightline/bin/python -m pytest tests/ -v
```

Fix any remaining failures, then:

```bash
git add -A && git commit -m "test: fix all tests for experience-first model with Watch context"
```

---

## Track Dependencies

```
Track A (Backend):  A1 → A2 → A3 → A4 → A5 → A6 → A7 → A8 → A9
Track B (iOS):      B1 → B2 → B3 → B4 → B5
Track C (watchOS):  C1 → C2 → C3 → C4 → C5

A1-A6 and B1-B2 can run in parallel (safety removal, different files)
A7-A9 and B3-B5 can run in parallel (context expansion, different files)
C1-C5 are fully independent (watchOS-only files)
```
