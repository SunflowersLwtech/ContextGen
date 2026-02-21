# Test Scenarios & OCR Implementation Research for SightLine

> **Research Date**: 2026-02-21
> **Source**: Parallel research agent - Test scenarios, OCR, fitness, daily life, latency

---

## SCENARIO 1: Book/Document Reading (VCR Mode)

### OCR Comparison

| Solution | Accuracy | Latency | Cost | Recommendation |
|----------|----------|---------|------|---------------|
| Cloud Vision OCR | 98.7% printed, 92.3% handwritten | Extra API call | $1.50/1K | Hybrid option |
| **Gemini Native OCR** | ~95%+ (Pro #3 on OCR Arena) | Zero extra latency | Included | **PRIMARY** |
| Document AI | Highest for structured docs | Heavy | Complex | Overkill |

**Decision**: Gemini native OCR -- sufficient for reading aloud, understands context (skip headers/footers), no extra API call.

### Page Turn Detection

- Gemini processes at 1 FPS -- page turns happen faster
- **Hackathon approach**: user voice/tap ("I turned the page")
- **Production approach**: client-side frame diff detection, send stabilized post-turn frame

### TTS for Long-Form Reading

- **Gemini Native Audio**: 320-800ms first response, 30 prebuilt voices
- **Gemini TTS**: better for audiobook quality, exact text recitation
- **Recommendation**: Native audio for hackathon throughout

---

## SCENARIO 2: Gym/Fitness Equipment Recognition

### Equipment Identification

- **Gemini Vision (RECOMMENDED)**: General understanding handles gym equipment without custom models
- Roboflow dataset exists (6,620 images) but unnecessary with Gemini
- Google Cloud Vision too generic ("machine", not "treadmill")

### Spatial Guidance

- **Clock-position from camera frame**: object x-position -> "treadmill at 2 o'clock"
- **Qualitative distances**: "nearby / a few steps / across the room" from apparent size
- **Gemini spatial reasoning**: relative distance from visual cues
- NO precise meter measurements without depth sensor

### Safety Rules (System Prompt)

- NEVER give exercise form corrections (liability)
- DO describe equipment settings (weight, incline)
- ALWAYS warn about: occupied equipment, weights on floor, wet surfaces
- Suggest asking gym staff for guidance

---

## SCENARIO 3: Daily Life

### Food Delivery
- Gemini can process screen captures via Proactive Audio
- Read delivery notifications, identify delivery person by appearance
- Better than face comparison: read name badge / confirm via app

### Barcode/QR Scanning
- **ML Kit (client-side)**: on-device, free, all standard formats
- **Gemini Vision (fallback)**: can read barcodes but not optimized
- Hybrid: ML Kit detects -> server does product lookup

### Product Identification
- **Gemini Vision**: identifies brands, reads labels, estimates sizes
- Cloud Vision Product Search requires pre-built catalog (impractical)
- Gemini 2.5: object segmentation with bounding boxes

### Currency Recognition
- **Gemini Vision**: identifies denominations across major currencies
- Dedicated apps exist (EyeNote, Cash Reader) for reference

### Kitchen Safety
- Gemini detects: flames, boiling water, steam, sharp objects
- Proactive alerts via system prompt rules
- Temperature descriptions from visual cues

---

## SCENARIO 4: Latency Optimization

### Gemini Live API Benchmarks

| Metric | Value |
|--------|-------|
| First audio response | **320-800ms** (sub-800ms) |
| 2-3x faster than traditional STT->LLM->TTS | |
| Scaled to 50+ concurrent, 1GB RAM | |

### Streaming TTS

YES -- Gemini starts speaking before finishing "thinking". Audio chunks stream in real-time.

**Caveat**: NON_BLOCKING function calls may cause hallucinated speculative answers while waiting for results. Use BLOCKING for critical info.

### Frame Selection Strategy

| LOD Level | Strategy |
|-----------|----------|
| LOD 3 (stationary/reading) | 1 frame / 2-3 seconds |
| LOD 1-2 (walking) | 1 frame / second, skip duplicates |
| Emergency | Immediate frame, skip queue |

Token cost: 10 min @ 1 FPS = ~154,800 tokens = ~$0.05

### Audio Interruption

VAD detects user speech -> generation canceled -> `interrupted=True`

```python
config = types.LiveConnectConfig(
    realtime_input_config=types.RealtimeInputConfig(
        automatic_activity_detection=types.AutomaticActivityDetection(
            start_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
            end_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
            silence_duration_ms=500,
        )
    )
)
```

### Cloud Run Optimization

```terraform
resource "google_cloud_run_v2_service" "sightline" {
  template {
    scaling { min_instance_count = 1; max_instance_count = 10 }
    containers {
      resources { limits = { cpu = "2"; memory = "1Gi" } }
      cpu_throttling = false
    }
    session_affinity = true
  }
}
```

### Session Management

- **MUST enable** `context_window_compression` (2 min video cap without it)
- **Session resumption**: reconnect within 2 hours with saved handle
- Server sends `GoAway` before termination

---

## COMPETITION RESEARCH

### Judging (Weight)

| Criterion | Weight |
|-----------|--------|
| Innovation & Multimodal UX | **40%** |
| Technical Implementation | **30%** |
| Demo & Presentation | **30%** |

### Mandatory

- Gemini model + GenAI SDK/ADK + Google Cloud + 1 additional GCP service

### Prizes

- Grand Prize: $25,000 + $3,000 GCP
- Best Live Agent: $10,000 + $1,000 GCP
- SightLine targets both

### Previous Winner

- "Live Assistant for Blind People" (2024) -- SightLine MUST differentiate with **LOD + Context Awareness**

### Terraform Quickstart

Key resources: `google_cloud_run_v2_service`, `google_firestore_database`, `google_secret_manager_secret`, `google_artifact_registry_repository`

---

## COST SUMMARY

### Per-Session (10 min)

| Component | Model | Tokens | Cost |
|-----------|-------|--------|------|
| Audio input (Live API) | 2.5 Flash native audio | 15,000 | $0.045 |
| Audio output (Live API) | 2.5 Flash native audio | 7,500 | $0.090 |
| Video input (Live API, 1fps) | 2.5 Flash native audio | 154,800 | $0.464 |
| Sub-agent calls | 3 Flash (FREE) | ~10,000 | **$0.00** |
| **Total** | | **~187K** | **~$0.60** |

*Note: Live API native audio pricing ($3.00/1M audio in, $12.00/1M audio out) is higher than standard API*
Monthly (2hr/day active user): ~$7.20 (Live API) + $0.00 (sub-agents)

---

## KEY DECISIONS

| Decision | Choice | Rationale |
|----------|--------|-----------|
| OCR | Gemini 3 Flash Native (FREE) | Lower latency, sufficient accuracy, zero cost |
| Gym Equipment | Gemini 3.1 Pro / 3 Flash Vision | General understanding suffices |
| Distance | Gemini Spatial + clock-face | No extra API, cross-platform |
| Barcode | ML Kit + Gemini fallback | Speed + reliability |
| Currency | Gemini Vision | Already in pipeline |
| TTS | Gemini 2.5 Flash Native Audio (Live API) | Lowest latency; Gemini 3 has no Live API yet |
| Session | Compression + Resumption | Unlimited sessions |

---

## Sources

- [OCR Arena Benchmarks](https://www.ocrarena.ai/)
- [Cloud Vision Pricing](https://cloud.google.com/vision/pricing)
- [Gemini TTS](https://ai.google.dev/gemini-api/docs/speech-generation)
- [Roboflow Gym Equipment](https://universe.roboflow.com/bangkit-academy-ognnb/gym-equipment-object-detection)
- [ML Kit Barcode](https://developers.google.com/ml-kit/vision/barcode-scanning)
- [Gemini Live Agent Challenge](https://algo-mania.com/en/blog/hackathons-coding/gemini-live-agent-challenge-create-immersive-ai-agents-with-google-gemini-live/)
- [2024 Winners](https://ai.google.dev/competition)
- [Cloud Run Optimization](https://cloud.google.com/blog/topics/developers-practitioners/3-ways-optimize-cloud-run-response-times)
