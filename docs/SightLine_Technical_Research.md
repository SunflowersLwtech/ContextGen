# SightLine: Wide Technical Research Report

> **Date**: 2026-02-21
> **Purpose**: Technology selection and feasibility research for SightLine
> **Competition**: Gemini Live Agent Challenge (Deadline: 2026-03-16)
> **Methodology**: 7 parallel research agents covering all technical domains

---

## Executive Summary

### Top-Level Architecture Decision

```
Phone (React PWA / Vite)
  |-- getUserMedia (camera + mic)
  |-- Canvas: 768x768 JPEG @ 1 FPS
  |-- AudioWorklet: PCM 16kHz mono
  |-- WebSocket → Cloud Run (server-to-server)
  |
  v
Cloud Run (FastAPI + ADK)
  |-- ADK Runner.run_live() + LiveRequestQueue
  |-- WebSocket (WSS) → Gemini Live API
  |
  v
Gemini Live API (WebSocket, v1alpha)
  |-- Model: gemini-2.5-flash-native-audio-preview-12-2025 (Live API still 2.5 only)
  |-- Proactive Audio + Affective Dialog
  |-- Function Calling (face ID, maps, memory)
  |-- Context Window Compression (unlimited sessions)
  |
  v
ADK Agent Hierarchy (Cloud Run 内)
  |-- Orchestrator Agent (2.5 Flash native audio) -> routes to sub-agents
  |-- Vision Sub-Agent (Gemini 3.1 Pro) -> deep scene analysis
  |-- OCR Sub-Agent (Gemini 3 Flash) -> text reading [FREE]
  |-- Navigation Sub-Agent (Gemini 3 Flash) -> Maps + Geocoding [FREE]
  |-- Face ID Sub-Agent -> InsightFace (ONNX) + Firestore
  |-- Memory Sub-Agent -> Firestore vector search + gemini-embedding-001
  |-- Grounding Sub-Agent (Gemini 3 Flash) -> Google Search [FREE]
  |
  v
Firestore
  |-- User profiles & preferences
  |-- Face embeddings (512-dim vectors, native vector search)
  |-- Long-term memory (text embeddings via gemini-embedding-001, native vector search)
  |-- Conversation summaries
```

### Key Discoveries

| Finding | Impact |
|---------|--------|
| Gemini Live API supports **Proactive Audio** | AI can decide when to speak -- core for "knowing when to shut up" |
| Gemini Live API supports **Affective Dialog** | AI adjusts tone based on user emotion -- core for personality |
| ADK has **native bidi-streaming** via `LiveRequestQueue` | Purpose-built for real-time audio/video multi-agent systems |
| Firestore has **native vector search** (KNN) | No separate vector DB needed for RAG or face embeddings |
| **InsightFace** (ONNX) beats all other face recognition options | 99.83% accuracy, ~150ms/frame CPU, 512-dim fits Firestore |
| Google has **NO** face recognition API (only detection) | Must use open-source (InsightFace) for face matching |
| Gemini native OCR is **competitive** with Cloud Vision | No need for separate OCR pipeline for book reading |
| **Gemini 3 Flash is FREE** during preview and outperforms 2.5 Pro | Near-zero cost for all sub-agents |
| **Gemini 3 models do NOT support Live API** | Orchestrator must stay on 2.5 Flash native audio |
| **`media_resolution` parameter** (Gemini 3) | LOD-aware token optimization: 70 tokens (LOD 1) vs 1120 (LOD 3) |
| **`gemini-embedding-001`** is GA with 3072 dims | Replaces deprecated `text-embedding-004`, better retrieval quality |
| Gemini has **native Google Maps grounding** | `google_maps` tool for exploratory queries |
| Video sessions hard-cap at **2 minutes** without compression | MUST enable `contextWindowCompression` |
| iOS standalone PWA has **broken camera access** | Need Safari fallback or Capacitor wrapper |
| OpenStreetMap has **best accessibility data** | Tactile paving, audible signals -- free API, complements Google Maps |
| Previous competition had a "Live Assistant for Blind People" winner | Must differentiate with LOD + Context Awareness |

---

## 1. Gemini Live API -- Core Communication Layer

### 1.1 Configuration (CRITICAL SETTINGS)

```python
from google import genai
from google.genai import types

# MUST use v1alpha for Proactive Audio + Affective Dialog
client = genai.Client(
    api_key="YOUR_API_KEY",
    http_options={"api_version": "v1alpha"}
)

# Model: use the 12-2025 version (09-2025 deprecated March 19, 2026)
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],

    # System instruction
    system_instruction=types.Content(
        parts=[types.Part(text="You are SightLine...")]
    ),

    # Proactive Audio: AI decides when to speak unprompted
    proactivity=types.ProactivityConfig(
        proactive_audio=True
    ),

    # Affective Dialog: detect and respond to user emotions
    # BUG: must be top-level, NOT inside GenerationConfig
    enable_affective_dialog=True,

    # Audio Transcription: real-time STT/TTS transcripts (ADK bidi-demo standard)
    # Used for: frontend captions, LOD Engine intent analysis, Memory Agent storage
    input_audio_transcription=types.AudioTranscriptionConfig(),
    output_audio_transcription=types.AudioTranscriptionConfig(),

    # MUST ENABLE: without this, video sessions cap at 2 minutes
    # Audio accumulates ~25 tokens/sec (Google Best Practices)
    context_window_compression=types.ContextWindowCompressionConfig(
        trigger_tokens=100000,                       # compress when reaching 100K tokens
        sliding_window=types.SlidingWindow(target_tokens=80000),  # compress down to 80K
    ),

    # Session resumption: reconnect within 2 hours
    session_resumption=types.SessionResumptionConfig(
        handle=None  # set to previous handle on reconnect
    ),

    # VAD configuration
    realtime_input_config=types.RealtimeInputConfig(
        automatic_activity_detection=types.AutomaticActivityDetection(
            start_of_speech_sensitivity="MEDIUM",
            end_of_speech_sensitivity="MEDIUM",
            prefix_padding_ms=200,
            silence_duration_ms=1000,
        )
    ),

    # Tools (Function Calling)
    tools=[...],
)
```

### 1.2 Media Formats

| Direction | Format | Details |
|-----------|--------|---------|
| Audio Input | PCM 16-bit LE | 16 kHz, mono |
| Audio Output | PCM 16-bit LE | 24 kHz, mono |
| Video Input | JPEG, base64 | 768x768, processed at **1 FPS** |
| Token cost (audio) | 25 tokens/sec | |
| Token cost (video) | 258 tokens/frame | |

### 1.3 Non-Blocking Function Calls

For face recognition and other async tools, use non-blocking execution:

```python
types.FunctionDeclaration(
    name="identify_person",
    description="Identify a person from the face library",
    behavior="NON_BLOCKING",  # Don't pause conversation
    # Scheduling: INTERRUPT / WHEN_IDLE / SILENT
)
```

- `INTERRUPT`: Result immediately interrupts current speech (for urgent alerts)
- `WHEN_IDLE`: Result delivered when model finishes speaking (for face ID)
- `SILENT`: Result stored in context silently (for background enrichment)

### 1.4 Session Limits

| Configuration | Audio-Only | Audio + Video |
|---------------|-----------|---------------|
| Without compression | 15 min | **2 min** |
| With compression | Unlimited | Unlimited |
| Connection lifetime | ~10 min (reconnect with resumption) | |
| Free tier concurrent sessions | 3 | |
| Tier 1 concurrent sessions | 50 | |

### 1.5 Latency Benchmarks

| Scenario | Latency (first audio chunk) |
|----------|---------------------------|
| Best case (audio-only, warm) | 320-800ms |
| Typical (audio + video) | 1-4s |
| Worst case (spikes) | 5-15s |

**Mitigation**: Streaming audio playback (play chunks as they arrive), pre-emptive feedback ("Let me look..."), intelligent frame selection.

---

## 2. Google ADK -- Multi-Agent Framework

### 2.1 Why ADK (Not LangGraph/CrewAI)

| Factor | ADK | LangGraph | CrewAI |
|--------|-----|-----------|--------|
| Gemini Live bidi-streaming | **Native** | No | No |
| `LiveRequestQueue` for audio/video | **Built-in** | No | No |
| Agent transfer (routing) | Automatic via LLM | Manual graph edges | Sequential/hierarchical |
| Per-agent model selection | Yes | Yes | Yes |
| Cloud Run deployment | One command | Self-hosted | Self-hosted |
| Real-time capable | **Yes** | No (batch) | No (batch) |

### 2.2 Agent Hierarchy Pattern

```python
from google.adk.agents import LlmAgent

# Sub-agents use Gemini 3 models (via REST API, not Live API)
vision_agent = LlmAgent(
    name="VisionAnalyzer",
    model="gemini-3.1-pro-preview",  # 3.1 Pro for deep vision (best reasoning)
    description="Detailed scene analysis for blind users",
    instruction="...",
    output_key="scene_description",
)

ocr_agent = LlmAgent(
    name="TextReader",
    model="gemini-3-flash-preview",  # 3 Flash: FREE, outperforms 2.5 Pro
    description="OCR and text reading from images",
    instruction="...",
    output_key="text_content",
)

nav_agent = LlmAgent(
    name="Navigator",
    model="gemini-3-flash-preview",  # 3 Flash: FREE, better tool calling
    description="Location awareness and navigation",
    instruction="...",
    tools=[get_location_info, search_nearby, get_directions],
    output_key="navigation_guidance",
)

# Orchestrator: stays on 2.5 Flash for Live API bidi-streaming
# (Gemini 3 does NOT support Live API as of Feb 2026)
root_agent = LlmAgent(
    name="SightLine",
    model="gemini-2.5-flash",        # 2.5 Flash required for Live API
    instruction="Route based on user intent and safety priority...",
    sub_agents=[vision_agent, ocr_agent, nav_agent],
)
```

### 2.3 Bidi-Streaming with ADK

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

runner = Runner(
    agent=root_agent,
    app_name="sightline",
    session_service=InMemorySessionService(),
)

# Create live request queue for real-time streaming
live_request_queue = runner.create_live_request_queue()

# Start live agent session
live_events = runner.run_live(
    session_id=session.id,
    user_id="user_1",
    live_request_queue=live_request_queue,
)

# Enqueue audio/video in real-time
live_request_queue.send_realtime(audio_or_video_data)
```

### 2.4 State Management

```python
# State key prefixes control scope:
# No prefix     -> current invocation only
# "temp:"       -> cleared between turns
# "user:"       -> persists across all sessions for user
# "app:"        -> persists across all users

tool_context.state["user:preferred_verbosity"] = "detailed"
tool_context.state["temp:current_frame_analysis"] = result
```

### 2.5 Deployment

```bash
# One-command Cloud Run deployment
adk deploy cloud_run \
  --project=$PROJECT_ID \
  --region=us-central1 \
  --service_name=sightline-agent \
  --with_ui \
  ./sightline_app
```

---

## 3. Face Recognition -- InsightFace (Primary Choice)

### 3.1 Why InsightFace

| Criterion | InsightFace | DeepFace | face_recognition |
|-----------|-------------|----------|-----------------|
| LFW Accuracy | **99.83%** | 99.65% | 99.38% |
| Embedding dims | 512 | 512 (ArcFace) | 128 |
| CPU latency/frame | **100-250ms** | 150-500ms | 300-400ms |
| Inference backend | **ONNX** (no TF/PyTorch) | TensorFlow | dlib (C++) |
| Docker image size | ~1.2GB | ~2GB | ~2GB |
| Maintained | Yes (Nov 2025) | Yes | **No (abandoned ~2022)** |
| Firestore compatible | 512-dim fits 2048 max | Yes | Yes |

### 3.2 Setup Code

```python
import insightface
from insightface.app import FaceAnalysis
import numpy as np

# Initialize once at startup
app = FaceAnalysis(
    name="buffalo_l",                    # best accuracy model
    providers=["CPUExecutionProvider"]    # CPU-only for Cloud Run
)
app.prepare(ctx_id=0, det_size=(640, 640))

# Register a face (generate 512-dim embedding)
def register_face(image) -> list[float]:
    faces = app.get(image)
    if not faces:
        return None
    face = sorted(faces, key=lambda x: (x.bbox[2]-x.bbox[0])*(x.bbox[3]-x.bbox[1]), reverse=True)[0]
    emb = face.embedding / np.linalg.norm(face.embedding)
    return emb.tolist()

# Match against library (cosine similarity)
def match_face(unknown_emb, known_persons, threshold=0.4):
    unknown = np.array(unknown_emb)
    unknown = unknown / np.linalg.norm(unknown)
    best_name, best_score = None, -1.0
    for person in known_persons:
        known = np.array(person["embedding"])
        score = float(np.dot(unknown, known))
        if score > threshold and score > best_score:
            best_score = score
            best_name = person["name"]
    return best_name, best_score
```

### 3.3 Firestore Storage

```python
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

# Store embedding
doc_ref.set({
    "name": "David",
    "relationship": "boss",
    "embedding": Vector(embedding_512dim),
    "created_at": firestore.SERVER_TIMESTAMP,
})

# Native KNN vector search
results = collection.find_nearest(
    vector_field="embedding",
    query_vector=Vector(unknown_embedding),
    distance_measure=DistanceMeasure.DOT_PRODUCT,
    limit=1,
)
```

### 3.4 Gemini Integration (Function Calling)

```python
# Gemini calls identify_person tool -> server runs InsightFace -> returns result
# Use behavior="NON_BLOCKING" with WHEN_IDLE scheduling
# Result: {"name": "David", "relationship": "boss", "confidence": 0.87}
# Gemini weaves into natural speech: "Your boss David is walking towards you, smiling."
```

### 3.5 Dockerfile

```dockerfile
FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0
RUN pip install insightface==0.7.3 onnxruntime==1.17.0 opencv-python-headless numpy
# Pre-download models
RUN python -c "from insightface.app import FaceAnalysis; \
    app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']); \
    app.prepare(ctx_id=0)"
```

---

## 4. RAG & Long-Term Memory -- Firestore Vector Search

### 4.1 Architecture

```
TIER 1: Ephemeral (ms~s)     -> Gemini context window / ADK session state
TIER 2: Session (min~hr)     -> ADK Session State (in-memory)
TIER 3: Long-term (permanent) -> Firestore with vector embeddings
```

### 4.2 Firestore Vector Search Specs

| Feature | Value |
|---------|-------|
| Max embedding dimensions | 2,048 |
| Distance measures | COSINE, EUCLIDEAN, DOT_PRODUCT |
| Index type | Flat (exact KNN) |
| Free tier | 50K reads, 20K writes/day |
| No extra cost | Vector fields are standard Firestore billing |

### 4.3 Memory Storage & Retrieval

```python
# Store memory with embedding
def store_memory(user_id, text, memory_type):
    embedding = genai.embed_content(
        model="gemini-embedding-001",  # GA, 3072 dims (truncated to 2048 for Firestore)
        content=text,
        config={"output_dimensionality": 2048},
    )['embedding']

    db.collection("users").document(user_id)\
      .collection("memories").document().set({
        "text": text,
        "type": memory_type,  # "preference", "location", "behavior"
        "embedding": Vector(embedding),
        "created_at": firestore.SERVER_TIMESTAMP,
    })

# Retrieve relevant memories
def retrieve_memories(user_id, query, limit=5):
    query_vec = genai.embed_content(
        model="gemini-embedding-001",
        content=query,
        config={"output_dimensionality": 2048},
    )['embedding']

    return db.collection("users").document(user_id)\
             .collection("memories").find_nearest(
        vector_field="embedding",
        query_vector=Vector(query_vec),
        distance_measure=DistanceMeasure.COSINE,
        limit=limit,
    )
```

### 4.4 Memory Consolidation (End of Session)

Use Gemini Flash to extract important facts from conversation history:
```python
# At session end -> Gemini analyzes conversation -> extracts memories
# -> stores with embeddings in Firestore
# Categories: preference, location, behavior, stress_trigger, routine
```

### 4.5 Gemini Context Caching

```python
# Cache system prompt + user profile (reused across turns)
# Note: Gemini 3 has automatic implicit caching — explicit caching optional
cache = client.caches.create(
    model="gemini-3-flash-preview",  # or gemini-3.1-pro-preview
    config=CreateCachedContentConfig(
        display_name="sightline-context",
        system_instruction=system_prompt + user_profile,
        ttl="3600s",
    )
)
# Gemini 3 Flash is FREE during preview; caching provides additional savings on Pro
```

### 4.6 Google Search Grounding

```python
# One line to enable factual verification
tools=[types.Tool(google_search=types.GoogleSearch())]
# Works in Live API: tools=[{"google_search": {}}]
```

---

## 5. Navigation -- Google Maps + Compass + Clock-Positions

### 5.1 API Choices

| API | Purpose | Free Tier | Hackathon Cost |
|-----|---------|-----------|---------------|
| Geocoding API | "Where am I?" | 10K/month | $0 |
| Places API (New) | "What's around me?" | 10K/month | $0 |
| Routes API | Walking directions | 10K/month | $0 |
| Maps JavaScript | Dev Console map | 10K loads/month | $0 |
| Gemini Maps Grounding | Exploratory queries | N/A | ~$5 |
| **Total** | | | **~$5** |

### 5.2 Clock-Position System

```python
def bearing_to_clock_direction(bearing, user_heading):
    relative = (bearing - user_heading + 360) % 360
    clock = round(relative / 30) % 12
    if clock == 0: clock = 12
    # "Starbucks at 2 o'clock, 50 meters"
```

Browser provides compass heading via `DeviceOrientationEvent` (requires permission on iOS).

### 5.3 Hybrid Strategy

- **Function Calling** (direct Maps API): For navigation, distances, directions -- we control clock-position formatting
- **Gemini Maps Grounding**: For exploratory queries ("tell me about this neighborhood") -- Gemini synthesizes reviews/ratings
- **OpenStreetMap Overpass**: For accessibility data (tactile paving, audible signals, kerb types) -- **free**

### 5.4 Vision + Location Fusion

Camera frame + GPS coordinates + compass heading are combined in a single Gemini prompt:
```
"You're at Market and 3rd. Crosswalk ahead. Walk signal is green. Starbucks 30m at 2 o'clock."
```

---

## 6. Frontend -- Vite + React PWA

### 6.1 Why Vite (Not Next.js/CRA)

- SightLine is a **SPA** (single-page app) -- no SSR needed
- Fastest dev experience (< 2s cold start, millisecond HMR)
- `vite-plugin-pwa` provides zero-config PWA setup
- Smallest bundle size for mobile performance
- CRA is deprecated; Next.js adds unnecessary server complexity

### 6.2 Architecture (Server-to-Server Mode)

> **⚠️ Architecture Decision**: 采用 Server-to-Server 模式 (Final Spec §6.1)。前端通过 WebSocket 连接 Cloud Run 后端，后端通过 ADK `run_live()` 连接 Gemini。不使用客户端直连。

```
Phone PWA
  |-- getUserMedia (native API, no WebRTC library needed)
  |-- AudioWorklet (PCM 16kHz chunking)
  |-- Canvas (768x768 JPEG frame grab)
  |-- WebSocket → Cloud Run (FastAPI + ADK)  ← NOT direct to Gemini
  |-- StreamingAudioPlayer (24kHz PCM playback)
  |-- GestureHandler (tap/double-tap/swipe/shake → WebSocket signals)
  |-- Wake Lock API (keep screen on)
  |-- DeviceOrientationEvent (compass heading)
  |-- Geolocation API (GPS tracking)
```

### 6.3 Transport Protocol

Gemini Live API **只支持 WebSocket (WSS)**。不支持 WebRTC、gRPC、或任何其他传输协议 (Google 官方确认)。

**Hackathon (Server-to-Server via Cloud Run)**:
1. 前端 WebSocket 连接 Cloud Run 后端: `ws://cloud-run-url/ws/{user_id}/{session_id}`
2. 后端通过 ADK `Runner.run_live()` + `LiveRequestQueue` 管理与 Gemini 的 bidi-streaming
3. 前端发送: audio (PCM 16kHz), image (JPEG), activity signals, telemetry (JSON)
4. 后端转发到 Gemini，接收响应后转发回前端
5. API Key 在后端 Secret Manager 中，前端不接触密钥
6. 参考实现: [google/adk-samples/bidi-demo](https://github.com/google/adk-samples/tree/main/python/agents/bidi-demo)

**Production (WebRTC 桥接优化)**:
```
Phone ──WebRTC (UDP, 抗弱网)──→ Pipecat/Daily Edge ──WebSocket (骨干网)──→ Cloud Run ──WSS──→ Gemini
```
在不稳定移动网络下，WebSocket 的 TCP 队头阻塞会导致延迟飙升至 10-15s。Pipecat + Daily 提供 WebRTC 桥接，用 UDP 处理"最后一公里"，显著降低感知延迟。Hackathon 阶段在受控 WiFi 下经 Cloud Run 中转即可 (320-800ms + ~10ms 一跳)。

### 6.4 iOS Gotcha

`getUserMedia` is broken in iOS standalone PWA mode. Workarounds:
- Detect iOS and open in Safari (not standalone)
- Or build a thin Capacitor native shell for iOS
- Android works fine

---

## 7. Test Scenario Implementation Guide

### 7.1 Book Reading (VCR Mode)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| OCR | **Gemini native** | Sufficient accuracy, understands context, no extra API |
| Page turn detection | User tap/voice + frame diff | More reliable than pure CV |
| TTS | **Gemini native audio** | Lowest latency, integrated |
| Reading position | Narrative Snapshot in session state | Resume from interruption point |

### 7.2 Gym/Fitness

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Equipment recognition | **Gemini Vision** | General understanding handles gym equipment well |
| Spatial guidance | **Clock-position from frame** | Object x-position -> direction; qualitative distance |
| Depth estimation | **Gemini spatial reasoning** | "nearby / a few steps / across the room" |
| Safety | System prompt rules | NEVER give form corrections (liability) |

### 7.3 Daily Life

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Product identification | **Gemini Vision** | Identifies brands, reads labels |
| Barcode scanning | ML Kit (client) + Gemini fallback | On-device speed |
| Currency recognition | **Gemini Vision** | Already in pipeline |
| Kitchen safety | Proactive Audio | Alert on flame, boiling, hazards |

### 7.4 Latency Optimization

| Strategy | Implementation | Phase |
|----------|---------------|-------|
| Streaming playback | Play audio chunks as they arrive (don't wait for complete response) | Hackathon |
| Pre-emptive feedback | "Let me look at that..." while Gemini processes | Hackathon |
| Frame selection | Client-side change detection; skip duplicate scenes | Hackathon |
| Context compression | `contextWindowCompression` for unlimited sessions | Hackathon |
| Session resumption | Reconnect within 2 hours with saved handle | Hackathon |
| Cloud Run warm | `min_instance_count=1`, `cpu_throttling=false` | Hackathon |
| Region matching | Deploy Cloud Run in same region as target users | Hackathon |
| **WebRTC 桥接** | **Pipecat + Daily: Phone←WebRTC→Edge←WebSocket→Gemini, 抗弱网** | **Production** |

---

## 8. Cost Estimates

### 8.1 Per-Session (10 minutes)

| Component | Tokens | Cost |
|-----------|--------|------|
| Live API audio input (10 min, 2.5 Flash) | 15,000 | $0.045 |
| Live API audio output (5 min, 2.5 Flash) | 7,500 | $0.090 |
| Live API video input (1 FPS, 2.5 Flash) | 154,800 | $0.464 |
| Sub-agent calls (3 Flash) | ~10,000 | **$0.00 (FREE)** |
| Vision deep calls (3.1 Pro, 2 calls) | ~5,000 | $0.07 |
| **Total per session** | **~192K** | **~$0.67** |

*Note: Live API native audio pricing is higher than standard API ($3.00/1M audio input, $12.00/1M audio output)*

### 8.2 Monthly (1 active user, 2hr/day)

| Component | Monthly Cost |
|-----------|-------------|
| Live API (2.5 Flash native audio) | ~$8.00 |
| Vision deep calls (3.1 Pro, 10/day) | ~$4.00 |
| Sub-agent calls (3 Flash) | **$0.00 (FREE)** |
| Maps APIs | $0 (free tier) |
| Cloud Run (1 min instance) | ~$17.00 |
| Firestore | $0 (free tier) |
| **Total** | **~$29/month** |

### 8.3 Hackathon Total (23 days dev + demo)

| Component | Estimated Cost |
|-----------|---------------|
| Live API (development + testing) | ~$25 |
| Sub-agent calls (Gemini 3 Flash) | **$0 (FREE)** |
| Vision deep calls (3.1 Pro) | ~$8 |
| Cloud Run | ~$20 |
| Maps APIs | ~$5 |
| Firestore | $0 |
| **Total hackathon cost** | **~$58** |

---

## 9. Competition Strategy

### 9.1 Judging Criteria Alignment

| Criterion (Weight) | SightLine Advantage |
|--------------------|-------------------|
| **Innovation & Multimodal UX (40%)** | Adaptive LOD (zero competitors), Proactive Audio (Gemini-exclusive), Affective Dialog, Context Awareness |
| **Technical Implementation (30%)** | ADK multi-agent, 5+ GCP services, InsightFace face recognition, Firestore vector search, Function Calling |
| **Demo & Presentation (30%)** | 4 compelling scenarios, Developer Console, real-time operation |

### 9.2 Mandatory Requirements Met

- [x] Gemini model (Flash + Pro)
- [x] Google GenAI SDK / ADK
- [x] Deploy on Google Cloud (Cloud Run)
- [x] Additional GCP service (Firestore, Cloud Logging, Secret Manager)

### 9.3 Bonus Points

| Bonus | Points | Status |
|-------|--------|--------|
| Technical blog (Medium + Dev.to) | +0.6 | Week 4 |
| Terraform deployment | +0.2 | Week 3 |
| GDG membership | +0.2 | **Do immediately** |

### 9.4 Differentiation from 2024 Winner

A "Live Assistant for Blind People" already won in 2024. SightLine MUST emphasize:
1. **Adaptive LOD** -- no competitor has this
2. **Context Awareness** (3-tier sensor fusion) -- unique
3. **"Knowing when to shut up"** -- the philosophical differentiator
4. **Narrative Snapshot** (interrupt + resume) -- novel

---

## 10. Technology Stack Summary

| Layer | Technology | Priority |
|-------|-----------|----------|
| **AI Model (Orchestrator/Live)** | Gemini 2.5 Flash native audio (Live API only supports 2.5) | P0 |
| **AI Model (Vision)** | Gemini 3.1 Pro (`gemini-3.1-pro-preview`) | P1 |
| **AI Model (Sub-agents)** | Gemini 3 Flash (`gemini-3-flash-preview`) — **FREE** | P0 |
| **Embeddings** | `gemini-embedding-001` (GA, 3072 dims) | P0 |
| **Agent Framework** | Google ADK (Python) | P0 |
| **Live Streaming** | Gemini Live API (WebSocket, v1alpha) | P0 |
| **Face Recognition** | InsightFace (buffalo_l, ONNX) | P2 |
| **Backend** | Cloud Run (min 1 instance, 2 vCPU) | P0 |
| **Database** | Firestore (vector search for RAG + faces) | P0 |
| **Search Grounding** | Google Search API | P1 |
| **Maps** | Places API (New) + Geocoding + Routes | P1 |
| **Accessibility Data** | OpenStreetMap Overpass API | P2 |
| **Frontend** | Vite + React PWA | P0 |
| **PWA Plugin** | vite-plugin-pwa | P0 |
| **Infrastructure** | Terraform + Cloud Build | P3 (bonus) |
| **Monitoring** | Cloud Logging | P3 |

### Priority Legend

- **P0**: Must have for MVP demo
- **P1**: Strongly needed for competitive submission
- **P2**: High-impact differentiator
- **P3**: Bonus points / nice-to-have

---

## 11. Critical Implementation Notes

### MUST-DO (will break things if missed)

1. **`api_version="v1alpha"`** -- required for Proactive Audio + Affective Dialog
2. **`enable_affective_dialog=True`** -- must be top-level in LiveConnectConfig (known Pydantic bug)
3. **`context_window_compression`** -- without it, video sessions cap at 2 minutes
4. **Live API model**: `gemini-2.5-flash-native-audio-preview-12-2025` (09-2025 deprecated March 19) — **Gemini 3 does NOT support Live API**
5. **Sub-agent models**: Use `gemini-3-flash-preview` (FREE) and `gemini-3.1-pro-preview` for REST API calls
6. **Embedding model**: Use `gemini-embedding-001` with `output_dimensionality=2048` (text-embedding-004 is deprecated)
7. **`thinking_level`** (not `thinking_budget`) for Gemini 3 sub-agents; Live API still uses `thinking_budget`
8. **`media_resolution`** parameter: Use for LOD-aware token optimization in Vision Sub-Agent
9. **`temperature=1.0`** for Gemini 3 models (lower values cause looping)
10. **Video at 1 FPS max** -- Gemini processes 1 frame/sec, sending more wastes bandwidth
11. **Audio format**: PCM 16kHz input, 24kHz output
12. **InsightFace models**: Pre-download in Dockerfile (avoids cold-start model download)
13. **Firestore vector index**: Must create before first vector query (gcloud CLI command)
14. **iOS PWA**: Don't use standalone mode; fall back to Safari for camera access
15. **Free tier limit**: Only 3 concurrent Gemini Live sessions -- use Tier 1 for demo

### Architecture Principles

- **2.5 Flash for Live API, Gemini 3 for sub-agents**: Orchestrator uses 2.5 Flash native audio (only Live API option); sub-agents use Gemini 3 Flash (FREE) / 3.1 Pro (best reasoning) via REST API
- **Function Calling for tool use**: Face ID, Maps, Memory all integrated via Gemini Function Calling
- **Non-blocking tools**: Face recognition uses NON_BLOCKING + WHEN_IDLE scheduling
- **Direct browser-to-Gemini**: No proxy for minimum latency; backend only mints ephemeral tokens
- **Firestore for everything persistent**: User profiles, face library, long-term memory -- all in one DB with native vector search
- **LOD-aware media_resolution**: Low (70 tokens) at LOD 1, High (1120 tokens) at LOD 3 -- 94% token savings for quick scans

---

## Sources (Organized by Topic)

### Gemini 3 Model Migration
- [Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3)
- [Gemini 3.1 Pro Announcement](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-1-pro/)
- [Gemini 3 Flash Announcement](https://blog.google/products/gemini/gemini-3-flash/)
- [Models Reference](https://ai.google.dev/gemini-api/docs/models)
- [Gemini Embedding GA](https://developers.googleblog.com/gemini-embedding-available-gemini-api/)
- [Embeddings Docs](https://ai.google.dev/gemini-api/docs/embeddings)

### Gemini Live API
- [Get Started](https://ai.google.dev/gemini-api/docs/live)
- [Capabilities Guide](https://ai.google.dev/gemini-api/docs/live-guide)
- [Tool Use](https://ai.google.dev/gemini-api/docs/live-tools)
- [Session Management](https://ai.google.dev/gemini-api/docs/live-session)
- [Ephemeral Tokens](https://ai.google.dev/gemini-api/docs/ephemeral-tokens)
- [Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Limits & Specs (Firebase)](https://firebase.google.com/docs/ai-logic/live-api/limits-and-specs)
- [Affective Dialog Bug (#865)](https://github.com/googleapis/python-genai/issues/865)

### Google ADK
- [Official Docs](https://google.github.io/adk-docs/)
- [GitHub Repo](https://github.com/google/adk-python)
- [Sample Agents](https://github.com/google/adk-samples)
- [Multi-Agent Systems](https://google.github.io/adk-docs/agents/multi-agents/)
- [Bidi-Streaming](https://google.github.io/adk-docs/streaming/)
- [Cloud Run Deployment](https://google.github.io/adk-docs/deploy/cloud-run/)
- [Session & State](https://google.github.io/adk-docs/sessions/state/)

### Face Recognition
- [InsightFace GitHub](https://github.com/deepinsight/insightface)
- [DeepFace GitHub](https://github.com/serengil/deepface)
- [Firestore Vector Search](https://firebase.google.com/docs/firestore/vector-search)

### Memory & RAG
- [Vertex AI RAG Engine](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/rag-overview)
- [ADK Memory Docs](https://google.github.io/adk-docs/sessions/memory/)
- [Gemini Context Caching](https://ai.google.dev/gemini-api/docs/caching)
- [Google Search Grounding](https://ai.google.dev/gemini-api/docs/google-search)

### Google Maps
- [Places API (New)](https://developers.google.com/maps/documentation/places/web-service)
- [Geocoding API](https://developers.google.com/maps/documentation/geocoding)
- [Routes API](https://developers.google.com/maps/documentation/routes)
- [Gemini Maps Grounding](https://ai.google.dev/gemini-api/docs/maps-grounding)
- [OpenStreetMap Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API)

### Frontend & PWA
- [Vite Plugin PWA](https://vite-pwa-org.netlify.app/guide/)
- [Live API Web Console (React)](https://github.com/google-gemini/live-api-web-console)
- [PWA Camera on iOS](https://bugs.webkit.org/show_bug.cgi?id=185448)

### Transport Protocol & WebRTC Bridge
- [Google AI Forum — No Native WebRTC](https://discuss.ai.google.dev/t/is-there-any-near-future-plans-to-have-native-webrtc-support-in-the-gemini-2-0-flash-live-multimodal-api-servers/57746)
- [Partner Integrations](https://ai.google.dev/gemini-api/docs/partner-integration)
- [Pipecat + Gemini WebRTC Demo](https://github.com/pipecat-ai/gemini-webrtc-web-simple)
- [Daily + Gemini Multimodal Live](https://www.daily.co/products/gemini/multimodal-live-api/)

### Competition
- [Gemini Live Agent Challenge](https://algo-mania.com/en/blog/hackathons-coding/gemini-live-agent-challenge-create-immersive-ai-agents-with-google-gemini-live/)
- [2024 Winners](https://ai.google.dev/competition)
- [Live Assistant for Blind (2024)](https://ai.google.dev/competition/projects/live-assistant-for-blind-people)

---

*This research report synthesizes findings from 7 parallel research agents covering all technical domains required for SightLine implementation. All recommendations are optimized for a 23-day hackathon timeline with the Google Gemini ecosystem.*

*Updated 2026-02-21: Model references updated to Gemini 3 (Flash/Pro) for sub-agents. Live API remains on Gemini 2.5 Flash native audio (no Gemini 3 Live API support yet). Embedding model updated to gemini-embedding-001. See `raw_research/infra/research_gemini_3_migration.md` for full migration analysis.*
