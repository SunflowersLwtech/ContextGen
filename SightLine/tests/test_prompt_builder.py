"""Tests for SightLine dynamic prompt builder."""

from lod.models import EphemeralContext, NarrativeSnapshot, SessionContext, UserProfile
from lod.prompt_builder import build_full_dynamic_prompt, build_lod_update_message


def _default_args(lod: int = 2, **overrides):
    """Helper to build default args for build_lod_update_message."""
    kwargs = dict(
        lod=lod,
        ephemeral=EphemeralContext(),
        session=SessionContext(),
        profile=UserProfile.default(),
        reason="test",
    )
    kwargs.update(overrides)
    return kwargs


def test_lod_update_contains_lod_level():
    msg = build_lod_update_message(**_default_args(lod=1))
    assert "LOD 1" in msg


def test_lod_update_contains_persona():
    msg = build_lod_update_message(**_default_args())
    assert "User Profile" in msg


def test_lod_update_lod1_no_cot():
    msg = build_lod_update_message(**_default_args(lod=1))
    assert "<think>" not in msg


def test_lod_update_lod2_has_cot():
    msg = build_lod_update_message(**_default_args(lod=2))
    assert "internally reason" in msg


def test_lod_update_with_memories():
    msg = build_lod_update_message(**_default_args(memories=["test memory"]))
    assert "Relevant Memories" in msg
    assert "test memory" in msg


def test_lod_update_with_snapshot():
    session = SessionContext(
        narrative_snapshot=NarrativeSnapshot(
            task_type="menu_reading",
            progress="item 3",
            remaining=["item 4"],
        )
    )
    msg = build_lod_update_message(**_default_args(lod=2, session=session))
    assert "Resume Point" in msg


def test_full_prompt_contains_principles():
    msg = build_full_dynamic_prompt(
        lod=2,
        profile=UserProfile.default(),
        ephemeral_semantic="test context",
        session=SessionContext(),
    )
    assert "SAFETY FIRST" in msg


def test_congenital_blind_no_color():
    profile = UserProfile.default()
    profile.blindness_onset = "congenital"
    profile.color_description = False
    msg = build_lod_update_message(**_default_args(profile=profile))
    assert "DISABLED" in msg
