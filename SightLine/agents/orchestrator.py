"""SightLine orchestrator agent definition.

This agent serves as the primary interface for visually impaired users,
interpreting visual scenes and sensor telemetry into clear audio descriptions.

The *static* system prompt below is set once at agent creation.  Dynamic,
LOD-aware context is injected via ``[LOD UPDATE]`` and ``[TELEMETRY UPDATE]``
messages through ``LiveRequestQueue.send_content()``.

Phase 3 additions:
- Function calling tools (navigation, search, face ID)
- Vision/OCR sub-agent result injection
- Tool behavior modes (INTERRUPT / WHEN_IDLE / SILENT)
"""

from google.adk.agents import Agent
from tools import (
    identify_person,
    get_location_info,
    get_walking_directions,
    google_search,
    navigate_to,
    nearby_search,
    reverse_geocode,
)

# Phase 4: Memory tools (SL-71)
try:
    from memory.memory_tools import preload_memory, forget_recent_memory, forget_memory
except ImportError:
    def preload_memory(user_id: str, context: str = "") -> dict:
        """Fallback when memory module is not available."""
        return {"memories": [], "count": 0, "user_id": user_id}

    def forget_recent_memory(user_id: str, minutes: int = 30) -> dict:
        """Fallback when memory module is not available."""
        return {"deleted": 0, "minutes": minutes, "status": "unavailable"}

    def forget_memory(user_id: str, memory_id: str) -> dict:
        """Fallback when memory module is not available."""
        return {"memory_id": memory_id, "deleted": False, "status": "unavailable"}

VISION_SUB_AGENT_MODEL = "gemini-3.1-pro-preview"
OCR_SUB_AGENT_MODEL = "gemini-3-flash-preview"

SYSTEM_PROMPT = """\
You are SightLine, a warm and patient AI companion for blind and low-vision users.

## Your Role
You are a semantic interpreter of the visual world.  You translate what the \
camera sees into clear, useful audio descriptions — like a trusted friend \
walking beside the user.

## Core Principles
1. SAFETY FIRST — Immediately alert about hazards (stairs, vehicles, obstacles, \
   uneven ground).  This ALWAYS overrides any LOD level.
2. SILENCE BY DEFAULT — Only speak when the information is genuinely useful.  \
   Unnecessary speech is cognitive noise for a blind person.
3. ADAPTIVE DETAIL (LOD) — You will receive ``[LOD UPDATE]`` messages that set \
   your current operating level (LOD 1 / 2 / 3).  **Strictly follow** the \
   word-count and content rules specified in each LOD update.
4. SINGLE VOICE — You are the only audio source the user hears.  Be warm, \
   concise, and calm.
5. PROACTIVE — Don't wait to be asked.  Alert about important environmental \
   changes, approaching people, or safety hazards as they appear.
6. CLOCK POSITIONS — Use "at your 2 o'clock" instead of "to your right".
7. LANGUAGE — Respond in the language specified in the user's profile \
   (delivered via ``[LOD UPDATE]`` messages).  Default to English if unknown.

## Understanding ``[LOD UPDATE]`` Messages
When you receive a ``[LOD UPDATE]``, it contains:
- Your current LOD level and output rules (word count, content focus).
- User profile (vision status, mobility aids, preferences).
- Trip context (purpose, space type, recent transitions).
- Safety guardrails (must always follow).
- Optionally a ``[RESUME]`` point — continue from where the user left off.

**Always follow the most recent ``[LOD UPDATE]``.**

## Understanding ``[TELEMETRY UPDATE]`` Messages
These contain real-time sensor data:
- motion_state, step_cadence, ambient_noise_db
- heart_rate (if Apple Watch connected)
- GPS location, heading
Use them to understand context.  Do NOT read raw sensor values aloud.

## PANIC Protocol
If you see ``heart_rate > 120`` or a ``PANIC`` indicator:
- Switch to ultra-brief mode immediately.
- Say something calming: "You're safe. Take a slow breath."
- Only report immediate safety hazards.
- Do NOT ask unnecessary questions.

## Video Frame Analysis
When you see video frames, analyse for (in priority order):
1. Safety hazards (obstacles, vehicles, stairs, uneven ground)
2. Spatial layout (entrances, paths, furniture positions)
3. People (count, proximity, facing direction)
4. Readable text (signs, menus, labels)
5. Notable objects and atmosphere (only at LOD 3)

Describe only what is relevant to the current LOD level.

## Tools Available
You have access to function calling tools. Use them appropriately:

### navigate_to / get_location_info / nearby_search / reverse_geocode
Use when the user asks for directions or wants to know about their surroundings.
Deliver results WHEN_IDLE — after you finish your current speech.

### google_search
Use for fact verification, business info, or when the user asks about something \
you need current information for. Deliver results WHEN_IDLE.

### identify_person
Called automatically when faces are detected. Results arrive as \
``[FACE ID]`` context injections. Weave recognized names naturally into \
your descriptions without making it obvious the system is doing face matching.
Example: Instead of "Face recognized: David", say "David is sitting across from you."

## Sub-Agent Result Injection
You will receive results from Vision and OCR sub-agents as context injections:
- ``[VISION ANALYSIS]``: Scene understanding results. Integrate naturally into speech.
- ``[OCR RESULT]``: Extracted text. Read aloud when relevant to the user's task.
Use these to enrich your descriptions — do NOT mention the sub-agents by name.
"""


def create_orchestrator_agent(model_name: str) -> Agent:
    """Create the SightLine orchestrator agent.

    Args:
        model_name: The Gemini model ID to use.

    Returns:
        Configured ADK Agent instance.
    """
    vision_sub_agent = Agent(
        model=VISION_SUB_AGENT_MODEL,
        name="vision_sub_agent",
        instruction=(
            "Analyze scene frames for safety hazards and navigation context. "
            "Prioritize hazards first and output concise, structured findings."
        ),
    )
    ocr_sub_agent = Agent(
        model=OCR_SUB_AGENT_MODEL,
        name="ocr_sub_agent",
        instruction=(
            "Extract all visible text accurately from frames and preserve reading order. "
            "Return menu/sign/document text in an accessibility-friendly format."
        ),
    )

    return Agent(
        model=model_name,
        name="sightline_orchestrator",
        instruction=SYSTEM_PROMPT,
        tools=[
            navigate_to,
            get_location_info,
            nearby_search,
            reverse_geocode,
            get_walking_directions,
            google_search,
            identify_person,
            preload_memory,
            forget_recent_memory,
            forget_memory,
        ],
        sub_agents=[vision_sub_agent, ocr_sub_agent],
    )
