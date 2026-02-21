# SightLine: 跨文档对齐审查报告

> **Date**: 2026-02-21
> **Auditor**: Alignment review of all specification documents
> **Scope**: Final_Specification, Technical_Research, Voice_Interaction_UX_Research, 核心架构, 硬件形态, Subtasks_Roadmap, Context_Engine
> **Goal**: 保证实际 Demo 执行不出问题 — 消除文档间矛盾、对齐 Best Practice、简化冗余架构

---

## 🔴 Critical Issues (会导致 Demo 失败)

### Issue #1: 架构模式矛盾 — Server-to-Server vs Direct Connect

| 文档 | 说法 |
|------|------|
| **Final Spec §6.1** | ✅ "采用 ADK Server-to-Server (全代理) 模式" — 有 5 条论证 |
| **Final Spec §6.3** | ❌ "Hackathon (直连): Gets ephemeral token → Opens WebSocket directly to Gemini" |
| **Technical Research §6.2** | ❌ "WebSocket (direct to Gemini Live API)" |

**根因**：Final Spec §6.1 做出了 Server-to-Server 决策，但 §6.3 和 Technical Research 仍保留了早期的直连方案。

**决议**：**Server-to-Server 是唯一正确架构。** 理由：
1. ADK `run_live()` + `LiveRequestQueue` 自动处理 Function Calling、agent transfer、session state
2. Sub-Agent (Vision/OCR/FaceID) 全部跑在后端
3. API Key 留在 Secret Manager，不暴露给前端
4. ADK 官方有现成的 `bidi-demo` 和 `realtime-conversational-agent` 模板可直接使用
5. 延迟仅增加 ~10ms（Cloud Run 同区域）

**修改要求**：
- [x] Final Spec §6.3: 删除 "Hackathon (直连)" 段落，统一为 Server-to-Server — ✅ 已重写为 ADK bidi-demo 模式
- [x] Technical Research §6.2: 更新 Frontend 架构图，WebSocket 目标改为 Cloud Run — ✅ Executive Summary + §6.2 + §6.3 均已修正
- [x] 删除 "ephemeral token" 概念 — ✅ Final Spec 和 Technical Research 主要章节已移除

---

### Issue #2: 手势映射定义冲突

| 手势 | Final Spec §7.2 | Voice UX Research §2.2 |
|------|------------|-----|
| **单击** | 暂停/恢复 | 静音/取消静音麦克风 |
| **双击** | 重复上一句 | 强制打断 Agent 说话 |
| **三击** | *(无定义)* | 重复上一句 |
| **长按** | 紧急暂停 | 紧急暂停 ✅ |
| **上/下滑** | *(无定义)* | LOD 升降 |
| **摇一摇** | *(无定义)* | SOS 紧急模式 |

**决议**：采用 **Voice UX Research 的方案**（更完善、6 种手势覆盖所有场景）。

**具体理由**：
- 单击 = 静音更合理（盲人用户最频繁的需求是快速静音，而非暂停/恢复整个 session）
- 双击 = 打断 Agent 比"重复"更紧急、优先级更高
- 上/下滑 = LOD 控制是关键差异化功能，必须有快捷手势

**修改要求**：
- [x] Final Spec §7.2: 更新手势映射表为 Voice UX Research 的版本 — ✅ 7 种手势 + 触觉反馈表
- [x] Final Spec §7.2: 添加触觉反馈 (haptic) 定义 — ✅ 包含 vibrate + 音效降级

---

### Issue #3: RunConfig API 与 ADK SDK 不匹配

**Final Spec §6.3 使用的 API 形状**：
```python
# WRONG — 这不是 ADK 的 API
run_config = RunConfig(
    proactive_audio=ProactiveAudio(enabled=True),
    affective_dialog=AffectiveDialog(enabled=True),
    session_resumption_config=SessionResumptionConfig(handle=...),
    context_window_compression_config=ContextWindowCompressionConfig(sliding_window=SlidingWindow()),
)
```

**ADK 实际 API (来自 context7 官方文档)**：
```python
# CORRECT — 这是 ADK SDK 的真实 API
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import types

run_config = RunConfig(
    streaming_mode=StreamingMode.BIDI,
    response_modalities=["AUDIO"],
    proactivity=types.ProactivityConfig(proactive_audio=True),
    enable_affective_dialog=True,
    session_resumption=types.SessionResumptionConfig(),
    context_window_compression=types.ContextWindowCompressionConfig(
        trigger_tokens=100000,
        sliding_window=types.SlidingWindow(target_tokens=80000),
    ),
    realtime_input_config=types.RealtimeInputConfig(
        automatic_activity_detection=types.AutomaticActivityDetection(
            start_of_speech_sensitivity="MEDIUM",
            end_of_speech_sensitivity="MEDIUM",
        )
    ),
)
```

**关键差异**：
1. `streaming_mode=StreamingMode.BIDI` — 必须显式指定
2. `proactivity=types.ProactivityConfig(...)` 而非 `proactive_audio=ProactiveAudio(...)`
3. `enable_affective_dialog=True`（顶层 bool）而非 `affective_dialog=AffectiveDialog(...)`
4. `context_window_compression` 需要 `trigger_tokens` 和 `target_tokens` 参数
5. `session_resumption`（不是 `session_resumption_config`）

**修改要求**：
- [x] Final Spec §6.3: 更新所有 `RunConfig` 代码示例为 ADK 正确 API — ✅ 完整重写，包含 StreamingMode.BIDI, ProactivityConfig, LiveRequestQueue
- [x] Technical Research §1.1: 同步更新 — ✅ §1.1 已是正确 API（proactivity, enable_affective_dialog, trigger_tokens）

---

## 🟡 Medium Issues (不阻塞 Demo 但影响质量)

### Issue #4: VAD 配置缺失/不一致

| 文档 | VAD 配置 |
|------|---------|
| Final Spec §6.1 拓扑图 | 仅提到 "MEDIUM sensitivity" |
| Technical Research §1.1 | 有完整配置但与 ADK API 不完全匹配 |
| Voice UX Research §1.2 | 引入 LOD-Adaptive VAD 参数，但仅在该文档中 |
| Context Engine Guide | 无 VAD 相关内容 |

**决议**：
1. LOD-Adaptive VAD 纳入 Final Spec（作为 LOD Engine 的一部分）
2. 使用 ADK RunConfig 的正确 API 格式

**修改要求**：
- [x] Final Spec §6.3 RunConfig: LOD-Adaptive VAD 参数已写入 — ✅ silence_duration_ms=1000 + 注释 "LOD Engine 会动态调整此值"
- [x] Final Spec §2.4: 新增 "LOD-Adaptive 描述个性化" 章节 — ✅ 包含 vision_status 驱动的描述策略 + 先天盲人无颜色描述 (Describe Now, ASSETS 2024)

---

### Issue #5: 语音名称选择

**决议**：使用 **Aoede**。根据 [Gemini 官方文档](https://ai.google.dev/gemini-api/docs/live#voice-and-language-selection)，Aoede 的音色更温暖、更适合陪伴场景。Zephyr 偏活泼/年轻。

但最终选择应该实际测试后决定。在 Roadmap 中添加"语音 A/B 测试"任务。

**修改要求**：
- [x] Subtasks Roadmap: Phase 3 添加 "Voice A/B test (Aoede vs Zephyr vs Puck)" 任务 — ✅ Task 3.13

---

### Issue #6: Embedding 维度描述不统一

| 文档 | 描述 |
|------|------|
| Technical Research §4.3 | "3072 dims (truncated to 2048 for Firestore)" |
| Final Spec §8.1 | "gemini-embedding-001 (GA, 3072 dims)" (未提 truncation) |
| Context Engine §4.2 | "gemini-embedding-001, 3072 dims → truncate to 2048" |
| Subtasks Roadmap §5 | "gemini-embedding-001 (2048 dims for Firestore)" |

**决议**：统一描述为 **"gemini-embedding-001 (native 3072d, truncated to 2048d for Firestore max)"**

**修改要求**：
- [x] Final Spec §8.1: 添加 truncation 说明 — ✅ "native 3072d → truncated to 2048d for Firestore max"
- [x] Subtasks Roadmap §5: 修正为 "3072→2048" — ✅ "native 3072d → 2048d for Firestore"

---

### Issue #7: Context Window Compression 缺少显式参数

**当前所有文档**：`SlidingWindow()` — 无显式参数

**ADK 官方文档 Best Practice**：
```python
context_window_compression=types.ContextWindowCompressionConfig(
    trigger_tokens=100000,
    sliding_window=types.SlidingWindow(target_tokens=80000),
)
```

**影响**：没有显式设置 `trigger_tokens` 和 `target_tokens` 时，使用 API 默认值。显式设置能更精确控制何时开始压缩。

**修改要求**：
- [x] Final Spec §6.3: 添加 `trigger_tokens=100000, target_tokens=80000` — ✅
- [x] Technical Research §1.1: 同步更新 — ✅

---

## 🟢 Minor Issues (低优先级)

### Issue #9: 过时文档标注

**Subtasks Roadmap §0**：
> "核心架构 / 硬件形态 = 被 Final Specification 吸收的两份早期深度设计文档 (**已过时，以 Final Spec 为准**)"

这很好——已经标注了。

- [x] 在两个文件开头添加醒目的 "DEPRECATED" 标注 — ✅ 已添加 `⚠️ DEPRECATED` banner

---

### Issue #10: 未引用 Voice Interaction UX Research

`Subtasks Roadmap §0` 的 Documents Relationship Map 没有包含新创建的 `SightLine_Voice_Interaction_UX_Research.md`。

**修改要求**：
- [x] Subtasks Roadmap §0: 添加 Voice UX Research 到文档关系图 — ✅
- [x] Subtasks Roadmap: 添加 Voice Interaction 相关子任务 — ✅ Task 2.13-2.15

---

## Summary: 对齐优先级

| Priority | Issue | 改什么 | 状态 |
|----------|-------|--------|------|
| 🔴 P0 | #1 架构模式矛盾 | Final Spec §6.3, Tech Research §6.2, Executive Summary | ✅ 已修复 |
| 🔴 P0 | #3 RunConfig API | Final Spec §6.3, Tech Research §1.1 | ✅ 已修复 |
| 🟡 P1 | #2 手势映射 | Final Spec §7.2 | ✅ 已修复 |
| 🟡 P1 | #4 VAD LOD-Adaptive | Final Spec §2.4 + §6.3 RunConfig | ✅ 已修复 |
| 🟡 P2 | #5 语音名称 | Spec + Subtasks Roadmap 3.13 | ✅ 已修复 |
| 🟡 P2 | #7 Compression 参数 | Final Spec §6, Tech Research §1.1 | ✅ 已修复 |
| 🟢 P3 | #6 Embedding 描述 | Final Spec §8.1, Subtasks Roadmap | ✅ 已修复 |
| 🟢 P3 | #9 过时文档标注 | 核心架构.md, 硬件形态.md | ✅ 已修复 |
| 🟢 P3 | #10 文档关系图 | Subtasks Roadmap §0 | ✅ 已修复 |

***所有 10 个 Issue 均已修复。***

---

## 第二轮审查 (2026-02-22) — 新增 4 个 Issue

### Issue #11: vision_status 枚举值不统一

| 文档 | 定义 |
|------|------|
| Final Spec §2.4 | `congenital_blind \| acquired_blind \| low_vision`（合并字段） |
| Context Engine §4.2 | `vision_status: totally_blind \| low_vision` + `blindness_onset: congenital \| acquired`（分离字段） |

**决议**：采用 **Context Engine 的分离设计**。`totally_blind + congenital` 和 `totally_blind + acquired` 的描述策略完全不同。

**修改记录**：
- [x] Final Spec §2.4: 更新枚举值和代码示例为分离字段 — ✅
- [x] Consolidated Doc §0.2: 追加矛盾 #8 裁定记录 — ✅

### Issue #12: Session Service 选型矛盾

| 文档 | 说法 |
|------|------|
| Final Spec §6.1 | `InMemorySessionService`（Hackathon 足够） |
| Memory Research §3.2 | `VertexAiSessionService` |

**决议**：开发初期 `InMemorySessionService`（零配置），Phase 2 切 `VertexAiSessionService`（持久化）。两者 API 兼容。

**修改记录**：
- [x] Final Spec §6.1 拓扑图: 标注渐进迁移路径 — ✅
- [x] Consolidated Doc §0.2: 追加矛盾 #9 裁定记录 — ✅

### Issue #13: Context Engine §4.1 推荐方案与 Memory Research 矛盾

| 文档 | 推荐方案 |
|------|---------|
| Context Engine §4.1 | "在 Firestore 之上自建 Mem0 式的自动提取层" |
| Memory Research §3 | "Vertex AI Memory Bank（~30 行集成）" |

**决议**：Memory Bank 为首选。Context Engine §4 自建方案降级为 fallback 备选。

**修改记录**：
- [x] Context Engine §4.1: 更新推荐方案表述，标注为 fallback — ✅
- [x] Consolidated Doc §0.2: 追加矛盾 #10 裁定记录 — ✅

### Issue #14: RAG Engine 示例中使用 text-embedding-005

| 文档 | Embedding 模型 |
|------|---------------|
| Memory Research §4.2 | `text-embedding-005`（2 处） |
| 所有其他文档 | `gemini-embedding-001` |

**决议**：统一 `gemini-embedding-001`。

**修改记录**：
- [x] Memory Research §4.2 + §5.2: 代码示例中的模型名已更正 — ✅
- [x] Consolidated Doc §0.2: 追加矛盾 #11 裁定记录 — ✅

### 第二轮 Summary

| Priority | Issue | 改什么 | 状态 |
|----------|-------|--------|------|
| 🟡 P1 | #11 vision_status 枚举 | Final Spec §2.4 | ✅ 已修复 |
| 🟢 P3 | #12 Session Service | Final Spec §6.1 | ✅ 已修复 |
| 🟡 P1 | #13 Memory 方案路径 | Context Engine §4.1 | ✅ 已修复 |
| 🟢 P3 | #14 Embedding 模型名 | Memory Research §4.2, §5.2 | ✅ 已修复 |

***14 个 Issue 全部修复。***

---

## 推荐的 Best Practice 改进

### 从 Google ADK 学到的

1. **使用 ADK `bidi-demo` 模板**：
   - 来源: `google/adk-samples/bidi-demo`
   - 已有: FastAPI WebSocket + upstream/downstream task 分离 + session management
   - 节省估计 2-3 天的 WebSocket 基础设施代码开发

2. **RunConfig 是一等对象**：
   - ADK 将所有 Live API 配置统一在 `RunConfig` 中
   - 不需要手动构建 `LiveConnectConfig` — ADK 的 `Runner.run_live()` 会处理

3. **Activity Signals 用于手势**：
   - `send_activity_start()` / `send_activity_end()` 可用于实现"双击打断 Agent"
   - 客户端发 `{type: "activity_start"}` + 立即 `{type: "activity_end"}` = 触发 barge-in

### 从开源项目学到的

1. **Pipecat 的 Krisp VIVA 集成**（生产级噪声消除）：
   - 放在 Telemetry 或 Audio pipeline 之前
   - 不在 Hackathon 实现，但在架构图和 Pitch 中展示为 "Production Roadmap"

2. **Daily 的 `smart-turn`**（智能 turn-taking 模型）：
   - 开源，比简单的 silence-duration 更智能
   - 可作为 Gemini AAD 的增强/替代

3. **ADK State Prefixes**：
   - `user:` prefix 可以替代部分 Firestore 持久化需求（简化 Hackathon 实现）
   - `temp:` prefix 用于 turn-level 暂存

---

*本文档应与所有 Specification 文档配合使用。后续开发中发现新的不一致时，追加到此文档中。*
