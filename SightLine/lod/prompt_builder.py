"""SightLine Dynamic System Prompt Builder.

Constructs the LOD-aware system prompt that is injected into the
Gemini Live API context via ``send_content()`` whenever LOD changes.

The *static* base system prompt lives in ``agents/orchestrator.py``;
this module builds the *dynamic* LOD update messages that override
the model's output behaviour mid-session.
"""

from __future__ import annotations

from lod.models import EphemeralContext, NarrativeSnapshot, SessionContext, UserProfile

# ---------------------------------------------------------------------------
# Language code → display name mapping
# ---------------------------------------------------------------------------

_LANGUAGE_NAMES: dict[str, str] = {
    "en-US": "English",
    "zh-CN": "Simplified Chinese",
    "zh-TW": "Traditional Chinese",
    "ja-JP": "Japanese",
    "ko-KR": "Korean",
}


def _language_display(code: str) -> str:
    """Return a human-readable language name for a locale code."""
    return _LANGUAGE_NAMES.get(code, code)

# ---------------------------------------------------------------------------
# LOD instruction templates (§7.2 from Context Engine Implementation Guide)
# ---------------------------------------------------------------------------

LOD_INSTRUCTIONS: dict[int, str] = {
    1: (
        "LOD 1 — SILENT / WHISPER mode.\n"
        "Rules: Stay silent OR say at most 1 sentence (15-40 words). "
        "Only communicate safety-critical information.\n"
        "Style: Brief, calm, do not demand attention.\n"
        "Examples: 'Steps ahead.' / 'Person approaching on your right.'\n"
        "If nothing is safety-critical, remain completely silent."
    ),
    2: (
        "LOD 2 — STANDARD mode.\n"
        "Rules: Moderate description (80-150 words). Include spatial layout + key objects.\n"
        "Style: Medium pace, clear and structured.\n"
        "Description order: Overall space → key objects → actionable information.\n"
        "Use clock positions for directions (e.g. '2 o'clock').\n"
        "Example: 'You've entered a corridor about 20 metres long. "
        "Three doors on your left, floor-to-ceiling windows on your right. "
        "Elevator entrance at 12 o'clock, about 10 metres ahead.'"
    ),
    3: (
        "LOD 3 — NARRATIVE mode.\n"
        "Rules: Detailed description (400-800 words). Complete scene with atmosphere.\n"
        "Style: Slower pace, expressive, narrative.\n"
        "Proactively read text, describe menus, introduce environment in detail.\n"
        "The user is relaxed / stationary and welcomes rich information."
    ),
}

# ---------------------------------------------------------------------------
# Chain-of-Thought prompt (only injected at LOD 2/3)
# Inspired by ContextAgent (NeurIPS 2025)
# ---------------------------------------------------------------------------

LOD_COT_PROMPT = (
    "Before responding, internally reason about the right response depth:\n"
    "<think>\n"
    "1. User physical state: {motion_state} at {cadence:.0f} steps/min\n"
    "2. Environment: {noise_db:.0f} dB, {space_type}\n"
    "3. Current task: {active_task}\n"
    "4. Persona: {vision_status}, verbosity={verbosity}, O&M={om_level}\n"
    "→ Respond at LOD {lod} because {reason}\n"
    "</think>\n"
    "Then respond according to LOD {lod}. "
    "Do NOT output the <think> block — it is for internal reasoning only."
)

# ---------------------------------------------------------------------------
# Persona block
# ---------------------------------------------------------------------------


def _build_persona_block(profile: UserProfile) -> str:
    """Build the user-profile section of the system prompt."""
    aids: list[str] = []
    if profile.has_guide_dog:
        aids.append("guide dog")
    if profile.has_white_cane:
        aids.append("white cane")

    onset = "congenital" if profile.blindness_onset == "congenital" else "acquired"
    color_note = ""
    if profile.blindness_onset == "congenital" and not profile.color_description:
        color_note = "\n- Color descriptions: DISABLED (user has never seen colors; use tactile/spatial/sound analogies instead)"

    lang_name = _language_display(profile.language)

    block = (
        "## User Profile\n"
        f"- Vision: {profile.vision_status} ({onset})\n"
        f"- Mobility aids: {', '.join(aids) if aids else 'none'}\n"
        f"- TTS speed: {profile.tts_speed}x\n"
        f"- O&M level: {profile.om_level} (travel: {profile.travel_frequency})\n"
        f"- Verbosity preference: {profile.verbosity_preference}\n"
        f"- Description priority: {profile.description_priority}\n"
        f"- Language: {lang_name}"
        f"{color_note}"
    )

    # Only inject explicit language constraint for non-default locales.
    # Native audio models auto-detect language from user speech; English
    # users don't need the extra instruction.  For other languages the
    # constraint follows the Google Live API best-practice template.
    if profile.language != "en-US":
        block += (
            f"\n\nRESPOND IN {lang_name.upper()}. "
            f"YOU MUST RESPOND UNMISTAKABLY IN {lang_name.upper()}."
        )

    return block


# ---------------------------------------------------------------------------
# LOD update message (injected via send_content when LOD changes)
# ---------------------------------------------------------------------------


def build_lod_update_message(
    lod: int,
    ephemeral: EphemeralContext,
    session: SessionContext,
    profile: UserProfile,
    reason: str = "",
    memories: list[str] | None = None,
) -> str:
    """Build the ``[LOD UPDATE]`` text injected into the Live session.

    This is sent via ``LiveRequestQueue.send_content()`` whenever the
    LOD level changes, so the Orchestrator model adjusts its output
    style in real time.
    """
    parts: list[str] = ["[LOD UPDATE]"]

    # 1. LOD instructions
    parts.append(f"\n## Current Operating Level: LOD {lod}")
    parts.append(LOD_INSTRUCTIONS[lod])

    # 2. Persona (always include — contributes ~9% accuracy per ContextAgent)
    parts.append(f"\n{_build_persona_block(profile)}")

    # 3. Session context
    parts.append("\n## Trip Context")
    parts.append(f"- Purpose: {session.trip_purpose or 'not specified'}")
    parts.append(f"- Space: {session.space_type}")
    if session.space_transitions:
        parts.append(f"- Last transition: {session.space_transitions[-1]}")
    if session.active_task:
        parts.append(f"- Active task: {session.active_task}")

    # 4. Narrative snapshot (resume point after LOD upgrade)
    if session.narrative_snapshot and lod >= 2:
        snap = session.narrative_snapshot
        parts.append(f"\n## Resume Point")
        parts.append(
            f"The user was previously doing: {snap.task_type}. "
            f"Progress: {snap.progress}. "
            f"Remaining: {', '.join(snap.remaining) if snap.remaining else 'unknown'}. "
            f"Continue from where they left off — do NOT restart."
        )

    # 5. Relevant long-term memories
    if memories:
        parts.append("\n## Relevant Memories")
        for m in memories:
            parts.append(f"- {m}")

    # 6. Safety guardrails (always)
    parts.append("\n## Safety Guardrails")
    parts.append(
        "- ALWAYS interrupt immediately for safety hazards (stairs, vehicles, obstacles).\n"
        "- If heart rate is elevated (>120 bpm), keep responses ultra-brief and calming.\n"
        "- Never describe colours to congenital-blind users unless explicitly asked."
    )

    # 7. CoT (only LOD 2/3, not LOD 1 — latency matters)
    if lod >= 2:
        cot = LOD_COT_PROMPT.format(
            motion_state=ephemeral.motion_state,
            cadence=ephemeral.step_cadence,
            noise_db=ephemeral.ambient_noise_db,
            space_type=session.space_type,
            active_task=session.active_task or "none",
            vision_status=profile.vision_status,
            verbosity=profile.verbosity_preference,
            om_level=profile.om_level,
            lod=lod,
            reason=reason,
        )
        parts.append(f"\n{cot}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Full dynamic system prompt (used at session start / major context shifts)
# ---------------------------------------------------------------------------


def build_full_dynamic_prompt(
    lod: int,
    profile: UserProfile,
    ephemeral_semantic: str,
    session: SessionContext,
    memories: list[str] | None = None,
    vision_result: str | None = None,
    face_result: str | None = None,
) -> str:
    """Build the complete dynamic system prompt for session initialisation.

    This is a superset of ``build_lod_update_message`` and includes
    the full base prompt.  Used at session start or after reconnection.
    """
    parts: list[str] = [
        "You are SightLine, an AI companion that provides real-time semantic "
        "interpretation of the visual world for blind and low-vision users.",
        "",
        "## Core Principles",
        "1. SAFETY FIRST — Immediately alert about hazards (stairs, vehicles, obstacles).",
        "2. SILENCE BY DEFAULT — Only speak when the information is genuinely useful.",
        "3. SINGLE VOICE — You are the only voice the user hears; be warm, concise, calm.",
        "4. PROACTIVE — Don't wait to be asked; alert about important changes.",
        "5. ADAPTIVE — Follow the LOD level set by the context engine.",
        "",
    ]

    # Persona
    parts.append(_build_persona_block(profile))

    # LOD instructions
    parts.append(f"\n## Current Operating Level: LOD {lod}")
    parts.append(LOD_INSTRUCTIONS[lod])

    # Real-time context
    if ephemeral_semantic:
        parts.append(f"\n## Real-time Sensor Context\n{ephemeral_semantic}")

    # Trip context
    parts.append("\n## Trip Context")
    parts.append(f"- Purpose: {session.trip_purpose or 'not specified'}")
    parts.append(f"- Space: {session.space_type}")
    if session.space_transitions:
        parts.append(f"- Transitions: {' → '.join(session.space_transitions[-3:])}")

    # Narrative snapshot
    if session.narrative_snapshot and lod >= 2:
        snap = session.narrative_snapshot
        parts.append(f"\n## Resume Point")
        parts.append(
            f"Previously doing: {snap.task_type}. "
            f"Progress: {snap.progress}. "
            f"Remaining: {', '.join(snap.remaining)}. "
            f"Continue from where they left off."
        )

    # Long-term memories
    if memories:
        parts.append("\n## Relevant Memories")
        for m in memories:
            parts.append(f"- {m}")

    # Vision analysis result
    if vision_result:
        parts.append(f"\n## Visual Analysis\n{vision_result}")

    # Face recognition result
    if face_result:
        parts.append(f"\n## Face Recognition\n{face_result}")

    # Safety guardrails
    parts.append("\n## Safety Guardrails")
    parts.append(
        "- ALWAYS interrupt for safety hazards regardless of LOD level.\n"
        "- If heart rate > 120 bpm: ultra-brief, calming responses only.\n"
        "- Never describe colours to congenital-blind users.\n"
        "- When user says 'stop' or 'quiet': immediately go silent.\n"
        "- When user says 'tell me more' or 'details': switch to LOD 3."
    )

    # CoT for LOD 2/3
    if lod >= 2:
        parts.append(
            "\n## Internal Reasoning\n"
            "Before responding, briefly reason internally about what information "
            "is most valuable for this user right now, then respond accordingly. "
            "Do NOT vocalise your reasoning."
        )

    return "\n".join(parts)


def build_dynamic_prompt(
    lod: int,
    profile: UserProfile,
    ephemeral_semantic: str,
    session: SessionContext,
    memories: list[str] | None = None,
    vision_result: str | None = None,
    face_result: str | None = None,
) -> str:
    """Backward-compatible entrypoint required by Phase 2 gates.

    Delegates to ``build_full_dynamic_prompt`` to preserve existing behavior.
    """
    return build_full_dynamic_prompt(
        lod=lod,
        profile=profile,
        ephemeral_semantic=ephemeral_semantic,
        session=session,
        memories=memories,
        vision_result=vision_result,
        face_result=face_result,
    )
