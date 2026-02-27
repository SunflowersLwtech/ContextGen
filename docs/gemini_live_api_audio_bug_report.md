# Bug Report: Gemini Live API Native Audio — Premature `turnComplete` Causes Mid-Sentence Audio Truncation

**Target repo:** `googleapis/python-genai`
**Title for GitHub:** `[Live API] Native audio output truncated mid-sentence — premature turnComplete with no interrupted flag`

---

## Description

When using the Gemini Live API with native audio output, the model frequently stops speaking mid-sentence. The server sends a `turnComplete` message while the model is still generating audio, with **no `interrupted` flag set**. This is not caused by client-side echo or VAD — it is a server-side issue where the model prematurely terminates its own turn.

This has been reported across multiple repos and confirmed by 40+ developers over the past 8+ months (see Related Issues below). Despite multiple fix attempts by Google engineers, the problem persists or regresses.

## Environment

- **Model:** `gemini-2.5-flash-native-audio-preview-12-2025`
- **SDK:** `google-genai` 1.64.0 (via `google-adk` 1.25.1)
- **API:** Google AI Developer API (not Vertex AI)
- **Platform:** FastAPI WebSocket server (Python 3.12) ↔ iOS client (SwiftUI)
- **OS:** macOS (server), iOS 18 (client)

## Steps to Reproduce

1. Establish a Live API session with native audio output:
   ```python
   config = LiveConnectConfig(
       response_modalities=["AUDIO"],
       speech_config=SpeechConfig(
           voice_config=VoiceConfig(
               prebuilt_voice_config=PrebuiltVoiceConfig(voice_name="Aoede")
           )
       ),
       realtime_input_config=RealtimeInputConfig(
           automatic_activity_detection=AutomaticActivityDetection(disabled=True)
       ),
   )
   ```
2. Send a user message that requires a multi-sentence response (e.g., "Describe what you see in detail")
3. Observe the server stream

## Expected Behavior

The model completes its entire response before sending `turnComplete`.

## Actual Behavior

- The model begins generating audio normally
- After 1-3 sentences (sometimes mid-word), a `turnComplete` message arrives **without** `interrupted: true`
- The remaining audio is never delivered
- This happens intermittently — sometimes the model completes, sometimes it truncates
- Frequency increases over the course of a session

## Key Evidence: This Is Server-Side, Not Echo

We have implemented **every possible client-side mitigation** and the problem persists:

1. **Hardware AEC:** iOS Voice Processing I/O (Audio Unit) provides hardware-level acoustic echo cancellation — far superior to desktop PyAudio setups
2. **Client-side echo gating:** During model speech, the client sends silence frames instead of microphone audio
3. **SileroVAD confirmation:** Voice activity detection confirms no speech is being sent during model output
4. **`NO_INTERRUPTION` mode:** Configured `turn_coverage: NO_INTERRUPTION` — the model should not be interruptible at all
5. **Disabled automatic activity detection:** `automatic_activity_detection.disabled = True` with manual activity signals

Despite all five layers of protection, the model still truncates its own output. The `turnComplete` arrives with no `interrupted` flag, confirming the server decided to end the turn on its own.

### Google's Own Documentation Acknowledges This

From the [Gemini Live API Get Started page](https://ai.google.dev/gemini-api/docs/live):

> **Note: Use headphones.** This script uses the system default audio input and output, which often won't include echo cancellation. To prevent the model from interrupting itself, use headphones.

This confirms Google is aware the model interrupts itself. However:
- Our iOS app already has **hardware-level AEC** (not software)
- We already implement **echo gating** (sending silence during playback)
- The problem persists because the root cause is **server-side premature turn termination**, not echo
- Requiring headphones is not an acceptable solution for an accessibility app serving visually impaired users

## Aggravating Factors

Through our testing and cross-referencing community reports, we identified 5 factors that significantly increase truncation frequency:

| Factor | Source | Impact |
|--------|--------|--------|
| **Tool calls (function calling)** | #707, #139, #1894 | Audio truncation frequency **dramatically increases** after tool call returns |
| **Growing context length** | #707 (@wehos) | Longer conversations → more frequent truncation |
| **Non-English languages** | #707 | Chinese, Japanese significantly worse |
| **`enable_affective_dialog`** | #707 | Directly correlated with premature turnComplete |
| **`context_window_compression`** | #117 | Enabling this worsens the problem |

Our application (SightLine, an AI assistant for visually impaired users) hits **all five factors simultaneously**: heavy tool usage (vision/OCR/face recognition/navigation), accumulating context, Chinese language support, and context window compression.

## Impact

SightLine is an AI-powered assistant for **visually impaired users** that relies on Gemini Live API's native audio for real-time voice interaction. The audio truncation makes the product unusable for its target audience — users receive incomplete safety-critical information (e.g., navigation directions cut off mid-sentence, obstacle warnings truncated).

This is not a cosmetic issue. For accessibility applications, reliable audio output is a hard requirement.

## No Alternative Models Available

| Model | Status | Viable? |
|-------|--------|---------|
| `gemini-2.5-flash-native-audio-preview-12-2025` | Current, in use | Has this bug |
| `gemini-2.5-flash-native-audio-preview-09-2025` | Deprecated 2026-03-19 | Worse — raspy audio (#1209) |
| `gemini-live-2.5-flash-native-audio` (Vertex AI GA) | Available | Same underlying model, same bug |
| `gemini-2.0-flash-live-001` | Decommissioned 2025-12-09 | Unavailable |
| Gemini 3.x series | No Live API support | Not applicable |

There is currently **no Gemini Live audio model without this bug**.

## Related Issues

This problem has been reported across multiple Google repos:

- **[googleapis/js-genai#707](https://github.com/googleapis/js-genai/issues/707)** — Premature turnComplete (OPEN, **P2**, 8+ months, 40+ confirmations, core issue)
- **[google-gemini/live-api-web-console#117](https://github.com/google-gemini/live-api-web-console/issues/117)** — Model stops midway (OPEN)
- **[googleapis/python-genai#872](https://github.com/googleapis/python-genai/issues/872)** — Audio quality degradation (CLOSED, but problem persists)
- **[googleapis/js-genai#1209](https://github.com/googleapis/js-genai/issues/1209)** — 12-2025 model raspy voice (OPEN, P2)
- **[google-gemini/live-api-web-console#139](https://github.com/google-gemini/live-api-web-console/issues/139)** — Model self-interrupts, talks over itself (OPEN)
- **[googleapis/python-genai#1894](https://github.com/googleapis/python-genai/issues/1894)** — Post-tool-call hallucination (CLOSED by bot)
- **[googleapis/python-genai#1275](https://github.com/googleapis/python-genai/issues/1275)** — Response truncation (OPEN, P3)

### Community Forum Reports

- [Audio glitches / stuttering (2026-02)](https://discuss.ai.google.dev/t/gemini-live-api-experiencing-audio-glitches/121812)
- [10-15s delay (2026-02)](https://discuss.ai.google.dev/t/significant-delay-with-gemini-live-2-5-flash-native-audio/122650)
- [5-6s response latency](https://discuss.ai.google.dev/t/live-api-5-6-second-response-latency/123254)
- [Audio plays only 1.5-2.5 words (2025-06)](https://discuss.ai.google.dev/t/gemini-2-5-native-dialog-audio-problems/90059)
- [Control characters instead of audio](https://discuss.ai.google.dev/t/bug-gemini-2-5-flash-native-audio-outputs-control-characters-ctrl-instead-of-audio-causing-silent-responses/115050)

### Developer Sentiment

From Issue #707:
> *"We gave up and switched over to gpt-realtime"* — @jgontrum
>
> *"We are about to develop our own pipeline to replace it"* — @AhmedAskar12
>
> *"We tend to fall back on the cascade pipeline"* — @wehos

Developers are actively leaving the platform due to this unresolved issue.

## Request

1. **Acknowledge** this as a server-side model issue, not a client-side echo problem
2. **Prioritize** a fix — P2 for 8+ months is too long for a production-blocking bug
3. **Provide a timeline** or interim workaround beyond "use headphones"
4. **Consider accessibility use cases** — visually impaired users cannot be told to "just wear headphones" as a prerequisite
