# Gemini 3.x Model Migration Analysis for SightLine

> **Research Date**: 2026-02-21
> **Purpose**: Identify outdated models, update to latest versions, document API changes and optimization opportunities

---

## 1. Model Update Matrix

### CRITICAL: Live API Stays on Gemini 2.5 Flash

As of February 2026, **Gemini 3 models do NOT support the Live API**. The Live API with native audio is exclusively powered by Gemini 2.5 Flash. This means SightLine's Orchestrator (the core real-time streaming component) **must remain on 2.5 Flash**.

### Full Update Matrix

| Component | OLD Model | NEW Model | Rationale |
|-----------|-----------|-----------|-----------|
| **Orchestrator (Live API)** | `gemini-2.5-flash-native-audio-preview-12-2025` | **NO CHANGE** (same) | Gemini 3 has no Live API support |
| **Vision Sub-Agent** | `gemini-2.5-pro` | **`gemini-3.1-pro-preview`** | Better reasoning, 1M context, media_resolution control |
| **OCR Sub-Agent** | `gemini-2.5-flash` | **`gemini-3-flash-preview`** | FREE during preview, outperforms 2.5 Pro |
| **Navigation Sub-Agent** | `gemini-2.5-flash` | **`gemini-3-flash-preview`** | FREE, better tool calling |
| **Grounding Sub-Agent** | `gemini-2.5-flash` | **`gemini-3-flash-preview`** | FREE, Google Search grounding supported |
| **Memory Consolidation** | `gemini-2.5-flash` | **`gemini-3-flash-preview`** | FREE, better extraction |
| **Context Caching** | `gemini-2.5-flash` | **`gemini-3-flash-preview`** | Automatic caching in Gemini 3 |
| **Embeddings** | `models/text-embedding-004` | **`gemini-embedding-001`** | GA, 3072 dims, text-embedding-004 deprecated |

### Deprecated Models (Remove Immediately)

| Model | Status | Removal Date |
|-------|--------|-------------|
| `gemini-2.0-flash-live-001` | Shut down | Already removed (Dec 9, 2025) |
| `gemini-live-2.5-flash-preview` | Shut down | Already removed (Dec 9, 2025) |
| `gemini-2.5-flash-native-audio-preview-09-2025` | Deprecated | **March 19, 2026** |
| `gemini-live-2.5-flash-preview-native-audio-09-2025` (Vertex) | Deprecated | **March 19, 2026** |
| `models/text-embedding-004` | Deprecated | Shutdown scheduled |
| `embedding-001` | Deprecated | Migrate immediately |

---

## 2. API Parameter Changes (Gemini 3 vs 2.5)

### 2.1 `thinking_level` Replaces `thinking_budget`

For Gemini 3 models (non-Live API), `thinking_budget` (integer) is replaced by `thinking_level` (enum string). They **cannot** be combined.

```python
# OLD (Gemini 2.5)
config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=2048)
)

# NEW (Gemini 3)
config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level="medium")
)
```

**Thinking levels:**
- `minimal` — Gemini 3 Flash only
- `low` — All Gemini 3 models
- `medium` — Gemini 3.1 Pro and Gemini 3 Flash
- `high` — All Gemini 3 models (default, dynamic)

**EXCEPTION**: Live API still uses `thinking_budget` (integer), not `thinking_level`.

### 2.2 New `media_resolution` Parameter

Controls token consumption per image/video frame:

```python
# For SightLine Vision Sub-Agent
config = types.GenerateContentConfig(
    media_resolution="high"  # 1120 tokens/frame for detailed analysis
)

# For quick scans
config = types.GenerateContentConfig(
    media_resolution="media_resolution_low"  # 70 tokens/frame
)
```

| Level | Tokens/Frame | Recommended For |
|-------|-------------|----------------|
| `media_resolution_low` | 70 | Video scanning, general awareness |
| `medium` | 560 | PDF, standard images |
| `high` | 1120 | Detailed image analysis (default for images) |
| `ultra_high` | Highest | Maximum fidelity |

**SightLine optimization**: Use `low` for LOD 1 quick scans, `high` for LOD 3 detailed analysis.

### 2.3 Temperature Constraint

Google **strongly recommends** `temperature=1.0` (the default) for Gemini 3. Lower values may cause response looping or degraded reasoning.

### 2.4 Thought Signatures (New in Gemini 3)

Gemini 3 introduces encrypted thought signature tokens in responses. These are:
- **Required** for function calling (must return all signatures in exact order)
- **Required** for image generation
- **Recommended** for text/chat
- **Handled automatically** by official Python/Node/Java SDKs

No code changes needed if using the official Google GenAI SDK.

---

## 3. New Capabilities in Gemini 3

### 3.1 Gemini 3.1 Pro (`gemini-3.1-pro-preview`)

- Released **February 19, 2026** (very latest)
- Three levels of adjustable "Deep Think" reasoning
- 1M token context window / 64K output tokens
- **Medium thinking level** support (new — not in Gemini 3 Pro)
- Significantly better on SWE-bench and complex reasoning tasks
- Best choice for Vision Sub-Agent (deep scene analysis)

### 3.2 Gemini 3 Flash (`gemini-3-flash-preview`)

- **Pro-level intelligence at Flash speed and pricing**
- Outperforms Gemini 2.5 Pro while being 3x faster
- 1M token context window / 64K output tokens
- SWE-bench Verified score of **78%** for agentic coding
- `minimal` thinking level support (unique to Flash)
- **Computer Use built-in** (no separate model needed)
- Dynamic thinking by default
- **FREE for standard API use** (text/image/video) during preview

### 3.3 Gemini Embedding 001 (`gemini-embedding-001`)

- GA (stable, production-ready)
- **3072 dimensions** by default (vs 768 for text-embedding-004)
- Supports truncation via Matryoshka Representation Learning
- **#1 on MTEB Multilingual leaderboard**
- 100+ languages
- Pricing: $0.15/1M tokens (standard)

**Firestore compatibility note**: Firestore's max vector dimension is 2048. Options:
1. Use `output_dimensionality=768` parameter to truncate (matches old behavior)
2. Use `output_dimensionality=2048` for maximum quality within Firestore limits

---

## 4. Pricing Comparison

### Sub-Agent Costs (Gemini 3 vs 2.5)

| Model | Text Input/1M | Text Output/1M | Status |
|-------|--------------|----------------|--------|
| **gemini-3-flash-preview** | **FREE** | **FREE** | Preview (FREE for standard use) |
| gemini-2.5-flash | $0.30 | $2.50 | GA |
| **gemini-3.1-pro-preview** | $2.00 | $12.00 | Preview |
| gemini-2.5-pro | $1.25 | $10.00 | GA |

### Updated Cost Estimates (Per 10-Min Session)

| Component | Old Cost (2.5 Flash) | New Cost (3 Flash) | Savings |
|-----------|---------------------|-------------------|---------|
| Sub-agent text calls | ~$0.02 | **$0.00** | 100% |
| Vision deep analysis (10 calls) | ~$0.10 (2.5 Pro) | ~$0.16 (3.1 Pro) | -60% (but better quality) |
| Live API (stays 2.5 Flash) | ~$0.07 | ~$0.07 | 0% |
| Embeddings | ~$0.001 | ~$0.001 | ~same |
| **Total per session** | **~$0.19** | **~$0.23** | Focus on quality, not cost |

### Monthly (1 active user, 2hr/day)

| Component | Old Monthly | New Monthly |
|-----------|------------|-------------|
| Live API (2.5 Flash native audio) | ~$1.00 | ~$1.00 (no change) |
| Vision deep calls (3.1 Pro) | ~$3.00 | ~$4.00 (better quality) |
| Sub-agent calls (3 Flash) | ~$2.00 | **$0.00 (FREE)** |
| Maps APIs | $0 | $0 |
| Cloud Run | ~$17.00 | ~$17.00 |
| Firestore | $0 | $0 |
| **Total** | **~$23/month** | **~$22/month** |

### Hackathon Total

| Component | Old Estimate | New Estimate |
|-----------|-------------|-------------|
| Live API (development + demo) | ~$25 | ~$25 |
| Sub-agent calls (3 Flash) | ~$10 | **$0 (FREE)** |
| Vision deep calls (3.1 Pro) | ~$5 | ~$8 |
| Cloud Run | ~$20 | ~$20 |
| Maps APIs | ~$5 | ~$5 |
| **Total** | **~$65** | **~$58** |

---

## 5. Optimization Opportunities

### 5.1 LOD-Aware `media_resolution` (NEW)

Use the new `media_resolution` parameter to dynamically adjust token consumption based on LOD level:

```python
# In Vision Sub-Agent
def get_media_resolution_for_lod(lod_level: int) -> str:
    """Dynamic media resolution based on LOD level."""
    return {
        1: "media_resolution_low",   # 70 tokens/frame — quick hazard scan
        2: "medium",                  # 560 tokens/frame — standard exploration
        3: "high",                    # 1120 tokens/frame — detailed analysis
    }[lod_level]
```

This directly reduces token cost at LOD 1 by **94%** (70 vs 1120 tokens/frame) while maintaining full quality at LOD 3.

### 5.2 Gemini 3 Flash as Universal Sub-Agent

Since Gemini 3 Flash **outperforms Gemini 2.5 Pro** while being free, consider:
- Using 3 Flash for ALL sub-agents (OCR, Nav, Grounding, Memory)
- Reserve 3.1 Pro ONLY for deep vision analysis (LOD 3 detailed scenes)
- This gives "Pro-level" quality at zero cost for most operations

### 5.3 Improved Embedding Quality

`gemini-embedding-001` with 2048 dimensions (Firestore max) gives significantly better retrieval quality for:
- Long-term memory (user preferences, behavior patterns)
- Face embedding search (though InsightFace produces 512-dim, stored separately)

### 5.4 Thinking Level Control for Sub-Agents

```python
# OCR: minimal thinking for speed
ocr_config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level="minimal")
)

# Vision: medium thinking for balanced analysis
vision_config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level="medium")
)
```

### 5.5 Automatic Context Caching

Gemini 3 supports automatic (implicit) context caching — the system automatically caches repeated content across requests. This means:
- System prompts are cached automatically
- No need for explicit `caches.create()` for common patterns
- Up to 90% cost savings on cached content

---

## 6. Live API Updates (Still 2.5 Flash)

### New VAD Parameters

```python
config = types.LiveConnectConfig(
    realtime_input_config=types.RealtimeInputConfig(
        automatic_activity_detection=types.AutomaticActivityDetection(
            start_of_speech_sensitivity="START_SENSITIVITY_LOW",
            end_of_speech_sensitivity="END_SENSITIVITY_LOW",
            prefix_padding_ms=20,
            silence_duration_ms=100,
        ),
        # NEW: activity handling control
        activity_handling="START_OF_ACTIVITY_INTERRUPTS",  # or "NO_INTERRUPTION"
    ),
)
```

### Audio Transcription (New)

```python
config = types.LiveConnectConfig(
    input_audio_transcription=types.AudioTranscriptionConfig(),   # transcribe user
    output_audio_transcription=types.AudioTranscriptionConfig(),  # transcribe AI
)
```

Useful for SightLine:
- Log conversation history as text for memory consolidation
- Debug audio quality issues
- Enable text-based search of past conversations

### Context Compression Tuning

```python
config = types.LiveConnectConfig(
    context_window_compression=types.ContextWindowCompressionConfig(
        sliding_window=types.SlidingWindow(
            target_tokens=16384,  # tokens to retain after compression
        ),
        trigger_tokens=102400,   # when to trigger (default: 80% of 128K)
    ),
)
```

---

## 7. Migration Checklist

### Must Do (Before Hackathon Start)

- [ ] Update sub-agent model references: `gemini-2.5-flash` → `gemini-3-flash-preview`
- [ ] Update Vision Agent model: `gemini-2.5-pro` → `gemini-3.1-pro-preview`
- [ ] Update embedding model: `text-embedding-004` → `gemini-embedding-001`
- [ ] Add `output_dimensionality=2048` to embedding calls (Firestore limit)
- [ ] Replace `thinking_budget` with `thinking_level` in sub-agent configs
- [ ] Add `media_resolution` parameter to Vision Sub-Agent
- [ ] Keep `temperature=1.0` for all Gemini 3 calls
- [ ] Keep Live API on `gemini-2.5-flash-native-audio-preview-12-2025`

### Nice to Have

- [ ] LOD-aware media_resolution switching
- [ ] Audio transcription for conversation logging
- [ ] Context compression tuning with explicit target_tokens
- [ ] Thinking level per sub-agent (minimal for OCR, medium for Vision)

---

## Sources

- [Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3)
- [Gemini 3.1 Pro Announcement](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-1-pro/)
- [Gemini 3 Flash Announcement](https://blog.google/products/gemini/gemini-3-flash/)
- [Models Reference](https://ai.google.dev/gemini-api/docs/models)
- [Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Live API Guide](https://ai.google.dev/gemini-api/docs/live)
- [Live API Capabilities](https://ai.google.dev/gemini-api/docs/live-guide)
- [Gemini Embedding GA](https://developers.googleblog.com/gemini-embedding-available-gemini-api/)
- [Embeddings Docs](https://ai.google.dev/gemini-api/docs/embeddings)
- [Gemini 3 Flash (Vertex AI)](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-flash)
- [Gemini 3.1 Pro (Vertex AI)](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-1-pro)
