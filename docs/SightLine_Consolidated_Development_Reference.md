# SightLine 统一开发参考方案

> **生成日期**: 2026-02-22
> **基于**: 35 份文档的交叉验证与整合
> **定位**: 取代所有分散文档，作为开发阶段的唯一参考

---

## 0. 文档体系评估与裁定

### 0.1 现有文档分层

经过对全部 35 份文档的交叉验证，文档体系形成以下层级：

| 层级 | 文档 | 状态 | 用途 |
|------|------|------|------|
| **L0 权威规格** | `SightLine_Final_Specification.md` | **主参考** | 产品定义 + 架构设计 + 竞赛策略 |
| **L1 执行计划** | `SightLine_Subtasks_Roadmap.md` | **直接使用** | Phase 分解、依赖图、Cut-Line |
| **L1 深化设计** | `engine/Context_Engine_Implementation_Guide.md` | **补充参考** | LOD Engine、Context 建模、Vision Extraction 实现细节 |
| **L1 深化设计** | `engine/Memory_System_Research_and_Integration.md` | **补充参考** | Memory 方案调研历史（最终采用：自建 Firestore MemoryBankService） |
| **L2 审计日志** | `SightLine_Alignment_Review.md` | **问题回溯** | 10 个跨文档矛盾的修复记录 |
| **L2 技术调研** | `SightLine_Technical_Research.md` | **实现细节** | Roadmap 大量引用的技术实现参考 |
| **L2 技术调研** | `SightLine_Best_Practices_Research.md` | **实现细节** | ADK bidi-demo 模板、Activity Signals 等最佳实践 |
| **L2 UX 调研** | `SightLine_Voice_Interaction_UX_Research.md` | **UX 细节** | VAD 调优、手势映射、嘈杂环境防御 |
| **L3 原始研究** | `raw_research/infra/*` (8 份) | **按需查阅** | 各技术栈的详细 API 用法和基准测试 |
| **L3 原始研究** | `raw_research/engine/*` (3 份) | **按需查阅** | 学术背景、开源框架评估 |
| **L3 竞赛/竞品** | `raw_research/competition/*` + `raw_research/product/*` | **策略参考** | 竞赛要求、竞品分析、产品定位 |
| **DEPRECATED** | `SightLine 核心架构_ Agent编排与上下文建模.md` | **已废弃** | 内容已被 Final Spec 吸收 |
| **L1 前端设计** | `SightLine_iOS_Native_Infra_Design.md` | **前端参考** | iOS/watchOS 前端架构、数据管线、WebSocket 协议、Apple Watch 心率 |
| **DEPRECATED** | `SightLine 硬件形态与极简部署策略.md` | **已废弃** | 内容已被 Final Spec 吸收（SEP 协议细节需从此处补充） |

### 0.2 跨文档矛盾裁定

经交叉验证发现以下关键矛盾，统一裁定如下：

| # | 矛盾点 | 涉及文档 | 裁定 |
|---|--------|---------|------|
| 1 | **架构模式**：Direct browser-to-Gemini vs Server-to-Server | Technical Research §753 vs 其他所有文档 | **Server-to-Server**。删除 Technical Research 中的直连方案残留 |
| 2 | **Memory 存储方案**：自建 Firestore 图谱 vs Mem0 vs Vertex AI Memory Bank | 核心架构 vs Implementation Guide vs Memory Research | **自建 Firestore MemoryBankService**（已采用，`memory/memory_bank.py`）。功能最完整（auto-extract / forget / budget / 三维排序），无外部依赖，成本更低。Vertex AI Memory Bank 和 Mem0 降级为备选，不再迁移 |
| 3 | **嵌入维度**：768 vs 2048 vs 3072 | RAG Research vs Gemini 3 Migration vs Final Spec | **2048 维**（gemini-embedding-001 native 3072d → truncated to 2048 for Firestore max） |
| 4 | **Live API 模型 ID** | 多种写法混用 | **Gemini Developer API**: `gemini-2.5-flash-native-audio-preview-12-2025`；**Vertex AI**: `gemini-live-2.5-flash-native-audio` (GA)。ADK **不会**自动映射名称，需根据 `GOOGLE_GENAI_USE_VERTEXAI` 设置对应名称（参见 ADK Part 5: How to Handle Model Names）。推荐通过 `.env` 环境变量 `GEMINI_LIVE_MODEL` 切换 |
| 5 | **Orchestrator 构建方式** | ADK 示例用 `LlmAgent` vs 实际需要 Live API bidi-streaming | ADK `LlmAgent` 仅为结构参考；实际 Orchestrator 通过 `client.aio.live.connect()` + `LiveRequestQueue` 连接 |
| 6 | **手势映射** | Final Spec §7.2 vs Voice UX Research §2.2 | 采用 **Voice UX Research 版本**（6 种手势，已在 Alignment Review 中确认） |
| 7 | **砍功能优先级** | Final Spec §12.1 vs Roadmap §4 Cut-Line | 执行时以 **Roadmap Cut-Line** 为准 |
| 8 | **vision_status 枚举值**：合并字段 vs 分离字段 | Final Spec §2.4 (`congenital_blind`) vs Context Engine §4.2 (`totally_blind` + `blindness_onset`) | **分离设计**：`vision_status: totally_blind \| low_vision` + `blindness_onset: congenital \| acquired`。合并会丢失信息，已更新 Final Spec |
| 9 | **Session Service 选型** | Final Spec §6.1 (`InMemorySessionService`) vs Memory Research §3.2 (`VertexAiSessionService`) | **Phase 5 已完成迁移**：`VertexAiSessionService`（Agent Engine ID: `8731647347169165312`）正式运行中，会话持久化生效 |
| 10 | **Long-term Memory 实现路径** | Context Engine §4.1（自建 Mem0 式） vs Memory Research（Memory Bank ~30 行） | **自建 Firestore MemoryBankService**（已采用，`memory/memory_bank.py`，340 行）。Vertex AI Memory Bank 降级为备选，不迁移。见矛盾裁定 #2 |
| 11 | **RAG Engine Embedding 模型名** | Memory Research §4.2 (`text-embedding-005`) vs 其他所有文档 (`gemini-embedding-001`) | 统一 `gemini-embedding-001`。已修正 Memory Research 中的代码示例 |
| 12 | **step_cadence 单位**：Final Spec 用 steps/sec (1.5), Consolidated/iOS 用 steps/min (72) | Final Spec §5.2 vs Consolidated §1.2 | **steps/minute**（iOS CMPedometer 原生输出） |
| 13 | **LOD 3 帧率**：Final Spec 写 1FPS，Consolidated/iOS 写 0.5FPS | Final Spec vs Consolidated §1.3 | **0.5 FPS（LOD 3 静止时）** |
| 14 | **Navigation Sub-Agent vs Tool**：Consolidated §4.2 列为独立 Sub-Agent，Final Spec §6.2 列为 Orchestrator 的 Function Calling tool | Consolidated §4.2 vs Final Spec §6.2 | **Function Calling tool on Orchestrator**（不经过独立 Agent） |
| 15 | **成本估算**：Final Spec ~$58 vs Infra Report ~$37-45 | Final Spec vs Infra Report §7.1 | **以 Infra Report 为准（$37-45），更新更详细** |
| 16 | **Session Resumption 有效期**：iOS Infra 写 "2 小时"，Final Spec 写 "10min" | iOS Infra §2.4 vs Final Spec §6.4 | **两个不同概念：WebSocket 连接生命周期 ~10min，Session Resumption handle 缓存 ~2hr** |

---

## 1. 硬件与环境感知

### 1.1 硬件形态

**设计哲学**："Hardware-Agnostic Cloud Brain"——不绑定任何特定硬件，通过 SightLine Edge Protocol (SEP) 标准化三大数据通道。

**Hackathon 硬件**：iPhone（Swift Native App）+ Apple Watch（极简心率 App）

> **前端已从 React PWA 迁移到 Swift Native iOS App**，详见 `SightLine_iOS_Native_Infra_Design.md`

| 通道 | Hackathon 实现 | 生产级目标 |
|------|---------------|-----------|
| SEP-Vision | iPhone 后置摄像头（`AVCaptureSession`）→ 768x768 JPEG @ 1FPS | 智能眼镜（Meta Ray-Ban 等）、胸前摄像头 |
| SEP-Audio | iPhone 麦克风 + AirPods（`AVAudioEngine`）→ PCM 16kHz mono | 助听器直连、多麦克风波束成形 |
| SEP-Telemetry | iPhone 原生传感器（CoreMotion + CoreLocation + HealthKit）+ Apple Watch 实时心率（WCSession）→ JSON | 盲杖 IMU、更多可穿戴设备 |

**iOS Native 解决的 PWA 致命缺陷**：

| PWA 缺陷 | iOS Native 方案 |
|---------|----------------|
| `navigator.vibrate()` iOS 不支持 — 盲人无操作确认 | `UIImpactFeedbackGenerator` 触觉反馈 |
| Standalone PWA `getUserMedia` 不可靠 | `AVCaptureSession` 原生稳定 |
| 后台音频被 iOS 随时杀掉 — Always-On 不可能 | Background Mode: Audio（`voip` category） |
| 传感器数据需 Developer Console 模拟 | **全部来自真实硬件**（CoreMotion + GPS + HealthKit + Apple Watch） |
| Demo 体验是"网页标签页" | 全屏沉浸 App，评委看到"产品" |

**剩余平台限制**：

| 限制 | 影响 | 缓解 |
|------|------|------|
| Gemini Live API 只支持 WebSocket | 无法用 WebRTC 直连 Gemini | Cloud Run 中转 WebSocket |
| 视频会话 2 分钟硬上限（无压缩时） | 会话中断 | **必须启用** `contextWindowCompression` |
| AirPods 在 playAndRecord 下降级为 HFP 单声道 | 音质下降为电话通话级 | 语音聊天场景可接受 |
| 免费 Apple ID 签名 7 天过期 | 需重新构建 | Hackathon 周期内无影响 |

### 1.2 硬件 Context 注入（SEP-Telemetry）

**数据获取方式**：

| 传感器 | 数据源 | 提取方法 | LOD 影响 |
|--------|-------|---------|---------|
| 加速度计 | `CMMotionActivityManager` + `CMPedometer` | → motion_state + step_cadence | walking/running→LOD 1, stationary→LOD 3 |
| 麦克风 RMS | `AVAudioEngine` installTap RMS 计算 | → ambient_noise_db | >80dB 强制精简, <40dB 低语模式 |
| GPS | `CLLocationManager` | → lat/lng + 空间转换检测 | 室外→室内 触发 LOD 升级 |
| 罗盘 | `CLLocationManager` heading | → heading (方位角) | 时钟位置计算 |
| 时钟 | `Date` API | → time_context (morning_commute 等) | 通勤时段降 LOD |
| 心率 | Apple Watch → watchOS App `HKWorkoutSession` → `WCSession.sendMessage` (<1s) | → heart_rate | >120 BPM 触发 PANIC 中断 |
| 心率（备份） | Apple Watch → HealthKit 系统同步（延迟 10-20 分钟） | → 长期趋势分析 | 不用于实时 PANIC |

**Telemetry JSON 报文格式**：

```json
{
  "motion_state": "walking|stationary|running|in_vehicle",
  "step_cadence": 72,
  "ambient_noise_db": 65,
  "gps": {"lat": 37.7749, "lng": -122.4194},
  "time_context": "morning_commute",
  "heart_rate": 75,
  "user_gesture": "lod_up",
  "panic": false
}
```

**传输路径**：前端 WebSocket → Cloud Run Context Parser → `LiveRequestQueue.send_content()` 以 `[TELEMETRY UPDATE] {...}` 文本消息注入 Gemini Live session context，复用同一条 WebSocket，不另开独立通道。

**发送频率（LOD-Aware 节流）**：LOD 1: 3-4s / LOD 2: 2-3s / LOD 3: 5-10s。`ImmediateTrigger`（PANIC、motion_state 切换、heart_rate_spike 等）不受节流限制，始终立即发送。

### 1.3 硬件相关配置

| 配置项 | 值 | 说明 |
|--------|---|------|
| 视频分辨率 | 768x768 JPEG | Gemini Live API 推荐 |
| 视频帧率 | 1 FPS（LOD 1-2）/ 0.3-0.5 FPS（LOD 3 静止） | 通过像素差异跳过重复帧 |
| 音频输入格式 | PCM 16-bit LE, 16kHz, Mono | Gemini Live API 要求 |
| 音频输出格式 | PCM 16-bit LE, 24kHz | Gemini Live API 输出 |
| WebSocket 路由 | `wss://cloud-run-url/ws/{user_id}/{session_id}` | 前端到 Cloud Run |
| Context Compression | trigger_tokens=100000, target=80000 | 必须启用 |
| Cloud Run 预热 | `min_instance_count=1`, `cpu_throttling=false`, startup CPU boost | 消除冷启动 |
| 屏幕常亮 | `UIApplication.shared.isIdleTimerDisabled = true` | 防止息屏 |
| 后台音频 | Background Mode: Audio（Info.plist） | App 后台/锁屏时音频管线持续运行 |

**Developer Console（Hackathon 传感器仿真）**：现在大部分传感器数据来自真实硬件（CoreMotion、GPS、Apple Watch 心率），仍可保留 Web Developer Console 用于调试和演示特殊场景（如模拟极端心率、特定 GPS 坐标）。

---

## 2. 记忆系统（Memory）

### 2.1 三层 Context 模型

| 层级 | 生命周期 | 存储位置 | 内容 |
|------|---------|---------|------|
| **Ephemeral** | ms ~ s | Gemini Context Window（实时注入） | 视频帧、传感器快照、心率突变、运动状态 |
| **Session** | min ~ hr | ADK Session State（内存/持久化） | trip_purpose, space_type, space_transitions, avg_cadence, conversation_topics, active_task, narrative_snapshot |
| **Long-term** | 跨会话 | 自建 Firestore Memory Bank（`memory/memory_bank.py`） | 用户偏好、人脸库、常去地点、行为模式、压力触发因素 |

### 2.2 长时记忆

**实际方案：自建 Firestore Memory Bank**

| 维度 | Vertex AI Memory Bank | 自建 Firestore（✅ 已采用） | Mem0 开源 |
|------|----------------------|---------------------------|-----------|
| 代码量 | ~30 行 | ~340 行 | ~50 行 |
| ADK 集成 | 原生（`VertexAiMemoryBankService`） | 手动 | 官方集成 |
| 记忆提取 | Gemini 自动提取 | 自建 extraction prompt（`memory_extractor.py`） | 内置提取 |
| 冲突处理 | 自动合并（非简单追加） | 手动实现（cosine > 0.85 更新） | 内置 |
| 检索 | `PreloadMemoryTool` 每轮自动加载 | `preload_memory()` + 三维排序 | 内置 |
| 底层存储 | Firestore | Firestore | 多种 |
| 忘记功能 | 不支持 | `forget_recent_memory()` + `forget_memory()` | 不支持 |
| 写入预算 | 无 | `MAX_NEW_MEMORIES_PER_SESSION = 5` | 无 |

**实际用法**：
```python
from memory.memory_bank import MemoryBankService

bank = MemoryBankService(user_id)
memories = bank.retrieve_memories(query, top_k=5)
bank.store_memory(content, category="preference", importance=0.8)
```

**决策说明**：初期设计首选 `VertexAiMemoryBankService`，实际开发中发现自建方案功能更完整（支持 auto-extract/forget/budget），成本更低，已确认为最终方案，不迁移。

**记忆分类**：

| 类型 | 来源 | 示例 |
|------|------|------|
| **Explicit Profile** | 用户主动填写 | vision_status, blindness_onset, has_guide_dog, tts_speed, verbosity_preference, om_level |
| **Implicit Episodic** | 系统自动提取 | preference, experience, person, location, routine, general |

**记忆提取时机**：Session 结束时（非实时，避免延迟影响）。Gemini Flash 提取 → 冲突检测（cosine_similarity > 0.85 更新，否则新建）→ confidence < 0.75 不存储（person/stress_trigger 类别要求 > 0.9）。**写入预算**：`MEMORY_WRITE_BUDGET = 5`（按 confidence 排序，超额截断），防止长会话记忆膨胀。

**检索策略**：
```
relevance = 0.5 * query_similarity + 0.3 * recency_score + 0.2 * importance_score
```
importance 权重：person > routine > preference。衰减机制：指数半衰期 24 小时（`recency = 2^(-age_hours/24)`）。

### 2.3 短时记忆（Session Context）

在 Gemini Live API 的 Context Window + ADK Session State 内维持：

```python
class SessionContext:
    trip_purpose: str           # "去面试" / "日常通勤"
    space_type: str             # "indoor" / "outdoor" / "vehicle"
    space_transitions: list     # ["室外 → 大堂", "大堂 → 电梯"]
    avg_cadence_30min: float    # 30 分钟步频均值
    conversation_topics: list   # 近期对话主题
    active_task: str | None     # "正在读菜单" / None
    narrative_snapshot: dict | None  # LOD 降级时的断点
```

**ADK State 前缀**：
- 无前缀：当前调用内临时
- `temp:`：每轮清除
- `user:`：跨会话持久化（该用户）
- `app:`：跨会话持久化（全局）

**Narrative Snapshot**：LOD 降级时保存当前任务断点（task_type、progress、remaining），LOD 恢复时从断点继续（10 分钟 TTL，超时重新开始）。

---

## 3. 引擎核心（Engine）

### 3.1 Context Engine 架构

Context Engine 不是传统的"场景匹配引擎"，而是**三层上下文融合 → LOD 决策 → Dynamic Prompt 构建**的管线：

```
Ephemeral Context (传感器)  ─┐
Session Context (会话状态)   ─┼→ LOD Decision Engine (规则引擎) → LOD 1/2/3
Long-term Context (记忆检索) ─┘         │
                                       ↓
                              Dynamic System Prompt 构建
                                       │
                                       ↓
                              Orchestrator (Gemini 2.5 Flash Live API)
```

### 3.2 LOD Decision Engine（Load Engine / 场景匹配引擎）

**核心原则**："知趣地闭嘴"——默认偏向静默，发声有认知成本，打断即降级。

**三级 LOD**：

| 等级 | 模式 | 字数 | 触发条件 | 信息内容 |
|------|------|------|---------|---------|
| LOD 1 | 静默/低语 | 15-40 词 | 行走中/跑步/高噪声/PANIC | 仅安全关键信息 |
| LOD 2 | 标准 | 80-150 词 | 缓步探索/新空间进入 | 空间布局 + 关键物体 |
| LOD 3 | 叙事 | 400-800 词 | 静止/阅读/用户请求 | 完整场景、细节、氛围 |

**决策优先级（从高到低）**：

1. **PANIC 中断**：heart_rate > 120 → 强制 LOD 1，清空 TTS 队列
2. **运动状态基线**：running/快步 → LOD 1；正常步行 → LOD 1；缓慢探索 → LOD 2；静止/车内 → LOD 3
3. **环境噪声调整**：> 80dB 强制精简
4. **空间转换提升**：进入新空间至少 LOD 2
5. **用户偏好调整**：verbosity_preference 微调
6. **O&M 水平调整**：高水平日常出行者降一级
7. **用户显式请求**（最终覆盖）："详细说说" → LOD 3，"停" → LOD 1

**实现方式**：纯规则引擎（非 LLM），因为延迟要求极高（ms 级决策）。

**发声阈值机制**：每次发声分配认知成本分数，运动越快/噪声越高则阈值越高：

| 信息类型 | info_value | 说明 |
|---------|-----------|------|
| safety_warning | 10.0 | 始终突破阈值 |
| navigation | 8.0 | 几乎始终通过 |
| face_recognition | 7.0 | 大多数情况通过 |
| spatial_description | 5.0 | LOD 2+ 通过 |
| object_enumeration | 3.0 | LOD 3 通过 |
| atmosphere | 1.0 | 仅 LOD 3 静止时通过 |

### 3.3 CoT 策略（Think-Before-Act）

受 ContextAgent（NeurIPS 2025）启发：
- LOD 1：**不启用 CoT**——延迟不可接受
- LOD 2/3：注入轻量推理链，让 Gemini 先内部推理再输出
- PANIC：直接跳过 CoT

### 3.4 Dynamic System Prompt 构建

LOD Decision Engine 输出后，构建包含以下部分的 System Prompt：

1. 用户 Profile（Persona 字段：vision_status、verbosity_preference 等——贡献 ~9% 决策准确率）
2. 当前 LOD 指令（字数限制、描述策略）
3. 实时 Ephemeral Context（传感器语义化文本）
4. Session Context（行程目的、空间状态）
5. Long-term Memory 检索结果（top-K 相关记忆）
6. Vision Sub-Agent 输出（LOD-Adaptive 提取结果）

### 3.5 Engineering Hardening（6 项工程加固）

经交叉验证补充的工程加固措施（详见各 L1 文档）：

| # | 加固点 | 优先级 | 所在文档 | 要点 |
|---|--------|-------|---------|------|
| 1 | **Telemetry LOD-Aware 节流** | P0 | Context Engine §2.4 + iOS Infra §3.6 | LOD 1: 3-4s / LOD 2: 2-3s / LOD 3: 5-10s；ImmediateTrigger 不受限 |
| 2 | **LOD Decision Log 可解释日志** | P0 | Context Engine §5.4 | `LODDecisionLog` dataclass：记录每次 LOD 决策的输入+触发规则+输出 |
| 3 | **断线 → 本地 LOD 1 降级** | P1 | iOS Infra §2.4 | WebSocket 断开时 `forceLocalLOD(1)`，本地 TTS 提示"安全模式"，重连后释放 |
| 4 | **Memory 写入预算** | P1 | Context Engine §4.3 | `MAX_NEW_MEMORIES_PER_SESSION = 5`，按 confidence 排序截断 |
| 5 | **DebugOverlay 内容规格** | P1 | iOS Infra §6.3 | LOD+触发原因、Telemetry 实时值、HR Sparkline、Memory top-3、WS 延迟 |
| 6 | **"忘掉刚才的"记忆删除** | P2 | Context Engine §4.5 | `forget_recent_memory()` Function Calling 预留接口 |

**执行顺序建议**：P0（LOD 日志 + Telemetry 节流） → P1（断线降级 + Memory 预算 + DebugOverlay） → P2（忘记接口）。P0 是 MVP 必需，P1 是 Demo 质量保障，P2 是 Phase 2 预留。

### 3.6 Proactive-Oriented Vision Extraction

Vision Sub-Agent 不回答"你看到了什么"，而是回答"对视障用户当前行动有什么影响"：

| LOD | Vision Prompt 焦点 | Token 消耗（media_resolution） |
|-----|-------------------|------------------------------|
| LOD 1 | 仅安全威胁（台阶、车辆、障碍） | `low` → 70 tokens/帧（省 94%） |
| LOD 2 | 空间导航信息（入口、路径、标识） | `medium` → 560 tokens/帧 |
| LOD 3 | 全量描述（人物、物品、文字、氛围） | `high` → 1120 tokens/帧 |

---

## 4. 交互与通信

### 4.1 交互体验（Interaction）

**核心设计**：Always-On Companion，无唤醒词，持续感知、适时说话、知趣闭嘴。

**VAD（自动语音检测）**：Gemini Live API 内建，参数随 LOD 动态调整：

| LOD | start_sensitivity | end_sensitivity | silence_duration_ms | 场景 |
|-----|-------------------|-----------------|--------------------|----|
| LOD 1 | HIGH | HIGH | 300-500ms | 行走/危险，极速响应 |
| LOD 2 | MEDIUM | MEDIUM | 700-1000ms | 探索环境 |
| LOD 3 | MEDIUM | LOW | 1200-1500ms | 静坐/阅读，允许复杂问题 |

**Gemini 独有能力**：
- **Proactive Audio**：AI 主动决定何时说话（危险/新场景时无需用户提问）
- **Affective Dialog**：识别用户情绪语调，调整回复语气
- **语义级 Barge-in**：区分真打断、背景噪音、"嗯/对"反馈

**手势映射（全屏触控区）**：

| 手势 | 动作 | 触觉反馈 |
|------|------|---------|
| 单击 | 静音/取消静音麦克风 | 短震一次 |
| 双击 | 强制中断 Agent 说话 | 短震两次 |
| 三击 | 重复上一句话 | 短震三次 |
| 长按 (3s) | 紧急暂停（全系统静音） | 长震一次 |
| 上滑 | LOD 升级（说更多） | 上升音效 |
| 下滑 | LOD 降级（说更少） | 下降音效 |
| 摇晃手机 | SOS 紧急求助 | 连续震动 |

**嘈杂环境防御（分阶段）**：

| 阶段 | 策略 | 效果 |
|------|------|------|
| Hackathon | Gemini AAD + 受控 Demo 环境 | 足够 Demo |
| Production P1 | + Pipecat + Krisp VIVA | 消除 71% 误打断 |
| Production P2 | + Picovoice Eagle 声纹验证 | 精准识别用户 |
| Future | + 多麦克风波束成形 | 方向感知 |

**个性化策略**（受 "Describe Now" ASSETS 2024 启发）：
- 先天盲人不理解颜色 → 用触觉/空间/声音类比替代
- BLV 用户偏好加速 TTS → LOD 1 采用更快语速

### 4.2 Google ADK Agent 编排

**层级架构**：

```
Orchestrator Agent (Gemini 2.5 Flash Native Audio, Live API)
├── Vision Sub-Agent (Gemini 3.1 Pro, REST)      — 场景理解/表情识别
├── OCR Sub-Agent (Gemini 3 Flash, REST, FREE)    — 文字读取
├── Memory Sub-Agent (自建 Firestore Memory Bank)  — 跨会话记忆
├── Face ID Sub-Agent (InsightFace ONNX)          — 人脸匹配
├── Tools (Function Calling on Orchestrator):
│   ├── navigate_location()                        — Google Maps 导航
│   └── google_search()                            — Grounding 搜索
```

**关键设计原则**：
- **Single Voice**：只有 Orchestrator 能对用户"说话"，Sub-Agent 以 JSON/Text 汇报
- **非阻塞视觉**：先回复"让我看看..."，异步挂载 Vision Sub-Agent，确保音频通道永远有反馈
- **后台记忆巩固**：对话中产生新偏好时后台异步更新，不阻塞主流程

**ADK 实时流处理**：

```python
runner = Runner(agent=root_agent, app_name="sightline",
                session_service=VertexAiSessionService(...))

# LiveRequestQueue 直接实例化（ADK 官方 API，不通过 runner 创建）
live_request_queue = LiveRequestQueue()
live_events = runner.run_live(session_id=sid, user_id=uid,
                              live_request_queue=live_request_queue)

# 实时注入音频/视频/遥测
live_request_queue.send_realtime(audio_chunk)       # PCM 16kHz
live_request_queue.send_realtime(video_frame)       # JPEG base64
live_request_queue.send_content("[TELEMETRY UPDATE] {...}")  # 传感器
```

**必须补充的 RunConfig**：
- `input_audio_transcription=True`：前端字幕 + LOD 意图分析 + Memory 存储
- `output_audio_transcription=True`：同上
- `enable_affective_dialog=True`：放在 `LiveConnectConfig` 顶层

### 4.3 底层网络 Infra

**Hackathon 架构（Server-to-Server）**：

```
iPhone App ──NWConnection WSS──→ Cloud Run (FastAPI + ADK) ──WebSocket (WSS)──→ Gemini Live API
    ↑                                      ↕
Apple Watch ──WCSession──→ iPhone    Sub-Agents (Vision/OCR/FaceID/Memory)
  (实时心率)                           Firestore / Maps API / Google Search
```

**数据流**：
- 前端通过 `AVCaptureSession` 获取视频，`AVAudioEngine` 获取音频
- `AVAudioEngine` installTap 切分 PCM 16kHz 块（每 100ms 一个 chunk）
- `CIImage` → resize 768x768 → JPEG 编码（硬件加速）
- 一条 NWConnection WebSocket 承载 audio + image + telemetry（不另开通道）
- Apple Watch 心率通过 WCSession 实时送达 iPhone，注入 Telemetry
- API Key 在后端 Secret Manager，前端不接触

**延迟分解（Swift Native）**：

| 环节 | 延迟 |
|------|------|
| 摄像头捕获 | ~8ms |
| JPEG 编码 | ~3-8ms |
| Base64 编码 | ~1-2ms |
| WebSocket 传输 | ~20-80ms |
| **Gemini 处理** | **500ms-6000ms** ← 主瓶颈 |
| 流式音频播放 | ~10-20ms |
| **总感知延迟** | **~550ms - 6100ms** |

**优化策略（Hackathon）**：
1. 流式播放（音频块到达即播），不等完整响应
2. 预反馈："Let me look at that..."
3. 客户端帧选择（像素差异跳过重复场景）
4. Context Compression（无限会话）
5. Session Resumption（WebSocket 连接 ~10min 生命周期，断线后 resumption handle 缓存有效期 ~2hr）
7. **断线 LOD 降级**：WebSocket 断开时本地强制 LOD 1 + 本地 TTS "安全模式"提示 + 触觉反馈，重连后恢复正常
6. Cloud Run 预热（`min_instance_count=1`）

**Production 升级路径**：
```
Phone ──WebRTC (UDP)──→ Pipecat/Daily Edge ──WebSocket──→ Cloud Run ──WSS──→ Gemini
```
WebRTC 用 UDP 处理"最后一公里"，消除 TCP 队头阻塞（移动 4G 下 WebSocket 延迟可飙至 10-15s）。

---

## 5. 功能与集成

### 5.1 Function Calling

**两种模式**：

| 模式 | 用于 | 定义方式 |
|------|------|---------|
| Gemini Live API Function Calling | Orchestrator 实时流中 | `LiveConnectConfig.tools` → `FunctionDeclaration` |
| ADK Agent Tools | Sub-Agent REST 调用 | `LlmAgent(tools=[python_function])` |

**三种调度行为**：

| 行为 | 用途 | 示例 |
|------|------|------|
| `INTERRUPT` | 安全警报，立即打断 | 检测到危险 |
| `WHEN_IDLE` | 模型说完后交付 | 导航结果、搜索结果 |
| `SILENT` | 后台静默存入 context | Telemetry 更新 |

**已定义的 Function 列表**：

| Function | 用途 | 行为模式 |
|----------|------|-----------|
| `navigate_to(destination, origin_lat, origin_lng, user_heading)` | 步行导航（时钟方位） | WHEN_IDLE / LOD1:INTERRUPT |
| `get_location_info(lat, lng)` | 位置信息 + 附近 POI | WHEN_IDLE |
| `nearby_search(lat, lng, radius, types, keyword)` | 附近地点搜索 | WHEN_IDLE |
| `reverse_geocode(lat, lng)` | 反向地理编码 | WHEN_IDLE |
| `get_walking_directions(origin, destination)` | 文本地址步行路线 | WHEN_IDLE |
| `google_search(query)` | 实时信息查询（Grounding） | WHEN_IDLE |
| `identify_person(description)` | 人脸识别（静默注入 context） | SILENT |
| `register_face(user_id, person_name, relationship, image_base64)` | 注册人脸嵌入（3-5 样本） | REST API |
| `load_face_library(user_id)` | 加载人脸库用于实时匹配 | Internal |
| `preload_memory(user_id, context)` | 预加载相关长期记忆 | Internal |
| `forget_recent_memory(user_id, minutes)` | 删除近 N 分钟记忆 | Function Calling |
| `forget_memory(user_id, memory_id)` | 删除指定记忆 | Function Calling |

**Gemini 3 注意事项**：Thought Signatures（加密签名令牌）必须按原序返回。使用官方 SDK 自动处理。

### 5.2 需要集成的 API

| API | 用途 | 免费额度 | Hackathon 成本 |
|-----|------|---------|---------------|
| **Gemini Live API** | 核心实时双向音频+视频流 | Free tier: 3 并发 | ~$22-25/月 |
| **Gemini 3 Flash (REST)** | OCR/Navigation/Memory sub-agents | **预览期免费** | $0 |
| **Gemini 3.1 Pro (REST)** | Vision 深度分析 | 付费 | ~$10-15 |
| **gemini-embedding-001** | 记忆/RAG 向量嵌入 | 包含在 Firestore 额度 | ~$0 |
| **Google Maps Places** | 附近地点搜索 | 10,000/月 | $0 |
| **Google Maps Routes** | 步行导航 | 10,000/月 | $0 |
| **Google Maps Geocoding** | 地址↔坐标 | 10,000/月 | $0 |
| **Google Search Grounding** | 实时信息查询 | 包含在 Gemini 调用 | ~$0 |
| **Firestore** | 用户数据 + 人脸向量 + 记忆 | 50K读/20K写/天 | $0 |
| **Cloud Run** | 后端部署 | 200 万请求/月 | ~$5 |
| **Secret Manager** | API Key 存储 | 6 个版本免费 | $0 |
| **OpenStreetMap Overpass** | 无障碍设施数据（触觉铺装、有声信号灯） | 无限 | $0 |

**Hackathon 总成本估算**：~$37-45（详见 Infra Report §7.1）

### 5.3 人脸识别系统

**方案：InsightFace buffalo_l (ONNX)**

| 维度 | 值 |
|------|---|
| LFW 准确率 | 99.83% |
| 嵌入维度 | 512-D |
| CPU 延迟 | 100-250ms |
| 推理框架 | ONNX Runtime |
| Docker 镜像 | ~1.2GB (`python:3.12-slim`) |
| 部署 | 独立 Cloud Run 服务 |

**注册流程**：用户拍照 → InsightFace 检测人脸 → 生成 512-D 嵌入 → L2 归一化 → 存入 Firestore `Vector` 字段

**匹配流程**：未知人脸 → 生成嵌入 → L2 归一化 → 与已知人脸计算余弦相似度（点积）→ 阈值 > 0.4 即匹配

**优化**：< 100 人场景，会话开始时加载所有嵌入到内存，内存级余弦相似度计算。

**隐私**：不存储原始图像，仅存储嵌入向量。

**为什么不用 Cloud Vision**：Google Cloud Vision API 仅做人脸检测（位置、表情），**不生成嵌入，不做识别**。

### 5.4 RAG 架构

**向量数据库：Firestore 原生向量搜索**（无需独立向量数据库）

**嵌入模型：`gemini-embedding-001`**
- Native 3072 维 → `output_dimensionality=2048`（Firestore 上限）
- Matryoshka Representation Learning，截断后质量保持良好
- GA 稳定版，MTEB 多语言排名第一，100+ 语言

**索引创建**：
```bash
gcloud firestore indexes composite create \
  --collection-group=memories \
  --query-scope=COLLECTION \
  --field-config field-path=embedding,vector-config='{"dimension":"2048","flat":"{}"}'
```

**检索流程**：
1. 当前上下文 → `gemini-embedding-001` 生成查询向量
2. Firestore `find_nearest()` KNN 搜索（COSINE 距离）
3. 返回 top-K 结果
4. 三维加权排序：`0.5 * relevance + 0.3 * recency + 0.2 * importance`

**与 Memory 系统的关系**：RAG 是 Memory 系统的底层检索机制。自建 Firestore Memory Bank（`memory/memory_bank.py`）直接使用 Firestore 向量搜索（`find_nearest`）做语义检索，开发者通过 `MemoryBankService` API 操作。

---

## 6. 技术栈总览

| 层级 | 选型 | 说明 |
|------|------|------|
| **Orchestrator 模型** | Developer API: `gemini-2.5-flash-native-audio-preview-12-2025` / Vertex AI: `gemini-live-2.5-flash-native-audio` (GA) | Live API 仅支持 2.5；**ADK 不自动映射名称**，需通过 `.env` 按平台配置 |
| **Vision 模型** | `gemini-3.1-pro-preview` | 最佳推理，1M 上下文 |
| **轻量 Sub-agent** | `gemini-3-flash-preview` | **预览期免费**（仅 Gemini Developer API Free Tier；Vertex AI 上正常计费） |
| **Embedding** | `gemini-embedding-001` (2048d) | GA，MTEB 第一 |
| **Agent 框架** | Google ADK (Python) | 唯一原生 Live API 支持 |
| **人脸识别** | InsightFace buffalo_l (ONNX, 512-D) | 99.83% LFW |
| **后端** | Cloud Run + FastAPI + ADK | 一命令部署 |
| **数据库** | Firestore（原生向量搜索） | 用户/人脸/记忆 |
| **记忆服务** | 自建 Firestore Memory Bank（`memory/memory_bank.py`） | ~340 行，支持 auto-extract/forget/budget |
| **iOS 前端** | Swift Native (AVFoundation + CoreMotion + HealthKit + NWConnection) | 详见 iOS Infra Design |
| **watchOS 前端** | SwiftUI + HKWorkoutSession + WCSession (~500-680 行) | 实时心率传输 |
| **基础设施** | Terraform + Cloud Build + Secret Manager | +0.2 加分项 |

> ⚠️ **模型名称映射**：ADK 不会自动在 Gemini Developer API 和 Vertex AI 之间翻译模型名称（见 [ADK Part 5: How to Handle Model Names](https://google.github.io/adk-docs/streaming/dev-guide/part5/#how-to-handle-model-names)）。`.env` 中的 `GEMINI_LIVE_MODEL` 必须与 `GOOGLE_GENAI_USE_VERTEXAI` 设置匹配。Vertex AI 上推荐 GA 稳定版 `gemini-live-2.5-flash-native-audio`（有效期至 2026-12-12），比 preview 版更可靠。

### 6.1 Gemini 模型版本注意

| 参数 | Gemini 2.5 (Live API) | Gemini 3 (REST Sub-agents) |
|------|----------------------|---------------------------|
| thinking | `thinking_budget`（整数） | `thinking_level`（枚举：minimal/low/medium/high） |
| temperature | 可调 | **强烈建议 1.0** |
| media_resolution | 不支持 | 支持（low/medium/high/ultra_high） |
| Thought Signatures | 无 | 加密签名令牌（SDK 自动处理） |

**已弃用模型（立即移除）**：
- `gemini-2.0-flash-live-001`：已关闭
- `gemini-live-2.5-flash-preview`：已关闭
- `text-embedding-004`：计划关闭
- `embedding-001`：立即迁移

---

## 7. 竞赛策略摘要

### 7.1 评分权重

| 标准 | 权重 | SightLine 匹配度 |
|------|------|-----------------|
| Innovation & Multimodal UX | **40%** | 极高（盲人=最彻底的"打破文本框"） |
| Technical Implementation | **30%** | 极高（6+ Agent + 5+ GCP 服务） |
| Demo & Presentation | **30%** | 高（最大情感冲击 + Proactive Audio Wow Moment） |

### 7.2 必须展示的能力（P0）

1. Gemini Live API 实时双向音频+视频流
2. 多代理架构（ADK Orchestrator + Sub-Agents）
3. Google Search Grounding（防幻觉）
4. 视觉输入（Camera/Video）

### 7.3 加分项

- Terraform + Cloud Build 自动部署：+0.2
- Medium/Dev.to 技术博客 + YouTube：+0.6
- GDG 会员：+0.2

### 7.4 Demo 场景设计

围绕 LOD 层级切换设计 3 个场景（4 分钟内）：
1. **行走场景**（LOD 1）：快步行走时 SightLine 保持静默，仅在检测到台阶/车辆时主动警告
2. **探索场景**（LOD 2）：缓步进入咖啡馆，描述空间布局、入口位置、人数
3. **静坐场景**（LOD 3）：坐下后，详细朗读菜单、描述对面人的表情、回忆该人的名字

核心 Pitch：*"We didn't build a radar; we built a Semantic Interpreter."*

---

## 8. 开发执行建议

### 8.1 推荐的文档阅读顺序

1. **本文档**（统一参考）→ 全局理解
2. `SightLine_iOS_Native_Infra_Design.md` → iOS/watchOS 前端完整设计
3. `SightLine_Subtasks_Roadmap.md` → 获取具体 Phase/Task 分解
4. `engine/Context_Engine_Implementation_Guide.md` → LOD Engine 实现细节
5. `SightLine_Best_Practices_Research.md` → ADK bidi-demo 模板代码
6. `raw_research/infra/*` → 按需查阅特定 API 用法

### 8.2 可归档/不再查阅的文档

- `SightLine 核心架构_ Agent编排与上下文建模.md`（DEPRECATED）
- `SightLine 硬件形态与极简部署策略.md`（DEPRECATED，SEP 细节已在本文档覆盖）
- `raw_research/competition/*` 和 `raw_research/product/*`（策略已定，不需再看）
- `Gemini_Live_Agent_Challenge_Deep_Research.md` 和 `Gemini_Live_Agent_Challenge_Strategy.md`（竞赛要求已提取到本文档 §7）

### 8.3 关键风险提醒

| 风险 | 级别 | 缓解 |
|------|------|------|
| ~~iOS standalone PWA 摄像头故障~~ | ~~高~~ | ~~已通过迁移到 Swift Native 解决~~ |
| Gemini Live API 高峰期延迟 5-15s | **中** | 预反馈 + 流式播放 + 避开高峰时段 Demo |
| 09-2025 模型 2026-03-19 弃用 | **中** | 已使用 12-2025 版本，无影响 |
| ~~Vertex AI Memory Bank 提取逻辑不够灵活~~ | ~~低~~ | ~~已采用自建 Firestore 方案，功能更完整~~ |
| Context Compression 未启用导致 2 分钟断会 | **高** | 配置检查清单第一项 |
