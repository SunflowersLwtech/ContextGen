"""SightLine LOD (Level of Detail) decision engine.

Implements the rule-based LOD decision system that determines
information density based on user physical state and context.
"""

from lod.lod_engine import LODDecisionLog, decide_lod, should_speak
from lod.models import (
    EphemeralContext,
    GPSData,
    NarrativeSnapshot,
    SessionContext,
    UserProfile,
)
from lod.narrative_snapshot import on_lod_change
from lod.panic_handler import PanicHandler
from lod.prompt_builder import build_full_dynamic_prompt, build_lod_update_message

__all__ = [
    "LODDecisionLog",
    "EphemeralContext",
    "GPSData",
    "NarrativeSnapshot",
    "SessionContext",
    "UserProfile",
    "PanicHandler",
    "decide_lod",
    "should_speak",
    "on_lod_change",
    "build_full_dynamic_prompt",
    "build_lod_update_message",
]
