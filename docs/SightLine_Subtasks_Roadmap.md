# SightLine: Subtasks & Development Roadmap

> **Date**: 2026-02-21
> **Deadline**: 2026-03-16 5:00 PM PDT (23 days remaining)
> **Based on**: Final Specification + Technical Research Report

---

## 0. Documents Relationship Map

```
SightLine 硬件形态与极简部署策略.md ──┐
  (SEP 协议、硬件解耦、部署策略)       │
                                      ├──▶ SightLine_Final_Specification.md (定稿 v1.0)
SightLine 核心架构_ Agent编排与上下文建模.md ──┤    (产品定义 + 架构设计 + 竞赛策略)
  (Agent 编排、Context 三层融合、记忆建模)      │              │
                                              │              │ 互相补充
raw_research/ (竞品分析、竞赛策略、市场调研) ──┘              │
                                                             ▼
                                            SightLine_Technical_Research.md (最新)
                                              (技术选型 + 可行性验证 + 代码示例)
                                              (7 个研究 Agent 的综合产出)
                                                             │
                                              ┌──────────────┤
                                              ▼              ▼
                      SightLine_Voice_Interaction_UX_Research.md    SightLine_Alignment_Review.md    SightLine_Best_Practices_Research.md
                        (VAD 调优 + 手势交互 + 嘈杂环境)              (跨文档对齐审查)                (DeepMind/闭源/顶会最佳实践)
```

**一句话关系**:
- **Final Specification** = 产品和架构的"**做什么**" (What & Why)
- **Technical Research** = 具体技术的"**怎么做**" (How & With What)
- **Voice UX Research** = 语音交互体验的"**怎么做对**" (VAD、手势、降噪)
- **Alignment Review** = 跨文档一致性审查和修正记录
- **Best Practices Research** = 最新调研: ContextAgent (NeurIPS 2025), Describe Now (ASSETS 2024), Gemini Best Practices
- **核心架构** / **硬件形态** = 被 Final Specification 吸收的早期文档 (**已过时，已标注 DEPRECATED**)

---

## 1. Subtask Breakdown

### Phase 0: Immediate Actions (Day 0 — 2/21)

| ID | Subtask | Priority | Output | Notes |
|----|---------|----------|--------|-------|
| 0.1 | Register GDG membership | P0 | GDG profile | +0.2 bonus, takes 5 min |
| 0.2 | Apply for Gemini API Tier 1 | P0 | API key with 50 concurrent sessions | Free tier only allows 3 concurrent Live sessions |
| 0.3 | Enable GCP billing + create project | P0 | GCP project ID | Firestore, Cloud Run, Maps API all need billing enabled |

---

### Phase 1: Core Skeleton (Week 1 — 2/22 ~ 2/28)

**Goal**: End-to-end audio/video loop running on GCP. User speaks into phone, Gemini responds.

| ID | Subtask | Priority | Depends On | Tech Ref | Output |
|----|---------|----------|------------|----------|--------|
| 1.1 | Init project repo + ADK boilerplate | P0 | 0.3 | Tech §2.2 | `sightline/` project structure |
| 1.2 | Gemini Live API WebSocket: connect + send/receive audio | P0 | 1.1 | Tech §1.1-1.4 | Working bidi audio stream |
| 1.3 | Add video input (JPEG 768x768 @ 1 FPS) to Live API | P0 | 1.2 | Tech §1.2 | Audio + video flowing |
| 1.4 | Enable `contextWindowCompression` + `sessionResumption` | P0 | 1.2 | Tech §1.1 | Sessions > 2 min |
| 1.5 | Orchestrator Agent (ADK): basic intent routing shell | P0 | 1.1 | Tech §2.2-2.3 | Root agent dispatches to sub-agents |
| 1.6 | LOD Engine v0: 3-level state machine (hardcoded thresholds) | P0 | 1.5 | Spec §2.1-2.2 | LOD 1/2/3 switching works |
| 1.7 | Frontend: Vite + React PWA scaffold (基于 ADK bidi-demo 模板) | P0 | — | Tech §6.1-6.2 | `getUserMedia` captures camera + mic, WebSocket to Cloud Run |
| 1.8 | Frontend: WebSocket to Cloud Run (server-to-server, NOT direct) | P0 | 1.2, 1.7 | Tech §6.3 | Browser talks to backend, backend talks to Gemini |
| 1.9 | Frontend: AudioWorklet (PCM 16kHz) + streaming playback (24kHz) | P0 | 1.8 | Tech §6.2 | Full audio loop in browser |
| 1.10 | Deploy to Cloud Run (one command via ADK) | P0 | 1.5 | Tech §2.5 | Live on GCP, verified end-to-end |
| 1.11 | Firestore: init database + user profile schema | P0 | 0.3 | Tech §4.2-4.3 | DB ready for all agents |

**Week 1 Milestone**: Open phone browser → see camera → speak → hear Gemini respond with video context. Deployed on Cloud Run.

---

### Phase 2: Core Agents (Week 2 — 3/1 ~ 3/7)

**Goal**: All major agents functional. LOD dynamically switches. Proactive Audio works.

| ID | Subtask | Priority | Depends On | Tech Ref | Output |
|----|---------|----------|------------|----------|--------|
| 2.1 | Vision Sub-Agent: scene description (Gemini 3.1 Pro) | P0 | 1.5 | Tech §2.2 | "You're in a café, 3 tables, barista on the left" |
| 2.2 | OCR Sub-Agent: text reading (Gemini 3 Flash, FREE) | P1 | 1.5 | Tech §7.1 | Reads menus, labels, signs |
| 2.3 | Enable Proactive Audio (`proactive_audio=True`) | P1 | 1.2 | Tech §1.1 | AI speaks unprompted at LOD 2/3 |
| 2.4 | Enable Affective Dialog (`enable_affective_dialog=True`) | P1 | 1.2 | Tech §1.1 | Tone adapts to user emotion |
| 2.5 | Navigation tool: `navigate_location()` via Google Maps API | P1 | 1.5 | Tech §5.1-5.3 | Clock-position directions |
| 2.6 | Navigation: compass heading via DeviceOrientationEvent | P1 | 1.7, 2.5 | Tech §5.2 | "Starbucks at 2 o'clock" |
| 2.7 | Google Search grounding tool (`google_search()`) | P1 | 1.5 | Tech §4.6 | Fact-check brands, products |
| 2.8 | Context Fusion algorithm: wire telemetry → LOD decisions | P0 | 1.6 | Spec §2.2, §3 | Heart rate + step cadence drive LOD |
| 2.9 | Face ID Sub-Agent: InsightFace setup + Firestore embeddings | P2 | 1.11 | Tech §3.1-3.4 | Register + match faces |
| 2.10 | Face ID: Non-blocking function call (`NON_BLOCKING` + `WHEN_IDLE`) | P2 | 2.9 | Tech §1.3 | Face result woven into speech |
| 2.11 | Face ID: registration flow (web UI for sighted helper) | P2 | 2.9 | Spec §4.2 | 3-5 photos per person |
| 2.12 | System prompt engineering: personality + LOD-aware instructions | P0 | 1.5 | Spec §7.1, §7.3 | Warm, calm friend persona |
| 2.13 | Gesture handler: tap/double-tap/swipe/shake → WebSocket signals | P1 | 1.7 | Voice UX §2.2 | 6-gesture fullscreen input |
| 2.14 | Haptic feedback: navigator.vibrate() per gesture type | P1 | 2.13 | Voice UX §2.2 | Tactile confirmation |
| 2.15 | LOD-Adaptive VAD: dynamically adjust silence_duration_ms per LOD | P1 | 1.6 | Voice UX §1.2 | LOD 1→400ms, LOD 3→1300ms |
| 2.16 | User profile: add `vision_status`, `color_description`, `preferred_tts_speed` to Firestore schema | P1 | 1.11 | Best Practices §3.1 | Congenital blind personalization |
| 2.17 | System Prompt restructure: persona → rules → guardrails (Google recommended order) | P0 | 2.12 | Best Practices §1.2 | Vertex AI Best Practices alignment |
| 2.18 | Audio transcription: add `input/output_audio_transcription` to RunConfig | P0 | 1.5 | Best Practices §1.2 | Frontend captions + LOD intent analysis |
| 2.19 | LOD Prompt personalization: congenital blind → no color descriptions, use tactile/spatial | P1 | 2.16, 2.17 | Best Practices §3.1 | "Describe Now" ASSETS 2024 findings |
| 2.20 | Proactive Audio strategy: multi-dimensional context fusion priority rules | P1 | 2.8, 2.12 | Best Practices §3.1 | ContextAgent NeurIPS 2025 pattern |

**Week 2 Milestone**: 4 demo scenarios partially functional. LOD transitions based on simulated telemetry.

---

### Phase 3: Polish & Integration (Week 3 — 3/8 ~ 3/12)

**Goal**: Demo-ready product with Developer Console. All scenarios rehearsed.

| ID | Subtask | Priority | Depends On | Tech Ref | Output |
|----|---------|----------|------------|----------|--------|
| 3.1 | Memory Sub-Agent: store + retrieve with Firestore vector search | P3 | 1.11 | Tech §4.3-4.4 | Cross-session memory |
| 3.2 | Memory: `gemini-embedding-001` integration (2048 dims) | P3 | 3.1 | Tech §4.3 | Semantic memory retrieval |
| 3.3 | Narrative Snapshot: save reading position on LOD downgrade | P3 | 1.6, 2.2 | Spec §2.3 | Interrupt + resume reading |
| 3.4 | Developer Console: telemetry simulator (heart rate, step cadence, head turn sliders) | P2 | 1.7 | Spec §3.2 | Web UI with sliders → JSON → cloud |
| 3.5 | Minimal UI: single button + LOD color transitions | P1 | 1.7 | Spec §7.2 | Deep blue / warm orange / soft white |
| 3.6 | Latency optimization: streaming playback + pre-emptive feedback | P1 | 1.9 | Tech §7.4 | "Let me look..." while processing |
| 3.7 | Latency optimization: client-side frame change detection | P1 | 1.3 | Tech §7.4 | Skip duplicate frames |
| 3.8 | Cloud Run: warm instance (`min_instance_count=1`) | P1 | 1.10 | Tech §7.4 | No cold start in demo |
| 3.9 | End-to-end test: all 4 demo scenarios | P0 | 2.* | — | Each scenario verified working |
| 3.10 | Error handling: camera blocked, network drop, API errors | P1 | 1.* | Spec §12 | Graceful degradation |
| 3.11 | iOS fallback: detect standalone PWA → redirect to Safari | P1 | 1.7 | Tech §6.4 | Camera works on iOS |
| 3.12 | Terraform scripts for infra-as-code | P3 | 1.10 | — | +0.2 bonus |
| 3.13 | Voice A/B test: Aoede vs Zephyr vs Puck | P2 | 1.5 | Best Practices §2.1 | Pick best voice for BLV users |

**Week 3 Milestone**: All 4 demo scenarios rehearsed end-to-end. Developer Console shows live sensor data driving AI behavior.

---

### Phase 4: Demo & Submission (Week 4 — 3/13 ~ 3/16)

**Goal**: Ship everything.

| ID | Subtask | Priority | Date | Output |
|----|---------|----------|------|--------|
| 4.1 | Record demo video (4 min, scripted) | P0 | 3/13 | MP4 following Spec §9 script |
| 4.2 | Create architecture diagram | P0 | 3/14 | PNG for Devpost |
| 4.3 | Write Devpost project description | P0 | 3/14 | Summary, features, tech stack |
| 4.4 | Write README with spin-up instructions | P0 | 3/14 | `README.md` in repo |
| 4.5 | GCP Console deployment screenshot/screencast | P0 | 3/14 | Proof of cloud deployment |
| 4.6 | Publish technical blog (Medium + Dev.to) | P3 | 3/15 | +0.6 bonus |
| 4.7 | Final check: all submission items complete | P0 | 3/15 | Spec §14 checklist |
| 4.8 | Submit to Devpost | P0 | 3/15 | Submission confirmed |
| 4.9 | Buffer day | — | 3/16 | Emergency fixes only |

---

## 2. Dependency Graph (Critical Path)

```
0.3 (GCP project)
 ├── 1.1 (ADK init) ── 1.5 (Orchestrator) ── 1.6 (LOD Engine)
 │                          │                      │
 │                          ├── 2.1 (Vision)       ├── 2.8 (Context Fusion)
 │                          ├── 2.2 (OCR)          │
 │                          ├── 2.5 (Navigation)   └── 3.3 (Narrative Snapshot)
 │                          ├── 2.7 (Grounding)
 │                          └── 2.12 (Prompt eng.)
 │
 ├── 1.2 (Live API WS) ── 1.3 (Video) ── 1.4 (Compression)
 │        │
 │        ├── 2.3 (Proactive Audio)
 │        └── 2.4 (Affective Dialog)
 │
 ├── 1.11 (Firestore) ── 2.9 (Face ID) ── 2.10, 2.11
 │                    └── 3.1 (Memory) ── 3.2 (Embedding)
 │
 └── 1.10 (Deploy) ── 3.8 (Warm instance) ── 3.12 (Terraform)

1.7 (Frontend) ── 1.8 (WS connection) ── 1.9 (Audio loop)
                                              │
                       ├── 3.5 (UI polish)    └── 3.6 (Latency opt)
                       ├── 3.4 (Dev Console)
                       └── 3.11 (iOS fallback)

ALL Week 1-3 tasks ── 3.9 (E2E test) ── 4.1 (Demo video) ── 4.8 (Submit)
```

---

## 3. Visual Roadmap

```
        2/21  2/22 ──────── 2/28  3/1 ──────── 3/7  3/8 ──────── 3/12  3/13 ──── 3/16
         │     │   WEEK 1    │     │   WEEK 2    │    │   WEEK 3    │     │ WEEK 4  │
         │     │             │     │             │    │             │     │         │
Phase 0  ■     │             │     │             │    │             │     │         │
GDG+API  │     │             │     │             │    │             │     │         │
         │     │             │     │             │    │             │     │         │
         │     ├─ Live API ──┤     │             │    │             │     │         │
         │     ├─ ADK+Orch ──┤     │             │    │             │     │         │
         │     ├─ LOD v0 ────┤     │             │    │             │     │         │
         │     ├─ Frontend ──┤     │             │    │             │     │         │
         │     ├─ Deploy ────┤     │             │    │             │     │         │
         │     ├─ Firestore ─┤     │             │    │             │     │         │
         │     │             │     │             │    │             │     │         │
         │     │  MILESTONE  │     │             │    │             │     │         │
         │     │  E2E audio  │     │             │    │             │     │         │
         │     │  +video on  │     │             │    │             │     │         │
         │     │  Cloud Run  │     │             │    │             │     │         │
         │     │             │     │             │    │             │     │         │
         │     │             │     ├─ Vision ────┤    │             │     │         │
         │     │             │     ├─ OCR ───────┤    │             │     │         │
         │     │             │     ├─ Nav+Maps ──┤    │             │     │         │
         │     │             │     ├─ Proactive ─┤    │             │     │         │
         │     │             │     ├─ Affective ─┤    │             │     │         │
         │     │             │     ├─ Face ID ───┤    │             │     │         │
         │     │             │     ├─ Context ───┤    │             │     │         │
         │     │             │     ├─ Prompt ────┤    │             │     │         │
         │     │             │     │             │    │             │     │         │
         │     │             │     │  MILESTONE  │    │             │     │         │
         │     │             │     │  4 scenarios │    │             │     │         │
         │     │             │     │  partially   │    │             │     │         │
         │     │             │     │  working     │    │             │     │         │
         │     │             │     │             │    │             │     │         │
         │     │             │     │             │    ├─ Memory ────┤     │         │
         │     │             │     │             │    ├─ Narrative ─┤     │         │
         │     │             │     │             │    ├─ Dev Console┤     │         │
         │     │             │     │             │    ├─ UI polish ─┤     │         │
         │     │             │     │             │    ├─ Latency ───┤     │         │
         │     │             │     │             │    ├─ E2E test ──┤     │         │
         │     │             │     │             │    ├─ Terraform ─┤     │         │
         │     │             │     │             │    │             │     │         │
         │     │             │     │             │    │  MILESTONE  │     │         │
         │     │             │     │             │    │  Demo-ready │     │         │
         │     │             │     │             │    │             │     │         │
         │     │             │     │             │    │             │     ├─ Video  │
         │     │             │     │             │    │             │     ├─ Arch   │
         │     │             │     │             │    │             │     ├─ Blog   │
         │     │             │     │             │    │             │     ├─ Submit │
         │     │             │     │             │    │             │     │         │
```

---

## 4. Cut-Line Strategy (If Time Runs Out)

If behind schedule, cut from bottom up:

| Tier | What to Cut | Impact |
|------|-------------|--------|
| **Cut first** | 4.6 Blog (+0.6), 3.12 Terraform (+0.2) | Lose 0.8 bonus points |
| **Cut second** | 3.1-3.2 Memory Agent, 3.3 Narrative Snapshot | Lose "memory" wow factor, but core demo intact |
| **Cut third** | 2.9-2.11 Face ID Agent | Lose emotional highlight, but LOD + Vision still strong |
| **Cut fourth** | 3.4 Developer Console | Lose transparency demo, simulate verbally instead |
| **Never cut** | LOD Engine + Vision + Proactive Audio + Frontend + Deploy + Demo Video | Without these, no viable submission |

---

## 5. Key Technical Decisions (Quick Reference)

| Decision | Choice | Why |
|----------|--------|-----|
| Orchestrator model | Gemini 2.5 Flash native audio | Only option for Live API bidi-streaming |
| Sub-agent models | Gemini 3 Flash / 3.1 Pro | FREE (Flash) / best reasoning (Pro), via REST API |
| Embedding model | `gemini-embedding-001` (native 3072d → 2048d for Firestore) | GA, replaces deprecated `text-embedding-004` |
| Agent framework | Google ADK (Python) | Native bidi-streaming, one-command Cloud Run deploy |
| Face recognition | InsightFace (ONNX, buffalo_l) | 99.83% accuracy, ~150ms CPU, 512-dim embeddings |
| Database | Firestore (with native vector search) | One DB for profiles, faces, memory; no extra vector DB |
| Frontend | Vite + React PWA | SPA, fastest dev, zero-config PWA via `vite-plugin-pwa` |
| Media transport | WebSocket to Cloud Run (server-to-server, ADK bidi-demo pattern) | API key secured server-side; ADK handles Function Calling + agent transfer |
| API version | `v1alpha` | Required for Proactive Audio + Affective Dialog |

---

*This document consolidates the Final Specification and Technical Research into an actionable development plan. Refer to `SightLine_Final_Specification.md` for product details and `SightLine_Technical_Research.md` for implementation specifics.*
