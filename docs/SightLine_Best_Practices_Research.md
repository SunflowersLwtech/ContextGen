# SightLine: 最佳实践调研报告

> **Date**: 2026-02-21
> **Scope**: Google DeepMind 开源、闭源产品思想、顶会论文
> **Focus**: LOD-Adaptive VAD、语音选择/个性化、Proactive AI Agent、盲人 UX

---

## 1. Google DeepMind & Google 开源

### 1.1 ContextAgent (NeurIPS 2025) ⭐ 最相关

**论文**: *ContextAgent: Context-Aware Proactive LLM Agents with Open-World Sensory Perceptions*
**作者**: Bufang Yang et al. (CUHK + Columbia)
**代码**: [github.com/openaiotlab/ContextAgent](https://github.com/openaiotlab/ContextAgent)
**会议**: NeurIPS 2025 Poster

**核心思想**：
- 与 SightLine 高度吻合 — 第一个"感知上下文→主动服务"的 LLM Agent
- 从可穿戴设备的多模态传感器（视频、音频、通知）中提取多维上下文
- 使用"Persona Context"（身份、偏好、历史行为）来预测何时需要主动帮助
- 分为三步：Sensory Perception → Context Extraction → Proactive Prediction → Tool Calling

**关键数据**：
| 指标 | 数值 |
|------|------|
| 评测基准 | ContextAgentBench (1,000 samples, 9 daily scenarios, 20 tools) |
| 主动预测准确率提升 | +8.5% vs baselines |
| 工具调用准确率提升 | +6.0% vs baselines |

**对 SightLine 的启发**：

| ContextAgent | SightLine 对应 |
|-------------|---------------|
| Sensory Perception (video, audio) | Camera + Mic 实时流 |
| Context Extraction | LOD Engine + Telemetry 融合 |
| Persona Context (历史偏好) | Memory Agent / User Profile |
| Proactive Prediction | Proactive Audio (Gemini 原生) |
| Tool Calling | Function Calling (face ID, maps, memory) |

**可用的设计模式**：
1. **Multi-dimensional Context Fusion** — 不要只看一个传感器，要融合多个上下文维度来决定行动
2. **Persona-aware Proactivity** — 主动行为应该考虑用户画像，而非千人一面
3. **Unobtrusive Assistance** — 主动帮助必须不打扰用户，论文强调 "assist users unobtrusively"

---

### 1.2 Gemini Live API 官方 Best Practices

**来源**: [Google Cloud Vertex AI 文档](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api/best-practices)

| 类别 | Best Practice | SightLine 影响 |
|------|-------------|---------------|
| **System Instruction 结构** | 按顺序：(1) Agent persona → (2) Conversational rules → (3) Guardrails | 我们的 System Prompt 需要按此结构重新组织 |
| **Audio 分块** | 20-40ms chunks，客户端不要缓冲超过 100ms | 前端 AudioWorklet 配置 |
| **打断处理** | 收到 `interrupted: true` 时必须**立即丢弃**客户端音频缓冲区 | 前端播放器实现 |
| **Context 管理** | 音频约 25 tokens/sec，长会话必须用 `ContextWindowCompressionConfig` | 已在 RunConfig 中实现 ✅ |
| **Tool 定义** | 明确说明工具的触发条件，模型在单一 function call 场景下表现最好 | Tool description 要精确 |
| **语言** | 添加 `"RESPOND IN {LANGUAGE}. YOU MUST RESPOND UNMISTAKABLY IN {LANGUAGE}."` | System prompt 需要加 |
| **Prompt 链** | 避免多页长 prompt，用 prompt chaining 替代 | 分 sub-agent 处理不同任务 |
| **启动对话** | 如果要 AI 先说话，include prompt 让它先问候用户 | Proactive Audio + greeting prompt |

**⚠️ 我们遗漏的关键配置**：

```python
# ADK bidi-demo 的 RunConfig 包含 audio transcription，我们没有！
run_config = RunConfig(
    streaming_mode=StreamingMode.BIDI,
    response_modalities=["AUDIO"],
    input_audio_transcription=types.AudioTranscriptionConfig(),   # 🆕 需要添加
    output_audio_transcription=types.AudioTranscriptionConfig(),  # 🆕 需要添加
    session_resumption=types.SessionResumptionConfig(),
)
```

`input_audio_transcription` 和 `output_audio_transcription` 使我们可以在传输音频的同时获取文字转录——对日志记录、LOD Engine 分析用户语句、和前端 UI transcript 显示都至关重要。

---

### 1.3 Gemini 2.5 Flash Native Audio (GA, Aug 2025)

**来源**: [Google Blog](https://blog.google/products-and-platforms/products/gemini/gemini-audio-model-updates/)

最新能力（已 GA）：
- **Proactive Audio**: "can distinguish between the speaker and background conversations, so it knows when to respond" — Gemini 能区分主说话人和背景对话
- **Affective Dialog**: "responds appropriately to a user's emotional expression and tone" — 感知情绪并调整语气
- **Thinking Model**: "A separate thinking model enables more complex queries" — 复杂推理走独立思考链
- **Live Speech Translation**: 30+ voices, 24+ languages
- **Speaker Distinction**: 能在嘈杂环境中识别主说话人

**对 SightLine 的意义**：
1. 不需要我们自己做 VAD 的噪声过滤 — Gemini 原生已经能区分主说话人和背景噪声
2. Affective Dialog 已 GA — 不再是实验性功能
3. Thinking model 可以处理 LOD 3 的复杂推理需求

---

### 1.4 WaveNet 遗产 (DeepMind)

Google Cloud TTS 的 Gemini-TTS voices 继承了 WaveNet 的神经波形合成技术：
- 30+ prebuilt voice options
- 支持 Chirp 3: HD Voices
- 单/多说话人模式
- 开发者可以通过 Cloud TTS API 或 Vertex AI API 获取

**对 SightLine**：当前 Live API 内置的 voice (Aoede, Zephyr, Puck 等) 已足够好，不需要外部 TTS。

---

## 2. 闭源产品的启发

### 2.1 Gemini Live App (Consumer Product)

| 功能 | 实现 | SightLine 可用 |
|------|------|---------------|
| 10+ voice options | 不同频率/音色满足不同听力特征 | 提供语音选择，适配用户听力差异 |
| 屏幕锁定后继续工作 | Hands-free，无需视觉交互 | 核心无障碍需求，已在设计中 |
| 对话历史保存 | 自动保存到 Google 账户 | Memory Agent 实现 |
| 速度控制 (0.75x) | 适配认知障碍/非母语用户 | 可作为 LOD 的补充维度 |
| 波形动画 | 显示 AI 说话状态 | 我们用呼吸灯替代（盲人友好） |

### 2.2 Newo.ai (AI Receptionist)

> "can identify the main speaker even in noisy settings, switch languages mid-conversation, and sound remarkably natural and emotionally expressive. Our agents can laugh, joke, and truly connect."

**启发**：
1. **嘈杂环境中的说话人识别**: Gemini 2.5 Flash 原生支持，无需额外处理
2. **情感表达**: "laugh, joke, connect" — Affective Dialog 在生产环境中表现良好
3. **语言切换**: Mid-conversation 语言切换已验证可行

### 2.3 SightCall (Visual Support)

> "real-time expert that knows what your best technicians know"

**启发**: 视觉 + 音频的多模态实时指导是生产就绪的。与 SightLine 的视觉描述场景直接相关。

### 2.4 Lumeris (Healthcare AI)

> "elevating the quality of every interaction... more responsive and personalized voice experience"

**启发**: 基于历史数据的个性化对话在医疗场景已验证。SightLine 的 Memory Agent 路线正确。

---

## 3. 顶会论文

### 3.1 "Describe Now" (ASSETS 2024 / PMC) ⭐ 盲人 UX 核心参考

**论文**: *Describe Now: User-Driven Audio Description for Blind and Low Vision Individuals*
**来源**: [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12413206/)

**关键发现**（直接影响 SightLine 设计）：

| # | 发现 | SightLine 影响 |
|---|------|---------------|
| 1 | BLV 用户强烈偏好**加速 TTS** (n=9 out of participants) | LOD 1 应该更快语速；考虑添加**语速控制手势** |
| 2 | 用户希望根据内容切换**男/女声** | 可在不同 Agent 之间使用不同 voice（如 Vision Agent 用不同声色） |
| 3 | **描述内容质量 >> TTS 音质** | "Quality of description itself is high, that's all that matters" — 优先优化 prompt |
| 4 | **先天盲人不理解颜色描述** | 用户画像应记录"视力状态"(先天/后天)，调整描述策略！ |
| 5 | "Start with general context, then add details" | 完美匹配 LOD 1→2→3 渐进式描述 |
| 6 | "Avoid over-describing" | LOD 1 的核心原则 |
| 7 | "Choose level of detail based on relevance" | LOD Engine 的核心逻辑 |
| 8 | Present tense + third-person + vivid verbs | System Prompt 写作规范 |
| 9 | AI 语音可能缺乏情感深度 | Affective Dialog 的价值——弥补 AI 语音的情感空白 |

**⚠️ 最关键发现 #4**：先天盲人对颜色描述感到困惑（"mention of colors made no sense to P16B as a congenitally blind person"）。

**行动项**：
- 用户注册时收集"视力状态"（先天盲、后天盲、低视力）
- LOD Prompt 中根据此标签动态调整："如果用户是先天盲人，用触觉/空间/声音类比替代颜色描述"
- 这是一个**差异化亮点**——竞品不会做到这个程度的个性化

---

### 3.2 VITA-1.5 (NeurIPS 2025 Spotlight)

*Towards GPT-4o Level Real-Time Vision and Speech Interaction*

验证了一个趋势：多模态实时交互是顶级研究热点。SightLine 的技术方向与学术前沿完全一致。

---

### 3.3 VAD Best Practices 综合 (多源)

综合 Deepgram、Picovoice、ShadeCoder 的 VAD 指南：

| 最佳实践 | 描述 | SightLine 实现 |
|---------|------|---------------|
| **Adaptive hold times** | 根据 SNR 动态调整 silence threshold | LOD-Adaptive VAD: LOD1=400ms, LOD3=1300ms |
| **Hybrid approach** | On-device quick detection + cloud re-evaluation | Gemini 的 AAD (Automatic Activity Detection) 就是这种模式 |
| **Error logging** | 记录 VAD 状态、时间戳、特征用于调试 | 后端 Cloud Logging |
| **Periodic re-evaluation** | "VAD behavior is context-dependent, benefits from continuous improvement" | 与 LOD Engine 的运行时动态调整一致 |
| **False accept vs false reject tradeoff** | 根据 UX 目标设定可接受阈值 | 盲人场景: prefer false accept (多说) over false reject (漏说) |
| **Audio preprocessing** | AGC + band-pass + noise suppression + echo cancellation | Gemini 2.5 Flash 原生处理 |

**Smart Turn-Taking** (from RealtimeVoiceChat / Vocalis):
- 不只看 silence duration，还看 acoustic features 来预测 turn boundary
- `TurnDetector.update_settings()` — 运行时可调的 turn 检测
- **Barge-in 技术指标**: VAD latency <100ms, stop latency <200ms, accuracy >95%

---

## 4. 综合最佳实践 → 具体行动项

### 4.1 RunConfig 需要补充的配置

```python
# 缺失项: audio transcription
input_audio_transcription=types.AudioTranscriptionConfig(),
output_audio_transcription=types.AudioTranscriptionConfig(),
```

这让我们可以同时获取音频+文字 transcript，用于：
- 前端显示实时字幕
- LOD Engine 分析用户意图（文字比音频更容易分析）
- 后端日志和 Memory Agent 存储

### 4.2 System Prompt 结构 (Google 官方推荐)

```
1. Agent Persona — 名字、角色、性格特征、语言偏好
2. Conversational Rules — 按优先级排列的对话规则
3. Guardrails — 不要做的事、边界条件
```

当前我们的 System Prompt 没有明确按此结构组织。需要重构。

### 4.3 用户画像增强 (受 Describe Now 论文启发)

在 Firestore 用户档案中添加：

```json
{
  "vision_status": "congenital_blind | acquired_blind | low_vision",
  "preferred_tts_speed": 1.0,          // 0.75 - 2.0
  "preferred_voice": "Aoede",
  "color_description": false,          // 先天盲人 = false
  "preferred_language": "en-US",
  "hearing_frequency_preference": null  // 未来: 低频/高频偏好
}
```

### 4.4 LOD Prompt 个性化 (受 Describe Now 启发)

**LOD 1 (先天盲人版本)**:
```
Describe using spatial, tactile, and auditory terms.
DO NOT mention colors.
Use size comparisons with familiar objects ("about the size of a backpack").
```

**LOD 1 (后天盲人/低视力版本)**:
```
Include colors briefly. Use spatial and visual terms they may remember.
```

### 4.5 Proactive Audio 策略 (受 ContextAgent 启发)

不要让 Proactive Audio "随便说话"。应该基于多维上下文融合来决定：

| 信号 | 权重 | 触发条件 |
|------|------|---------|
| 环境突变 (新人出现、车辆接近) | 高 | 立即说 |
| 用户提问后沉默 | 中 | 0.8s 后补充 |
| 环境平稳无变化 | 低 | 保持沉默 |
| 用户正在移动 (步频检测) | 中高 | 主动播报导航 |
| 用户处于静止/社交场景 | 低 | 等待被问 |

---

## 5. 需要落地的具体修改清单

| # | 修改 | 文件 | 优先级 | 来源 |
|---|------|------|--------|------|
| 1 | RunConfig 添加 `input/output_audio_transcription` | Final Spec §6.3 | P0 | ADK bidi-demo |
| 2 | System Prompt 按 Google 推荐结构重组 (persona→rules→guardrails) | Final Spec §7.1 | P1 | Vertex AI Best Practices |
| 3 | 用户画像增加 `vision_status`、`color_description`、`preferred_tts_speed` | Final Spec §3, Subtasks | P1 | Describe Now (ASSETS 2024) |
| 4 | LOD Prompt 添加先天盲人个性化 (无颜色描述) | Final Spec §2/§7 | P1 | Describe Now |
| 5 | Proactive Audio 策略文档化 (多维上下文融合) | Final Spec §7.3 | P2 | ContextAgent (NeurIPS 2025) |
| 6 | Subtasks Roadmap 添加 Voice A/B test 任务 | Subtasks Roadmap | P3 | Gemini Live App |
| 7 | 添加语言指令 `"RESPOND IN ENGLISH UNMISTAKABLY"` | System Prompt | P2 | Vertex AI Best Practices |
| 8 | 音频分块建议: 20-40ms | Technical Research §6.2 | P3 | Vertex AI Best Practices |

---

## 附录: 所有引用来源

### Google 开源 / 官方
1. [ADK Samples: bidi-demo](https://github.com/google/adk-samples/tree/main/python/agents/bidi-demo)
2. [ADK Samples: realtime-conversational-agent](https://github.com/google/adk-samples/tree/main/python/agents/realtime-conversational-agent)
3. [Vertex AI Live API Best Practices](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api/best-practices)
4. [Gemini Audio Model Updates (Aug 2025 Blog)](https://blog.google/products-and-platforms/products/gemini/gemini-audio-model-updates/)
5. [Gemini-TTS Documentation](https://docs.cloud.google.com/text-to-speech/docs/gemini-tts)
6. [Gemini Live API on Vertex AI (Blog)](https://cloud.google.com/blog/products/ai-machine-learning/gemini-live-api-available-on-vertex-ai)
7. [Build Voice Agent with Gemini & ADK](https://cloud.google.com/blog/products/ai-machine-learning/build-a-real-time-voice-agent-with-gemini-adk)
8. [WaveNet - DeepMind](https://deepmind.google/research/wavenet/)
9. [Google 2024 AI Year in Review](https://blog.google/innovation-and-ai/products/2024-ai-extraordinary-progress-advancement/)

### 闭源产品
10. [Newo.ai — AI Receptionists (Gemini Live API)](https://cloud.google.com/blog/products/ai-machine-learning/gemini-live-api-available-on-vertex-ai)
11. [SightCall — Visual Support with Gemini](https://cloud.google.com/blog/products/ai-machine-learning/gemini-live-api-available-on-vertex-ai)
12. [Lumeris — Healthcare AI Voice](https://cloud.google.com/blog/products/ai-machine-learning/gemini-live-api-available-on-vertex-ai)
13. [Gemini Live App Guide (AdwaitX)](https://www.adwaitx.com/gemini-live-audio-features-guide/)

### 学术论文
14. [ContextAgent: Context-Aware Proactive LLM Agents (NeurIPS 2025)](https://arxiv.org/abs/2505.14668) — [Code](https://github.com/openaiotlab/ContextAgent)
15. [Describe Now: User-Driven Audio Description for BLV (ASSETS 2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12413206/)
16. [VITA-1.5: Real-Time Vision and Speech Interaction (NeurIPS 2025 Spotlight)](https://neurips.cc/virtual/2025/events/spotlight-posters-2024)
17. [Google Patent: VAD Integration for ASR (US12198680)](https://patents.google.com/patent/US12198680/en)

### 开源项目 / 技术指南
18. [Vocalis: Real-time Voice Chat with Barge-in](https://github.com/Lex-au/Vocalis)
19. [RealtimeVoiceChat: Smart Turn-Taking](https://github.com/KoljaB/RealtimeVoiceChat)
20. [Rapida: Voice AI Orchestration Platform](https://github.com/rapidaai/voice-ai)
21. [Agent Voice Response (AVR)](https://github.com/agentvoiceresponse)
22. [VAD Complete Guide 2026 (Picovoice)](https://picovoice.ai/blog/complete-guide-voice-activity-detection-vad/)
23. [VAD Production Overview (Deepgram)](https://deepgram.com/learn/voice-activity-detection)
24. [Voice AI Guide: Building Real-Time Voice Agents](https://dev.to/programmerraja/2025-voice-ai-guide-how-to-make-your-own-real-time-voice-agent-part-3-3ocb)
25. [Top 5 Real-Time Speech-to-Speech APIs (GetStream)](https://getstream.io/blog/speech-apis/)

---

*本文档记录了截止 2026-02-21 的调研成果。所有技术参考均已验证为最新 stable 版本。*
