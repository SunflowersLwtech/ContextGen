"""Unit tests for ContextInjectionQueue in server.py.

Tests cover: enqueue/flush/dedup/merge/priority sorting, model speaking
state switching, max_age timeout, vision spoken cooldown, and SILENT wrapping.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

# We need to import the class from server.py.  The module has heavy
# dependencies (ADK, Firestore, etc.) so we patch them at import time.

# Minimal stubs so `import server` doesn't blow up.
import sys
import types as _pytypes


def _make_stub(name):
    mod = _pytypes.ModuleType(name)
    sys.modules[name] = mod
    return mod


# Stub out heavy third-party imports before importing anything from server.
_stubs_needed = [
    "dotenv",
    "fastapi",
    "fastapi.middleware",
    "fastapi.middleware.cors",
    "fastapi.responses",
    "google.adk",
    "google.adk.agents",
    "google.adk.agents.live_request_queue",
    "google.adk.runners",
    "google.genai",
    "starlette",
    "starlette.websockets",
    "agents",
    "agents.orchestrator",
    "live_api",
    "live_api.session_manager",
    "lod",
    "lod.lod_engine",
    "lod.telemetry_aggregator",
    "telemetry",
    "telemetry.telemetry_parser",
    "telemetry.session_meta_tracker",
]

for mod_name in _stubs_needed:
    if mod_name not in sys.modules:
        _make_stub(mod_name)

# Now provide the specific names that server.py expects at module level.
# google.genai.types needs Content/Part classes
_genai_types = _make_stub("google.genai.types")


class _FakePart:
    def __init__(self, text="", **kwargs):
        self.text = text


class _FakeContent:
    def __init__(self, parts=None, role="user"):
        self.parts = parts or []
        self.role = role


_genai_types.Part = _FakePart
_genai_types.Content = _FakeContent

# google.adk.agents.live_request_queue.LiveRequestQueue
_lrq_mod = sys.modules["google.adk.agents.live_request_queue"]


class _FakeLRQ:
    def __init__(self):
        self.sent: list = []

    def send_content(self, content):
        self.sent.append(content)

    def close(self):
        pass


_lrq_mod.LiveRequestQueue = _FakeLRQ

# Now we can safely import the ContextInjectionQueue class and helpers
# directly — but server.py is huge and wired to FastAPI.  Instead, we
# re-create the class in isolation by exec-ing just the relevant source
# block.  This is fragile, so we take a simpler approach: copy the class
# source into a small helper that we test against the real types.

# Actually the cleanest approach: import the constants + class by extracting
# them.  But that's also fragile.  Let's just test via a self-contained
# reimplementation that mirrors the real class — but that defeats the purpose.
#
# Best approach: directly instantiate using the real module types after
# setting up google.genai.types.

# Patch google.genai so `from google.genai import types` works in server
sys.modules["google.genai"].types = _genai_types
sys.modules["google.adk.runners"].Runner = MagicMock

# Provide stubs for server-level imports
sys.modules["fastapi"].FastAPI = MagicMock
sys.modules["fastapi"].Request = MagicMock
sys.modules["fastapi"].WebSocket = MagicMock
sys.modules["fastapi"].WebSocketDisconnect = Exception
sys.modules["fastapi.middleware.cors"].CORSMiddleware = MagicMock
sys.modules["fastapi.responses"].JSONResponse = MagicMock
sys.modules["starlette.websockets"].WebSocketState = MagicMock
sys.modules["dotenv"].load_dotenv = lambda *a, **kw: None

# Stub the local project imports
sys.modules["agents.orchestrator"].create_orchestrator_agent = MagicMock
for fn_name in [
    "SessionManager",
    "build_vad_runtime_update_message",
    "build_vad_runtime_update_payload",
    "create_session_service",
    "supports_runtime_vad_reconfiguration",
]:
    setattr(sys.modules["live_api.session_manager"], fn_name, MagicMock())
for fn_name in [
    "PanicHandler",
    "build_full_dynamic_prompt",
    "build_lod_update_message",
    "decide_lod",
    "on_lod_change",
]:
    setattr(sys.modules["lod"], fn_name, MagicMock())
sys.modules["lod.lod_engine"].should_speak = MagicMock()
sys.modules["lod.telemetry_aggregator"].TelemetryAggregator = MagicMock
sys.modules["telemetry.telemetry_parser"].parse_telemetry = MagicMock()
sys.modules["telemetry.telemetry_parser"].parse_telemetry_to_ephemeral = MagicMock()
sys.modules["telemetry.session_meta_tracker"].SessionMetaTracker = MagicMock

# --- Finally, import the real class ----------------------------------------
# We add the SightLine directory to sys.path so `import server` resolves.
import os

_sightline_dir = os.path.join(os.path.dirname(__file__), "..")
if _sightline_dir not in sys.path:
    sys.path.insert(0, _sightline_dir)

from server import (
    ContextInjectionQueue,
    QUEUE_MAX_AGE_SEC,
    VISION_SPOKEN_COOLDOWN_SEC,
    _QueuedItem,
)

# Alias the fake types for convenience in tests
Content = _FakeContent
Part = _FakePart


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def lrq():
    """A mock LiveRequestQueue that records sent items."""
    return _FakeLRQ()


@pytest.fixture
def queue(lrq):
    """A fresh ContextInjectionQueue wrapping the mock LRQ."""
    return ContextInjectionQueue(lrq)


# ---------------------------------------------------------------------------
# Tests: enqueue when model idle → immediate send
# ---------------------------------------------------------------------------


class TestEnqueueModelIdle:
    def test_sends_immediately_when_not_speaking(self, queue, lrq):
        queue.enqueue("vision", "scene description", priority=5, speak=True)
        assert len(lrq.sent) == 1
        assert lrq.sent[0].parts[0].text == "scene description"

    def test_queue_stays_empty_after_immediate_send(self, queue, lrq):
        queue.enqueue("vision", "scene description", priority=5, speak=True)
        assert queue.flush() is False  # nothing to flush


# ---------------------------------------------------------------------------
# Tests: enqueue when model speaking → queued
# ---------------------------------------------------------------------------


class TestEnqueueModelSpeaking:
    def test_queues_when_speaking(self, queue, lrq):
        queue.set_model_speaking(True)
        queue.enqueue("vision", "scene description", priority=5, speak=True)
        assert len(lrq.sent) == 0  # not sent yet

    def test_flush_sends_queued(self, queue, lrq):
        queue.set_model_speaking(True)
        queue.enqueue("vision", "scene description", priority=5, speak=True)
        queue.set_model_speaking(False)
        result = queue.flush()
        assert result is True
        assert len(lrq.sent) == 1
        assert "scene description" in lrq.sent[0].parts[0].text

    def test_flush_empty_returns_false(self, queue, lrq):
        assert queue.flush() is False


# ---------------------------------------------------------------------------
# Tests: category dedup (newer replaces older)
# ---------------------------------------------------------------------------


class TestCategoryDedup:
    def test_same_category_overwritten(self, queue, lrq):
        queue.set_model_speaking(True)
        queue.enqueue("vision", "old scene", priority=5, speak=True)
        queue.enqueue("vision", "new scene", priority=5, speak=True)
        queue.flush()
        assert len(lrq.sent) == 1
        assert "new scene" in lrq.sent[0].parts[0].text
        assert "old scene" not in lrq.sent[0].parts[0].text

    def test_different_categories_both_kept(self, queue, lrq):
        queue.set_model_speaking(True)
        queue.enqueue("vision", "scene", priority=5, speak=True)
        queue.enqueue("face", "John detected", priority=4, speak=True)
        queue.flush()
        assert len(lrq.sent) == 1
        text = lrq.sent[0].parts[0].text
        assert "scene" in text
        assert "John detected" in text


# ---------------------------------------------------------------------------
# Tests: priority sorting in merged output
# ---------------------------------------------------------------------------


class TestPrioritySorting:
    def test_lower_priority_number_comes_first(self, queue, lrq):
        queue.set_model_speaking(True)
        queue.enqueue("telemetry", "sensor data", priority=8, speak=False)
        queue.enqueue("vision", "danger ahead", priority=2, speak=True)
        queue.enqueue("face", "person nearby", priority=4, speak=True)
        queue.flush()
        text = lrq.sent[0].parts[0].text
        # priority 2 (vision) should come before priority 4 (face) before 8 (telemetry)
        idx_vision = text.index("danger ahead")
        idx_face = text.index("person nearby")
        idx_telemetry = text.index("sensor data")
        assert idx_vision < idx_face < idx_telemetry


# ---------------------------------------------------------------------------
# Tests: SILENT wrapping
# ---------------------------------------------------------------------------


class TestSilentWrapping:
    def test_all_silent_items_get_prefix(self, queue, lrq):
        queue.set_model_speaking(True)
        queue.enqueue("lod", "lod update", priority=3, speak=False)
        queue.enqueue("telemetry", "sensor", priority=8, speak=False)
        queue.flush()
        text = lrq.sent[0].parts[0].text
        assert text.startswith("[CONTEXT UPDATE - DO NOT SPEAK]")

    def test_mixed_speak_no_prefix(self, queue, lrq):
        queue.set_model_speaking(True)
        queue.enqueue("vision", "scene", priority=5, speak=True)
        queue.enqueue("telemetry", "sensor", priority=8, speak=False)
        queue.flush()
        text = lrq.sent[0].parts[0].text
        assert not text.startswith("[CONTEXT UPDATE - DO NOT SPEAK]")


# ---------------------------------------------------------------------------
# Tests: model speaking state
# ---------------------------------------------------------------------------


class TestModelSpeakingState:
    def test_default_not_speaking(self, queue):
        assert queue.model_speaking is False

    def test_set_speaking(self, queue):
        queue.set_model_speaking(True)
        assert queue.model_speaking is True

    def test_set_not_speaking(self, queue):
        queue.set_model_speaking(True)
        queue.set_model_speaking(False)
        assert queue.model_speaking is False


# ---------------------------------------------------------------------------
# Tests: inject_immediate always bypasses
# ---------------------------------------------------------------------------


class TestInjectImmediate:
    def test_bypass_when_speaking(self, queue, lrq):
        queue.set_model_speaking(True)
        content = Content(parts=[Part(text="PANIC")])
        queue.inject_immediate(content)
        assert len(lrq.sent) == 1
        assert lrq.sent[0].parts[0].text == "PANIC"

    def test_bypass_when_idle(self, queue, lrq):
        content = Content(parts=[Part(text="init prompt")])
        queue.inject_immediate(content)
        assert len(lrq.sent) == 1


# ---------------------------------------------------------------------------
# Tests: max_age timeout
# ---------------------------------------------------------------------------


class TestMaxAge:
    def test_no_flush_within_age(self, queue, lrq):
        queue.set_model_speaking(True)
        queue.enqueue("vision", "scene", priority=5, speak=True)
        assert queue.check_max_age() is False

    def test_flush_after_max_age(self, queue, lrq):
        queue.set_model_speaking(True)
        queue.enqueue("vision", "scene", priority=5, speak=True)
        # Manually backdate the enqueued_at
        for item in queue._queue.values():
            item.enqueued_at = time.monotonic() - QUEUE_MAX_AGE_SEC - 1
        assert queue.check_max_age() is True
        assert len(lrq.sent) == 1


# ---------------------------------------------------------------------------
# Tests: vision spoken cooldown
# ---------------------------------------------------------------------------


class TestVisionSpokenCooldown:
    def test_cooldown_initially_inactive(self, queue):
        assert queue.vision_spoken_cooldown_active is False

    def test_cooldown_active_after_record(self, queue):
        queue.record_vision_spoken()
        assert queue.vision_spoken_cooldown_active is True

    def test_cooldown_expires(self, queue):
        queue._vision_spoken_at = time.monotonic() - VISION_SPOKEN_COOLDOWN_SEC - 1
        assert queue.vision_spoken_cooldown_active is False


# ---------------------------------------------------------------------------
# Tests: background flush task lifecycle
# ---------------------------------------------------------------------------


class TestBackgroundTask:
    @pytest.mark.asyncio
    async def test_start_and_stop(self, queue):
        queue.start_background_flush_task()
        assert queue._bg_task is not None
        assert not queue._bg_task.done()
        queue.stop()
        # Give the event loop a chance to process the cancellation
        await asyncio.sleep(0.05)
        assert queue._bg_task.done()

    def test_stop_without_start(self, queue):
        """stop() should not raise if background task was never started."""
        queue.stop()  # no error


# ---------------------------------------------------------------------------
# Tests: merge format
# ---------------------------------------------------------------------------


class TestMergeFormat:
    def test_items_joined_with_double_newline(self, queue, lrq):
        queue.set_model_speaking(True)
        queue.enqueue("vision", "scene A", priority=2, speak=True)
        queue.enqueue("face", "person B", priority=4, speak=True)
        queue.flush()
        text = lrq.sent[0].parts[0].text
        assert "\n\n" in text
        assert "scene A" in text
        assert "person B" in text
