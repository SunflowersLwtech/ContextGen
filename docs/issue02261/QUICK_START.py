"""
SightLine Issue 02261 — Quick Start for Implementing Agent
==========================================================

READ ORDER:
  1. This file (overview + checklist)
  2. ARCHITECTURE_CONTEXT.py (system architecture + file map)
  3. ROOT_CAUSE_ANALYSIS.py (detailed root causes + exact fix code)

ISSUE SUMMARY:
  (a) Model can't determine when to stop/start speaking
      → VAD preset wrong + proactive_audio triggers on context injections
  (b) Model parrots scene/heart-rate data
      → Natural language telemetry format + too frequent injection + all role="user"
  (c) User speech labeled as model speech in System Log
      → No echo detection between input/output transcription

FIX SUMMARY (10 fixes across 7 files):
  P0_FIX_1: VAD preset — end_sensitivity LOW→HIGH for LOD 2
  P0_FIX_2: Telemetry format — natural language → structured KV
  P0_FIX_3: Echo detection — server-side input/output similarity check
  P1_FIX_1: Injection frequency — reduce force-refresh, widen vision intervals
  P1_FIX_2: System prompt — add NEVER ECHO CONTEXT principle
  P1_FIX_3: CoT prompt — remove raw sensor values
  P1_FIX_4: Boundary markers — <<<SENSOR_DATA>>> delimiters
  P2_FIX_1: Conditional proactive_audio at LOD 1
  P2_FIX_2: iOS echo filter in MainView + DeveloperConsoleView
  P2_FIX_3: Suppress injection during model audio generation

FILES TO MODIFY:
  [Python]
  SightLine/live_api/session_manager.py    — P0_FIX_1, P2_FIX_1
  SightLine/telemetry/telemetry_parser.py  — P0_FIX_2
  SightLine/server.py                      — P0_FIX_3, P1_FIX_1, P1_FIX_4, P2_FIX_3
  SightLine/agents/orchestrator.py         — P1_FIX_2
  SightLine/lod/prompt_builder.py          — P1_FIX_3

  [Swift]
  SightLine/SightLine/UI/MainView.swift              — P2_FIX_2
  SightLine/SightLine/UI/DeveloperConsoleView.swift   — P2_FIX_2

IMPLEMENTATION ORDER: P0 → P1 → P2 (see ROOT_CAUSE_ANALYSIS.py for details)

VERIFICATION:
  - Python: pytest (if test files exist), manual WebSocket test
  - Swift: xcodebuild test -scheme SightLine -destination 'platform=iOS Simulator,...'
  - Manual: check Developer Console Log for correct role labels
  - Manual: verify model no longer parrots "heart rate" or "noise dB"
"""
