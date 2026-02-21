# Gemini Live API Technical Research for SightLine

> **Research Date**: 2026-02-21
> **Source**: Parallel research agent - Gemini Live API capabilities

---

## 1. Gemini Live API (WebSocket Streaming)

### 1.1 Connection Architecture

The Live API uses **WebSockets** for persistent, bidirectional communication. Two deployment patterns exist:

- **Client-to-Server (Direct)**: Frontend connects directly to Gemini via WebSocket. Lowest latency. Requires ephemeral tokens for security.
- **Server-to-Server (Proxied)**: Backend acts as WebSocket proxy. Slightly higher latency (+ms per hop). API key stays server-side.

**Basic Connection Setup (Python):**

```python
import asyncio
from google import genai
from google.genai import types

# For proactive audio / affective dialog, use v1alpha
client = genai.Client(
    api_key="YOUR_API_KEY",
    http_options={"api_version": "v1alpha"}
)

MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    system_instruction=types.Content(
        parts=[types.Part(text="""You are SightLine, a real-time visual assistant
        for visually impaired users. Describe the environment clearly, concisely,
        and proactively. Prioritize safety-critical information first.""")]
    ),
    enable_affective_dialog=True,
)

async def main():
    async with client.aio.live.connect(model=MODEL, config=config) as session:
        pass

asyncio.run(main())
```

### 1.2 Proactive Audio

This is the single most important capability for SightLine. Instead of request-response, **the AI decides when to speak unprompted**.

- Moves beyond simple Voice Activity Detection
- Model intelligently decides when to respond and when to remain silent
- Only responds when content is relevant; ignores non-device-directed queries
- Requires `api_version="v1alpha"`

**Configuration:**

```python
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    enable_affective_dialog=True,
    proactivity=types.ProactivityConfig(
        proactive_audio=True
    ),
)
```

**SightLine application**: When the camera detects a hazard (approaching car, stairs, obstacle), the AI speaks up without being asked. This transforms SightLine from an "ask-and-answer" tool to a proactive safety companion.

### 1.3 Affective Dialog

Enables the model to:
- Natively process raw audio to interpret subtle acoustic nuances (tone, emotion, pace)
- Detect the user's emotional state (frustration, confusion, anxiety)
- Adjust its own tone to respond with appropriate empathy

**Configuration** -- set as a top-level field in `LiveConnectConfig`, NOT inside `GenerationConfig()` (known Pydantic validation bug):

```python
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    enable_affective_dialog=True,
)
```

### 1.4 Function Calling Within Live Sessions

Functions are defined in the session config and handled manually during streaming:

```python
# Define tools
navigate_to = types.FunctionDeclaration(
    name="navigate_to",
    description="Get walking directions to a destination",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "destination": types.Schema(type="STRING", description="Target location"),
        },
        required=["destination"]
    )
)

config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    tools=[types.Tool(function_declarations=[navigate_to])],
)

# Handle function calls during streaming
async with client.aio.live.connect(model=MODEL, config=config) as session:
    async for response in session.receive():
        if response.tool_call:
            function_responses = []
            for fc in response.tool_call.function_calls:
                result = await get_directions(fc.args["destination"])
                function_responses.append(
                    types.FunctionResponse(
                        id=fc.id,
                        name=fc.name,
                        response={"result": result}
                    )
                )
            await session.send_tool_response(function_responses=function_responses)
```

**Asynchronous (non-blocking) execution** is supported via `behavior="NON_BLOCKING"` on the function declaration, with scheduling options:
- `INTERRUPT` -- respond immediately (for urgent safety alerts)
- `WHEN_IDLE` -- respond when model finishes current output
- `SILENT` -- store result without interrupting (background context)

### 1.5 Supported Media Formats

**Audio:**

| Direction | Format | Sample Rate | Channels | Bit Depth |
|-----------|--------|-------------|----------|-----------|
| Input | Raw PCM, little-endian | 16 kHz | Mono | 16-bit |
| Output | Raw PCM | 24 kHz | Mono | 16-bit |

MIME type: `audio/pcm;rate=16000`. Also accepts `audio/flac`, `audio/mp3`, `audio/wav`, `audio/webm`, and others.

**Video / Image Frames:**

| Parameter | Specification |
|-----------|--------------|
| Processing rate | **1 frame per second** |
| Recommended resolution | 768x768 native |
| Token cost | ~258 tokens per frame (at 384px or below); larger images tiled into 768x768 at 258 tokens each |
| Supported image types | PNG, JPEG, WEBP, HEIC, HEIF |
| Supported video containers | FLV, QuickTime, MPEG, MP4, WebM, WMV, 3GPP |

**Critical**: Video is processed at **1 FPS**. This is adequate for SightLine (walking pace) but do not send frames faster than 1 FPS -- it wastes bandwidth.

### 1.6 Latency Benchmarks

- **Target**: Anything over 200-300 ms between stop-speaking and start-hearing breaks conversational rhythm
- **Best case (direct WebSocket)**: ~200-500 ms round-trip for audio-only
- **Typical case (proxied)**: ~500-1500 ms
- **Worst case (spikes)**: 5-15 seconds reported during peak loads (late 2025 developer reports)
- Video+audio has higher latency due to frame processing overhead

### 1.7 Rate Limits and Quotas

**Concurrent Session Limits:**

| Tier | Concurrent Sessions |
|------|---------------------|
| Free | 3 per API key |
| Tier 1 (Pay-as-you-go) | 50 per project |
| Tier 2 | Up to 1,000 per project |

**Session Duration Limits (without compression):**

| Mode | Maximum Duration |
|------|-----------------|
| Audio-only | 15 minutes |
| Audio + Video | **2 minutes** |
| Connection lifetime | ~10 minutes |
| Context window | 128K tokens |

With `contextWindowCompression` + `SlidingWindow` enabled, sessions extend **indefinitely**.

**General API Rate Limits:**

| Tier | RPM | TPM |
|------|-----|-----|
| Free | 5-15 | 250K |
| Tier 1 | 150-300 | Higher |

---

## 2. Gemini 2.5 Flash vs Gemini 2.5 Pro

### Head-to-Head Comparison

| Dimension | 2.5 Flash | 2.5 Pro |
|-----------|-----------|---------|
| Context Window | 1,000,000 tokens | 1,000,000 tokens |
| Input Price (text) | $0.30 / 1M tokens | $1.25 / 1M tokens |
| Output Price (text) | $2.50 / 1M tokens | $10.00 / 1M tokens |
| Audio Input | $1.00 / 1M tokens | Higher |
| Speed | Fast (real-time optimized) | Slower (deeper reasoning) |
| MMMU (Vision) | ~75% (estimated) | **81.7%** (state-of-the-art) |
| VideoMME | Competitive | **84.8%** |
| Live API Support | **Yes (native audio model)** | Limited live support |
| Native Audio Model | `gemini-2.5-flash-native-audio-preview-12-2025` | Not available for live |

### Which is better for real-time orchestration?

**Gemini 2.5 Flash** -- has a dedicated native audio model for Live API, is purpose-built for speed and low latency, supports hybrid reasoning with controllable thinking depth, and is 4x cheaper on both input and output.

### Which is better for deep vision understanding?

**Gemini 2.5 Pro** -- 81.7% MMMU (significantly better visual reasoning), 84.8% VideoMME (state-of-the-art video), 69.4% Vibe-Eval (leading image comprehension), superior at complex spatial reasoning and OCR edge cases.

### Can they be used together?

**Yes, and this is the recommended architecture.** Flash runs the live session for real-time conversation. When a user needs deep analysis ("Read this entire menu", "Describe everything in this room in detail"), Flash triggers a function call that sends the current frame to Pro via REST API, then speaks the result.

### Pricing Estimate (per active user, 1 hour/day)

| Component | Flash Cost | Pro Cost |
|-----------|------------|----------|
| Audio input (1hr/day, ~28.8M tokens/mo) | ~$28.80 | N/A |
| Video frames (1fps, ~27.9M tokens/mo) | ~$8.37 | N/A |
| Text output (~3M tokens/mo) | ~$7.50 | N/A |
| Deep vision calls (10/day via Pro) | N/A | ~$3.38 |
| **Combined monthly total** | **~$48/month** | |

---

## 3. Gemini Vision Capabilities

### Scene Description
- Strong general scene understanding (objects, people, activities, indoor/outdoor, lighting)
- Spatial relationships ("chair to the left of the table", "stairs ahead")
- Safety features: Can identify obstacles, vehicles, crosswalks, traffic lights
- Relative depth ordering ("closer/farther") -- absolute distances are limited
- Pro is significantly better than Flash for detailed descriptions

### OCR Accuracy
- **Strengths**: High accuracy on printed text, multi-language, reasons about content (not just transcribes), processes PDFs natively, good with signs/labels/menus at reasonable distances
- **Limitations**: Handwritten text varies, very small/distant text may be missed, decorative fonts challenging, low-light/motion blur degrades accuracy

### Face Detection
- Can detect presence of people/faces and count approximate numbers
- Can describe general appearance (clothing, posture, activity)
- Returns bounding box coordinates for detected people
- Will NOT perform facial recognition (identifying who someone is)
- Will NOT make definitive statements about age, race, or gender
- Has safety filters around face-related queries

### Facial Expression Description
- **Yes, Gemini can describe facial expressions**: smiling, frowning, surprised, confused
- With affective dialog enabled, detects emotional tone from both visual AND audio cues
- Uses hedging language ("appears to", "seems to") rather than definitive attributions

### Object Detection and Spatial Relationships
- Bounding boxes in `[y0, x0, y1, x1]` format, normalized to 0-1000 scale
- Segmentation with contour masks and probability maps (Gemini 2.5+)
- Relative positioning, depth ordering, grouping, directional descriptions
- Experimental 3D spatial understanding

---

## 4. Integration Patterns

### 4.1 Sending Video + Audio Simultaneously

Run parallel async tasks on the same WebSocket:

```python
async def send_audio(session, audio_stream):
    while True:
        audio_data = audio_stream.read(1024, exception_on_overflow=False)
        await session.send_realtime_input(
            audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
        )
        await asyncio.sleep(0.01)

async def send_video(session, cap):
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        frame = cv2.resize(frame, (768, 768))
        _, buffer = cv2.imencode('.jpg', frame)
        await session.send_realtime_input(
            video=types.Blob(data=buffer.tobytes(), mime_type="image/jpeg")
        )
        await asyncio.sleep(1.0)  # 1 FPS

async def receive_responses(session, playback_stream):
    async for response in session.receive():
        if response.server_content:
            if response.server_content.interrupted:
                clear_audio_queue()
                continue
            if response.server_content.model_turn:
                for part in response.server_content.model_turn.parts:
                    if part.inline_data:
                        playback_stream.write(part.inline_data.data)
        if response.tool_call:
            await handle_tool_calls(session, response.tool_call)

# Run all three concurrently
await asyncio.gather(
    send_audio(session, mic_stream),
    send_video(session, cap),
    receive_responses(session, speaker_stream),
)
```

### 4.2 Injecting Context Mid-Session

System instructions are set at connection time. For mid-session updates, use `send_client_content`:

```python
await session.send_client_content(
    turns=types.Content(
        role="user",
        parts=[types.Part(text="""[CONTEXT UPDATE] User entered a restaurant.
        Prioritize: menu reading, table layout, staff identification.""")]
    ),
    turn_complete=False  # Don't trigger a model response
)
```

### 4.3 Handling Interruptions

Automatic VAD is enabled by default. Configure sensitivity:

```python
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    realtime_input_config=types.RealtimeInputConfig(
        automatic_activity_detection=types.AutomaticActivityDetection(
            start_of_speech_sensitivity="MEDIUM",
            end_of_speech_sensitivity="MEDIUM",
            prefix_padding_ms=200,
            silence_duration_ms=1000,
        )
    )
)
```

When interrupted, the server cancels current generation and sets `interrupted=True`. The client must stop playback and clear its audio queue immediately.

### 4.4 Session Management

**Context window compression** for unlimited session duration:

```python
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    context_window_compression=types.ContextWindowCompressionConfig(
        sliding_window=types.SlidingWindow(),
    ),
)
```

**Session resumption** across connections (tokens valid for 2 hours):

```python
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    session_resumption=types.SessionResumptionConfig(
        handle=previous_handle  # None for first connection
    ),
)

# Capture resumption tokens from responses
async for response in session.receive():
    if response.session_resumption_update:
        if response.session_resumption_update.handle:
            saved_handle = response.session_resumption_update.handle
```

---

## 5. Critical Implementation Notes for SightLine

1. **API Version**: Must use `v1alpha` for proactive audio and affective dialog
2. **Model Name**: `gemini-2.5-flash-native-audio-preview-12-2025` (the older `09-2025` version is deprecated March 19, 2026)
3. **ALWAYS enable `contextWindowCompression`** -- without it, audio+video sessions hard-cap at 2 minutes
4. **`enable_affective_dialog` bug**: Must be top-level in `LiveConnectConfig`, not inside `GenerationConfig`
5. **1 FPS processing**: Do not send frames faster than 1 FPS
6. **Free tier**: Only 3 concurrent sessions -- use paid Tier 1 for the demo
7. **Dual-model pipeline** (Flash live + Pro REST) shows technical sophistication for judges
8. **Ephemeral tokens**: Use for client-side connections rather than exposing API keys

---

## Sources

**Official Google Documentation:**
- [Get Started with Live API](https://ai.google.dev/gemini-api/docs/live)
- [Live API Capabilities Guide](https://ai.google.dev/gemini-api/docs/live-guide)
- [Tool Use with Live API](https://ai.google.dev/gemini-api/docs/live-tools)
- [Session Management](https://ai.google.dev/gemini-api/docs/live-session)
- [Vision Capabilities](https://ai.google.dev/gemini-api/docs/vision)
- [Image Understanding](https://ai.google.dev/gemini-api/docs/image-understanding)
- [Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Pricing](https://ai.google.dev/gemini-api/docs/pricing)

**Google Cloud / Vertex AI:**
- [Live API Overview (Vertex AI)](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api)
- [Gemini 2.5 Flash with Live API](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-live-api)
- [Native Audio Blog Post](https://cloud.google.com/blog/topics/developers-practitioners/how-to-use-gemini-live-api-native-audio-in-vertex-ai)
- [Vertex AI Quotas](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/quotas)

**Firebase:**
- [Live API Limits and Specs](https://firebase.google.com/docs/ai-logic/live-api/limits-and-specs)

**Developer Community:**
- [enable_affective_dialog Issue #865](https://github.com/googleapis/python-genai/issues/865)
- [Latency Discussion](https://discuss.ai.google.dev/t/gemini-live-api-models-high-latency/108989)
- [Concurrent Sessions Discussion](https://discuss.ai.google.dev/t/gemini-live-api-tier-2-project-still-limited-to-50-concurrent-connections-and-billed-as-tier-1/94634)

**Benchmarks:**
- [Gemini 2.5 Flash (Artificial Analysis)](https://artificialanalysis.ai/models/gemini-2-5-flash)
- [Gemini 2.5 Pro (Artificial Analysis)](https://artificialanalysis.ai/models/gemini-2-5-pro)
- [Flash vs Pro Comparison](https://llm-stats.com/models/compare/gemini-2.5-flash-vs-gemini-2.5-pro)
