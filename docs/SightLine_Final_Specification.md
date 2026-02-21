# SightLine: Final Product Specification

> **Version**: 1.0 — 定稿
> **Date**: 2026-02-21
> **Competition**: Gemini Live Agent Challenge (Track: Live Agents)
> **Deadline**: 2026-03-16 5:00 PM PDT
> **Core Thesis**: 视障群体的语义翻译官，用自适应 LOD + 多维上下文感知重新定义 AI 辅助交互

---

## 1. 产品定位与核心卖点

### 1.1 一句话定义

SightLine 是一个**上下文感知 (Context-Aware) 的实时语义翻译官**，通过自适应细节层级 (Adaptive LOD) 机制，在正确的时间、以正确的密度，向视障用户传递环境信息。

### 1.2 两大核心卖点 (Demo 时集中打这两点)

| 卖点 | 为什么是杀手级 | 学术背书 |
|------|-------------|---------|
| **Adaptive LOD** | 全市场零竞品实现；不是"少说话"，是根据用户物理状态+认知负荷动态调节信息密度 | DIS 2025: 手动控制细节层级反而增加认知负荷；ASSETS 2025: 5/8 BLV 用户明确要求自适应细节层级 |
| **Context Awareness** | 三层上下文融合 (极短期/会话期/长期)，让 AI 真正"懂"用户当前状态；融合生理信号+运动状态+空间注意力 | Pedestrian Stress 2025: HRV 对 30-120s 步行压力可靠；Science Robotics 2021: 减少认知负荷的辅助将行走速度提高 18% |

### 1.3 不做什么 (明确边界)

- **不做物理避障**：不替代白手杖或导盲犬。时延 1-2 秒的云端 AI 无法承担毫秒级安全职责。
- **不做通用聊天**：SightLine 不是 ChatGPT 加摄像头，是一个有明确场景和用户群的产品。
- **不做离线功能**：Hackathon 范围内，完全依赖云端 Gemini。

---

## 2. LOD 系统详细设计

### 2.1 三级 LOD 定义

| Level | 名称 | 触发条件 | 信息密度 | 语音风格 |
|-------|------|---------|---------|---------|
| **LOD 1** | Silent / Whisper | 用户在移动 (步频 > 阈值)；心率突升 (恐慌)；高噪声环境 | 完全静默，或仅一句话 (15-40 词)。例："前方十米是星巴克入口" | 简短、平静、不抢夺注意力 |
| **LOD 2** | Standard | 用户缓步或驻足探索；进入新空间 | 中等描述 (80-150 词)。空间布局 + 关键物体 | 中等语速、清晰 |
| **LOD 3** | Narrative | 用户坐下/静止；主动提问；手持物品需要阅读 | 全量描述 (400-800 词)。OCR、菜单阅读、详细场景叙述 | 慢速、富有表现力、叙事弧 |

### 2.2 LOD 切换算法 (Context Fusion)

```
每次 Orchestrator 决策前:

1. 读取极短期上下文 (Ephemeral):
   - 当前帧视觉内容
   - 运动状态 motion_state (手机加速度计: stationary/walking/running/in_vehicle)
   - 步频 step_cadence (手机加速度计, 单位: steps/minute)
   - 环境噪声 ambient_noise_db (手机麦克风后台分析)
   - 实时心率 heart_rate (若有手表，可选)
   - 用户语音打断信号

2. 读取会话期上下文 (Session):
   - 用户今天的出行目的 ("我要去面试")
   - 当前空间类型 (室内/室外/交通工具)
   - 近 N 分钟步频均值
   - 当前对话话题和叙事位置
   - 时间上下文 time_context (时段推断: morning_commute/work_hours/evening)

3. 读取长期上下文 (Long-term):
   - 用户偏好 (语速、详细程度偏好)
   - 视力状态 vision_status (congenital_blind | acquired_blind | low_vision)
   - 颜色描述开关 color_description (先天盲人 = false)
   - TTS 语速偏好 preferred_tts_speed (0.75 - 2.0)
   - 已知人脸库
   - 常去地点
   - 历史压力触发器

4. 融合决策:
   - 如果 heart_rate 可用且触发 PANIC → 强制 LOD 1，清空播放队列
   - 否则基于 motion_state + step_cadence + ambient_noise_db 加权融合三层 Context，计算目标 LOD
   - 平滑过渡 (避免频繁跳级)
```

### 2.3 "知趣地闭嘴" 设计原则

这是 LOD 的灵魂。实现要点：

- **默认偏向静默**：没有充分理由不说话。LOD 1 不等于"少说"，等于"几乎不说"。
- **说话有成本**：系统内部给每次发声分配一个"认知成本"分数，当用户物理活动水平高时，成本阈值大幅提高，只有高价值信息才能突破阈值。
- **打断即降级**：用户任何时候说"停"或物理状态变化 (开始走路)，立即降级。
- **恢复有记忆**：LOD 降级时保存叙事快照 (Narrative Snapshot)。当条件恢复后，AI 从中断点继续，而不是从头开始。
- **先通用后细节**："Start with general context, then add details" (Describe Now, ASSETS 2024) — LOD 1→2→3 的渐进式描述。
- **避免过度描述**："Avoid over-describing; choose level of detail based on relevance" — 只有与用户任务相关的信息才值得说。

### 2.4 LOD-Adaptive 描述个性化 (受 Describe Now 论文启发)

> **来源**: *Describe Now: User-Driven Audio Description for BLV* (ASSETS 2024, PMC)

**关键发现**：先天盲人不理解颜色描述。一位参与者说："mention of colors made no sense to me as a congenitally blind person"。

根据用户 `vision_status` + `blindness_onset` 动态调整 LOD 描述策略：

> **字段设计说明**：采用 `vision_status` (totally_blind | low_vision) + `blindness_onset` (congenital | acquired) 分离设计，因为 `totally_blind + congenital` 与 `totally_blind + acquired` 的描述策略完全不同。详见 Context Engine §4.2 UserProfile。

| 用户类型 | 描述策略 |
|---------|----------|
| **先天全盲** (totally_blind + congenital) | 使用触觉、空间、声音类比描述。**不描述颜色**。用尺寸比较 ("像背包那么大") 代替视觉描述。 |
| **后天全盲** (totally_blind + acquired) | 可以使用颜色和视觉记忆相关的词汇。用户可能记得视觉概念。 |
| **低视力** (low_vision) | 使用高对比度描述。强调空间关系和大小。颜色可用但需简洁。 |

**System Prompt 动态注入** (基于 Firestore 用户档案)：

```python
# 先天全盲版本
if user_profile.vision_status == "totally_blind" and user_profile.blindness_onset == "congenital":
    lod_context += """
    IMPORTANT: This user has been blind since birth.
    - DO NOT describe colors. Use spatial, tactile, and auditory terms instead.
    - Use size comparisons with familiar objects ("about the size of a coffee mug").
    - Describe textures and sounds when relevant.
    - Use spatial relationships precisely ("to your left", "about three steps ahead").
    """
```

---

## 3. Context Awareness 多维上下文建模

### 3.1 上下文数据源与生命周期

| 层级 | 时间尺度 | 数据源 | 用途 |
|------|---------|--------|------|
| **Ephemeral** | 毫秒~秒 | 视频帧、音频打断、心率突变、陀螺仪剧烈晃动 | 最高中断优先级；危险信号立即清空 TTS 队列 |
| **Session** | 分钟~小时 | 出行目的、空间类型、步频均值、对话历史 | 维持系统平稳运行；例如知道用户"正在喝咖啡"→ LOD 稳定在 3 |
| **Long-term** | 跨会话 | Firestore 存储：用户偏好、人脸库、常去地点、压力触发器 | 个性化；让 AI 越来越"懂"用户 |

> **Persona 重要性的量化证据** (ContextAgent, NeurIPS 2025 消融实验)：
> - 去掉 Persona 后，主动决策准确率 (Acc-P) 下降 **9.0%**，工具选择 F1 下降 **12.3%**
> - 去掉视觉模态后，Acc-P 下降 **17.9%**，F1 下降 **23.3%**（视觉是最关键模态）
> - 去掉音频模态后，影响较小但仍显著
>
> **结论**：`vision_status`、`verbosity_preference`、`om_level` 等 Persona 字段不是锦上添花——它们对 LOD 决策质量的贡献接近 10%。Long-term Context 层的实现优先级应与 Ephemeral 层同等重要。

### 3.2 Hackathon 中的 Context 输入方式

| 数据类型 | 来源 | Hackathon 实现 | 生产级实现 |
|---------|------|---------------|-----------|
| 视频流 | 手机摄像头 | `AVCaptureSession` → JPEG 768x768 @ 1FPS → NWConnection WebSocket 上传 | 智能眼镜、胸前摄像头 via SEP-Vision |
| 音频 | 手机麦克风 | `AVAudioEngine` installTap → PCM 16kHz Mono → NWConnection WebSocket 上传 | 骨传导耳机、助听器 via SEP-Audio |
| **运动状态** | 手机加速度计 | iOS CMMotionActivityManager 真实硬件 | iOS CMMotionActivityManager / Android ActivityRecognitionClient |
| **步频** | 手机加速度计 | iOS CMPedometer 真实硬件 | iOS CMPedometer / Android TYPE_STEP_COUNTER |
| **环境噪声** | 手机麦克风 | iOS AVAudioEngine RMS 实时计算 | 麦克风背景 RMS → dB 实时计算 |
| **时间上下文** | 手机时钟 | 自动获取 (无需模拟) | 同左 + 结合长期记忆推断时段模式 |
| 地理位置 | 手机 GPS | 手机 GPS (真实) | 同左 + 更精确的 UWB 定位 |
| 心率 *(可选)* | 智能手表 | Apple Watch HKWorkoutSession → WCSession (<1s 实时传输) | Apple Watch / 运动手环 via SEP-Telemetry |

**Developer Console 设计**：由于运动状态、步频、环境噪声、心率等传感器数据已全部来自 iOS 真实硬件（CMMotionActivityManager、CMPedometer、AVAudioEngine RMS、Apple Watch HKWorkoutSession），Developer Console 仅保留用于调试和 Demo 特殊场景模拟（如模拟极端心率、特定噪声环境等）。在 Demo 中可向评委展示真实传感器数据流，证明：(1) 云端 Agent 是 100% 真实运行的，(2) 传感器数据来自真实硬件而非模拟。

---

## 4. 人脸库 (Familiar Face Recognition)

### 4.1 产品价值

这是 SightLine 的温情亮点。场景示例：
- 用户的妻子走进房间 → AI 低声说："Sarah 进来了，看起来笑着。"
- 用户的老板走过来 → AI 说："David 在向你走来，表情看起来心情不错。"
- 陌生人 → AI 只说"有人向你走来"，不做身份识别。

### 4.2 技术实现方案

**核心结论：Gemini 不能直接做人脸匹配。** Gemini Vision 能检测人脸存在、描述表情、识别公众人物，但无法维护自定义人脸库或生成/匹配 face embeddings。因此需要**独立的人脸识别 pipeline + Gemini Function Calling 集成**。

#### 架构

```
Camera Frame ──────────────────────────────────────> Gemini Live API
     │                                                    ↑
     │                                                    │ tool response:
     ▼                                                    │ {"name": "David",
InsightFace buffalo_l (ONNX)                              │  "relationship": "boss"}
  ├── Detection (RetinaFace)                              │
  └── Embedding (ArcFace, 512-D)                          │
     │                                                    │
     ▼                                                    │
Cosine Similarity Match vs Library ──── if match ────────>┘
```

#### 注册流程 (由视力正常的亲属操作)

1. 拍照 → InsightFace 人脸检测 (RetinaFace) → 裁剪对齐
2. 生成 512 维 face embedding (使用 InsightFace `buffalo_l` 模型, ArcFace backbone, 99.83% LFW)
3. 存入 Firestore (使用原生 `Vector()` 类型)：
```python
from google.cloud.firestore_v1.vector import Vector

doc_ref.set({
    "person_id": "uuid",
    "name": "David",
    "relationship": "boss",
    "embedding": Vector(embedding_512dim),  # 512-D, Firestore 原生向量类型
    "registered_by": "user_wife",
    "created_at": firestore.SERVER_TIMESTAMP,
})
```
4. 每人存储 3-5 张不同角度/光线的 embedding 以提高识别率。
5. 对于 < 100 人的库：会话启动时加载全部 embedding 到内存，实时匹配走内存计算（比逐帧查 Firestore 更快）。

#### 实时匹配流程

1. 从视频流中抽帧 (1-2 FPS 足够)
2. InsightFace 人脸检测 → 找到所有人脸 bounding box
3. 对每张脸生成 512-D embedding (ArcFace, ONNX Runtime, ~100-250ms/帧 CPU)
4. 与库中所有 embedding 计算 cosine similarity (内存中 brute-force)
5. 若 max_similarity > 0.4 → 匹配成功 (InsightFace 推荐阈值)
6. 将匹配结果通过 Function Calling 返回给 Gemini：
   - Gemini 调用 `identify_person` tool
   - 返回 `{"name": "David", "relationship": "boss"}`
   - Gemini 融合视觉描述 + 身份信息，生成自然语言："你的老板 David 走过来了，看起来心情不错。"

#### Hackathon MVP 实现

| 组件 | 技术选择 | 理由 |
|------|---------|------|
| 人脸检测+嵌入 | InsightFace `buffalo_l` (ONNX Runtime, CPU) | 99.83% LFW, 512-D, 无 TF/PyTorch 依赖, Docker 镜像 ~1.2GB |
| 人脸库存储 | Firestore (`Vector()` 原生向量类型 + `find_nearest()`) | 原生 KNN 搜索；< 100 人可内存 brute-force < 1ms |
| Gemini 集成 | Function Calling (`identify_person` tool) | Gemini 决定何时需要识别，干净的关注点分离 |

### 4.3 隐私声明 (提交材料中写明)

在 submission 的文字描述中加入：
- 人脸库仅存储数学特征向量 (embedding)，不存储原始照片。
- 仅识别已被家人/朋友**主动注册**的人。未注册的人只会被描述外观，不会被识别身份。
- 数据存储在用户自己的 Firestore 账户中，用户拥有完全控制权。
- 提供一键清除所有人脸数据的功能。

---

## 5. 硬件无关性 (Hardware-Agnostic) 决策

### 5.1 结论：做协议层设计，但 Hackathon 内不硬推

**你应该做"硬件无关"的架构设计，但不应该把它当作核心卖点来推。**

理由：
- **做的好处**：(a) 架构解耦本身就是好的工程实践，(b) 向评委展示"前瞻性"和"平台思维"，(c) 为赛后发展留门。
- **不当核心卖点的原因**：(a) 没有用户基数的协议不会有厂商接入，(b) 竞品验证报告已明确标注这是"过度愿景"，(c) 评委更看重真实可用的 Demo 而非宏大画饼。

### 5.2 SightLine Edge Protocol (SEP) 精简版

保留三通道解耦设计，但在 Pitch 中作为"架构亮点"一笔带过，不作为产品 USP：

#### SEP-Vision (视觉通道)

| 协议 | 覆盖设备 | 优先级 |
|------|---------|--------|
| **WebRTC** | 手机浏览器摄像头、PWA | **P0 (Hackathon 唯一实现)** |
| RTMP ingest | GoPro、DJI 运动相机 | P1 (赛后) |
| RTSP pull | IP 摄像头、RunCam WiFiLink | P1 (赛后) |
| USB UVC | USB 摄像头、HDMI 采集卡 | P2 (赛后) |

**Hackathon 策略**：仅实现 WebRTC (手机摄像头)。在架构图中画出 RTMP/RTSP/UVC 接口，但标注为 "future integration"。如果评委问到，说明：

> "Our cloud agent is protocol-agnostic. Today we demonstrate with WebRTC from a phone camera. But our SEP gateway is designed to accept RTMP (for GoPro/DJI), RTSP (for IP cameras), and UVC (for USB cameras). The AI backend doesn't care where the pixels come from — it only processes standardized frames."

#### SEP-Audio (音频通道)

| 协议 | 覆盖设备 | 说明 |
|------|---------|------|
| **AVAudioSession (iOS)** | 所有蓝牙设备 (iOS 系统抽象蓝牙层) | `AVAudioSession` 配置 `.allowBluetooth` + `.allowBluetoothA2DP` 自动处理 HFP/A2DP 蓝牙协商 |
| HFP (Hands-Free Profile) | 所有蓝牙耳机、助听器、骨传导 | 双向单声道 8-16kHz，语音 AI 完全够用 |

**关键洞察**：不需要写任何蓝牙协议代码。iOS `AVAudioSession` 已经抽象掉了蓝牙细节。用户连什么蓝牙设备，系统会自动用 HFP 建立双向音频通道。注意：AirPods 在 `playAndRecord` 模式下会降级为 HFP 单声道（语音聊天场景可接受）。

#### SEP-Telemetry (遥测通道)

标准化 JSON 格式（轻量化设计：Core 字段全部来自手机，无需额外设备）：
```json
{
  "timestamp": "2026-02-21T10:30:00Z",

  // === Core 字段 (手机自带传感器，零额外硬件) ===
  "step_cadence": 72,              // 单位: steps/minute (来自 iOS CMPedometer)
  "motion_state": "walking",        // "stationary" | "walking" | "running" | "in_vehicle"
  "ambient_noise_db": 65,
  "gps": { "lat": 37.7749, "lng": -122.4194 },
  "time_context": { "hour": 8, "period": "morning_commute" },

  // === Optional 字段 (有智能手表时启用) ===
  "heart_rate": 78,                  // null if no watch connected

  "device_type": "phone_only",       // "phone_only" | "phone_and_watch" | "simulation_console"
  "optional_devices": ["apple_watch"]
}
```

**设计原则：手机即主传感器。** Core 字段通过手机加速度计（运动/步频）、麦克风（噪声）、GPS、时钟即可获取，用户无需佩戴任何额外设备。heart_rate 为可选增强，有手表时自动启用。

**传输方式**：Telemetry 数据通过 ADK WebSocket 的 `LiveRequestQueue.send_content()` 以文本消息注入 Live session context，格式为 `[TELEMETRY UPDATE] {...}`。不另开独立通道，复用同一条 WebSocket 连接。这样 Gemini 可以直接在对话上下文中读取传感器数据，驱动 LOD 决策。

Hackathon 中：Developer Console 通过同一 WebSocket 发送模拟数据。
赛后：手机原生传感器 API 提供 Core 数据 + Apple Watch 提供 Optional 数据。

### 5.3 媒体中继方案 (赛后扩展)

如果要支持多种摄像头，推荐使用 **MediaMTX** 作为通用媒体中继：

```
GoPro ──RTMP──> MediaMTX ──WebRTC──> SightLine Cloud
DJI   ──RTMP──>    ↑
RunCam ──RTSP──>   │
USB cam ──FFmpeg──>┘
```

MediaMTX 是开源的媒体服务器，能接收 RTMP push、RTSP pull，统一转发为 WebRTC/HLS/RTSP。一个组件解决所有摄像头适配问题。

---

## 6. Agent 编排架构

### 6.1 端到端数据流拓扑 (ADK Server-to-Server 模式)

**架构决策：采用 ADK Server-to-Server (全代理) 模式。**

Google Live API 仅支持 WebSocket (WSS)，不支持 WebRTC/gRPC。iOS 前端通过 `AVCaptureSession`/`AVAudioEngine` 采集媒体，经 NWConnection WebSocket 发送到 Cloud Run 后端，后端通过 ADK `run_live()` + `LiveRequestQueue` 管理与 Gemini 的双向流式会话。

选择全代理而非客户端直连的理由：
- ADK `run_live()` 自动处理 Function Calling、agent transfer、session state
- Sub-Agent (Vision/OCR/FaceID) 全部跑在后端，直连模式下调用路径极其复杂
- API Key 留在服务端 (via Secret Manager)，无需前端 ephemeral token
- 延迟增加可控：Cloud Run 同区域 <10ms 一跳
- 参考实现：[google/adk-samples/bidi-demo](https://github.com/google/adk-samples/tree/main/python/agents/bidi-demo)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ iPhone (Swift Native App)                                                │
│  ├── AVCaptureSession → 摄像头 (768x768 JPEG, 1FPS) + AVAudioEngine → 麦克风 │
│  ├── AVAudioEngine installTap (PCM 16kHz Mono, 每100ms chunk)            │
│  ├── NWConnection WebSocket → wss://cloud-run-url/ws/{user_id}/{session_id} │
│  ├── AVAudioPlayerNode (24kHz PCM playback)                              │
│  ├── Telemetry: CoreMotion + GPS + HealthKit + Apple Watch → JSON via 同一 WebSocket │
│  └── UIApplication.isIdleTimerDisabled (防息屏)                           │
└────────────────────────────┬───────────────────────────────────────────────┘
Apple Watch (watchOS App) ── WCSession ──→ iPhone (实时心率)
                             │ WebSocket (WSS)
                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Cloud Run (FastAPI + ADK)                                                 │
│  ├── POST /api/token  → (预留) Ephemeral Token 签发                       │
│  ├── WS /ws/{user_id}/{session_id}  → ADK WebSocket Handler              │
│  │    ├── Upstream Task:  WebSocket → LiveRequestQueue.send_realtime()    │
│  │    └── Downstream Task: runner.run_live() events → WebSocket           │
│  │                                                                        │
│  ├──【Orchestrator Agent】←── Adaptive LOD Engine                         │
│  │    (Gemini 2.5 Flash Native Audio — Live API 仅支持 2.5)               │
│  │    │                                                                   │
│  │    ├──▶ [Vision Sub-Agent]   Gemini 3.1 Pro (REST) — 帧解析、表情     │
│  │    ├──▶ [OCR Sub-Agent]      Gemini 3 Flash (REST) — 文字读取 [FREE]  │
│  │    ├──▶ [Memory Sub-Agent]   Firestore + embedding-001 — 跨会话记忆   │
│  │    ├──▶ [Face ID Sub-Agent]  InsightFace (ONNX) + Firestore — 人脸    │
│  │    │                                                                   │
│  │    ├── Tools (Function Calling, 异步模式) ──────────────               │
│  │    ├──🔧 navigate_location()  Maps API [FREE]                         │
│  │    ├──🔧 google_search()      Grounding                               │
│  │    └──🔧 identify_person()    → Face ID Sub-Agent (behavior=SILENT)   │
│  │                                                                        │
│  ├── Session: InMemorySessionService (开发初期) → VertexAiSessionService  │
│  ├── Config: min_instance_count=1, timeout=3600s, memory=2Gi, cpu=2      │
│  └── Secret Manager: GOOGLE_API_KEY                                       │
└────────────────────────────┬───────────────────────────────────────────────┘
                             │ WebSocket (WSS, 骨干网)
                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Gemini Live API (v1alpha)                                                 │
│  ├── Model: gemini-2.5-flash-native-audio-preview-12-2025                │
│  ├── Proactive Audio: ON                                                  │
│  ├── Affective Dialog: ON                                                 │
│  ├── Context Window Compression: SlidingWindow (无限时长)                 │
│  ├── Session Resumption: ON (handle 缓存，10min 自动重连)                 │
│  └── VAD: automatic_activity_detection (MEDIUM sensitivity)               │
└────────────────────────────────────────────────────────────────────────────┘

生产级升级路径 (赛后):
  Phone PWA ──WebRTC──→ Pipecat/Daily Edge ──WebSocket──→ Cloud Run ──WSS──→ Gemini
  (UDP 抗弱网)          (全球边缘节点)        (骨干网)                (TCP 缺点被掩盖)
```

### 6.2 编排规则

1. **Single Voice**：只有 Orchestrator 有权和用户"说话"。所有 Sub-Agent 以 JSON/Text 向 Orchestrator 汇报。
2. **极速路由**：Orchestrator 用 Flash 模型做意图判断，按需挂载重量级 Sub-Agent (Vision Pro)。
3. **中断优先级**：Ephemeral Context 触发 PANIC → 任何 Sub-Agent 的任务被即时终止，Orchestrator 切入安全响应。
4. **非阻塞**：Vision 解析耗时 → Orchestrator 先回复 "让我看看..."，异步等待 Vision 结果，再补充完整描述。
5. **人脸匹配并行**：Face ID Sub-Agent 独立运行，通过 Function Calling 将结果注入 Gemini 上下文。**使用 `behavior=SILENT` 模式** — 人脸匹配结果静默存入上下文，不打断当前对话；仅当 Gemini 认为时机合适时才融合到语音输出中。
6. **轻量工具调用**：导航 (`navigate_location`) 和搜索验证 (`google_search`) 作为 Orchestrator 的 Function Calling tools 直接调用，不经过独立 Agent。
7. **Function Calling 异步模式**：Live API 支持三种行为模式：
   - `INTERRUPT`：立即响应（用于安全警报，如 `identify_person` 发现未知人接近）
   - `WHEN_IDLE`：等模型说完话再响应（用于 `navigate_location` 结果）
   - `SILENT`：静默存入上下文（用于 Telemetry 更新、Face ID 背景匹配）
8. **Proactive-Oriented Vision Extraction**（来源：ContextAgent, NeurIPS 2025）：Vision Sub-Agent 的 prompt 必须是 **面向目的的提取**，而非泛泛的场景描述。根据当前 LOD 级别使用不同的 Vision prompt：LOD 1 只提取安全威胁，LOD 2 提取空间导航信息，LOD 3 才做全量描述。论文消融实验证明，proactive-oriented extraction 比 zero-shot 描述在工具选择 F1 上高 3.3%。详见 `Context_Engine_Implementation_Guide.md §6`。
9. **Think-Before-Act LOD 推理**（来源：ContextAgent, NeurIPS 2025）：在 LOD 2/3 场景下，Orchestrator System Prompt 注入轻量 CoT 推理链（`<think>` 标签），让模型先内部推理 LOD 决策再输出。LOD 1 不启用（延迟优先）。论文证明 CoT 在 few-shot 下提升 20.1% 的主动决策准确率。详见 `Context_Engine_Implementation_Guide.md §5.3`。

### 6.3 核心编排伪代码（ADK Bidi-Streaming）

> 参考实现：[google/adk-samples/bidi-demo](https://github.com/google/adk-samples)

```python
# ── server.py ── FastAPI WebSocket → ADK run_live() ──
# 参考: google/adk-samples/bidi-demo + realtime-conversational-agent

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.genai import types
import json, asyncio

# ── ADK Agent 定义 ──
orchestrator = Agent(
    model="gemini-2.5-flash-native-audio-preview-12-2025",
    name="sightline_orchestrator",
    instruction=SYSTEM_PROMPT,              # LOD-Aware Dynamic Prompt
    tools=[identify_person, navigate_location, google_search],
    sub_agents=[vision_pro_agent, face_id_agent, memory_agent],
)
runner = Runner(agent=orchestrator, session_service=InMemorySessionService(),
                app_name="sightline")

# ── Session Resumption Handle 缓存 ──
session_handles: dict[str, str] = {}       # session_id → last_resumption_handle

# ── WebSocket Endpoint ──
@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(ws: WebSocket, user_id: str, session_id: str):
    await ws.accept()

    # RunConfig — 使用 ADK 正确 API (verified against ADK docs)
    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,         # 必须显式指定 BIDI 模式
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
        # Proactive Audio: AI 决定何时主动说话 (参考 ContextAgent, NeurIPS 2025)
        proactivity=types.ProactivityConfig(proactive_audio=True),
        # Affective Dialog: 感知用户情绪并调整语气
        enable_affective_dialog=True,
        # Audio Transcription: 获取实时文字转录 (ADK bidi-demo 标准配置)
        # 用于: 前端字幕、LOD Engine 用户意图分析、Memory Agent 存储
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        # Session Resumption: 10min 连接断开后自动恢复
        session_resumption=types.SessionResumptionConfig(
            handle=session_handles.get(session_id),
        ),
        # Context Window Compression: 突破 2min 音视频限制
        # 音频约 25 tokens/sec (Google Best Practices)
        context_window_compression=types.ContextWindowCompressionConfig(
            trigger_tokens=100000,                    # 100K token 时触发压缩
            sliding_window=types.SlidingWindow(target_tokens=80000),  # 压缩至 80K
        ),
        # VAD: LOD-Adaptive 参数 (默认 MEDIUM, 运行时由 LOD Engine 动态调整)
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                start_of_speech_sensitivity="MEDIUM",
                end_of_speech_sensitivity="MEDIUM",
                prefix_padding_ms=200,
                silence_duration_ms=1000,             # LOD Engine 会动态调整此值
            )
        ),
    )

    live_request_queue = LiveRequestQueue()
    live_events = runner.run_live(
        session_id=session_id,
        user_id=user_id,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )

    # ── Upstream: iOS App → Gemini ──
    async def upstream():
        try:
            while True:
                message = await ws.receive_json()
                if message.get("type") == "audio":
                    import base64
                    audio_data = base64.b64decode(message["data"])
                    audio_blob = types.Blob(
                        mime_type="audio/pcm;rate=16000",
                        data=audio_data,
                    )
                    live_request_queue.send_realtime(audio_blob)  # PCM 16kHz mono
                elif message.get("type") == "image":
                    import base64
                    image_data = base64.b64decode(message["data"])
                    image_blob = types.Blob(
                        mime_type=message.get("mimeType", "image/jpeg"),
                        data=image_data,
                    )
                    live_request_queue.send_realtime(image_blob)  # JPEG frame
                elif message.get("type") == "activity_start":
                    live_request_queue.send_activity_start()      # 手势触发 barge-in
                elif message.get("type") == "activity_end":
                    live_request_queue.send_activity_end()
                elif message.get("type") == "telemetry":
                    # Telemetry 以 text content 注入上下文
                    content = types.Content(
                        parts=[types.Part(
                            text=f"[TELEMETRY UPDATE] {json.dumps(message['data'])}"
                        )]
                    )
                    live_request_queue.send_content(content)
        except WebSocketDisconnect:
            live_request_queue.close()

    # ── Downstream: Gemini → 浏览器 ──
    async def downstream():
        async for event in live_events:
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if part.inline_data:
                        await ws.send_bytes(part.inline_data.data)  # PCM 24kHz
                    elif part.text:
                        await ws.send_json({"type": "text", "text": part.text})
            # Session resumption handle 更新
            if hasattr(event, 'session_resumption_update') and event.session_resumption_update:
                session_handles[session_id] = event.session_resumption_update.handle

    await asyncio.gather(upstream(), downstream())
```

---

### 6.4 Session 生命周期管理

Gemini Live API 基于 WebSocket 长连接，存在三条硬性时间限制：

| 限制 | 阈值 | 触发条件 | 应对策略 |
|------|------|----------|----------|
| **连接生命周期** | ~10 min | 单条 WebSocket 最长存活时间 | `SessionResumptionConfig` — 监听 `GoAway` 信号，缓存 resumption handle，500ms 内自动重连 |
| **Audio+Video 会话** | ~2 min | 同时发送音频+视频流时上下文窗口耗尽 | `ContextWindowCompressionConfig` + `SlidingWindow()` — 自动压缩旧上下文，延长至全生命周期 |
| **Audio-only 会话** | ~15 min | 仅音频流时上下文窗口耗尽 | 同上，启用 `SlidingWindow` 后可覆盖整个连接周期 |

**Session Resumption 流程（5 步）**：

1. **初始连接**：`SessionResumptionConfig(handle=None)` → Gemini 分配新 session
2. **持续缓存**：监听 `session_resumption_update` 事件，实时更新 handle → `session_handles[session_id]`
3. **GoAway 预警**：Gemini 在断连前 ~5s 发送 `GoAway` 信号 → 客户端收到 `{"type": "go_away", "retry_ms": 500}`
4. **快速重连**：客户端 500ms 后重新连接 `/ws/live/{session_id}`，服务端用缓存的 handle 发起 `SessionResumptionConfig(handle=cached_handle)`
5. **透明恢复**：Gemini 恢复完整对话上下文，用户无感知

**Context Window Compression**：启用 `SlidingWindow()` 后，Gemini 会在上下文接近窗口上限时自动压缩早期对话内容（保留关键事实，丢弃冗余turn），使 Audio+Video 会话从 2min 延长至接近连接生命周期上限（~10min）。

---

## 7. 产品个性与 UI 设计

### 7.1 人格定义 (Personality)

SightLine 的 AI 伴侣不是冷冰冰的机器人，而是一个**温暖的、有耐心的朋友**。

| 维度 | 定义 |
|------|------|
| **称呼** | 不叫自己"AI"或"系统"。用第一人称自然对话，像朋友 |
| **语气** | 温暖但不矫情；平静但不冷漠。像一个值得信赖的老朋友在你身边低声描述 |
| **幽默感** | 偶尔有，但不刻意。在 LOD 3 (用户放松时) 可以稍微活泼一些 |
| **在危险时** | 立即切换为简短、坚定、直接。不加修饰，不带情绪，只传递关键信息 |
| **在社交场合** | 像一个懂社交礼仪的助手，低声告诉你关键信息 ("他在微笑"、"她看起来有点着急") |
| **沉默时** | 沉默本身就是一种表达——"我在这里，但我知道你现在不需要我说话" |
| **描述风格** | 现在时 + 第三人称全知视角 + 生动动词优于平淡动词+副词 (Describe Now, ASSETS 2024) |

**System Instruction 结构** (Google Vertex AI Best Practices 推荐顺序)：

```
1. Agent Persona — 名字、角色、性格特征
   "You are SightLine, a warm and patient companion for a blind user..."

2. Conversational Rules (按优先级排列)
   - LOD 动态规则 [由 LOD Engine 注入]
   - 用户个性化规则 [由 vision_status/偏好注入]
   - 描述规范: present tense, third-person, vivid verbs
   - RESPOND IN ENGLISH. YOU MUST RESPOND UNMISTAKABLY IN ENGLISH.

3. Guardrails
   - 不评判用户行为
   - 不提供医疗建议
   - 检测到危险时停止所有非安全相关输出
```

**为什么这个顺序很重要**：Google 官方推荐 persona → rules → guardrails 这个顺序，因为模型对 System Instruction 的前半部分注意力最高。Persona 放在最前确保 AI 人格最稳定。

### 7.2 UI 设计

**极简原则**：全屏是一个巨大的触控区。不需要精确瞄准任何 UI 元素。

```
┌─────────────────────────────────┐
│                                 │
│    ┌───────────────────────┐    │
│    │                       │    │
│    │    全屏触控区域         │    │
│    │    (整个屏幕都是按钮)   │    │
│    │                       │    │
│    │        ● 呼吸灯        │    │
│    │      (彩色渐变)        │    │
│    │                       │    │
│    └───────────────────────┘    │
│                                 │
└─────────────────────────────────┘
   背景色随 LOD 状态柔和变化:
   LOD 1 = 深蓝 (安静/安全)
   LOD 2 = 暖橙 (探索中)
   LOD 3 = 柔白 (全量描述)
```

**彩色设计的意义**：即便用户看不见，他们可能通过家人转述、或残存视力感知到颜色变化。这是温情的设计细节——一个为看不见的人设计的彩色世界。如果在 Demo 中被评委注意到，会成为一个小的 "Aha Moment"。

**交互手势** (详见 `SightLine_Voice_Interaction_UX_Research.md` §2.2)：

| 手势 | 动作 | 触觉反馈 |
|------|------|----------|
| **单击** (anywhere) | 静音/取消静音麦克风 | 短震 1 次 |
| **双击** (anywhere) | 强制打断 Agent 说话 | 短震 2 次 |
| **三击** (anywhere) | 重复上一句 | 短震 3 次 |
| **长按 3s** | 紧急暂停 — 全系统静音 | 长震 |
| **上滑** | LOD 升级 (说更多) | 上升音效 |
| **下滑** | LOD 降级 (说更少) | 下降音效 |
| **摇一摇** | SOS 紧急求助 | 连续震动 |

**启动流程**：
- 打开 App → 自动启动 (不需要登录/注册流程)
- NWConnection 自动连接 WebSocket → Cloud Run → Gemini Live API
- 自动开启麦克风 (AVAudioEngine) + 摄像头 (AVCaptureSession)
- 自动防息屏 (UIApplication.isIdleTimerDisabled)
- 系统的 Proactive Audio 自动决定何时说话，中央呼吸灯效果指示状态

**技术实现**：
- 双击打断 = UITapGestureRecognizer (2 taps) → 发送 `activity_start` 信号触发 Gemini barge-in
- 上/下滑 = UISwipeGestureRecognizer (.up/.down) → 注入 Telemetry: `{"user_gesture": "lod_up/lod_down"}`
- 触觉反馈 = UIImpactFeedbackGenerator / UINotificationFeedbackGenerator (iOS 原生触觉引擎)

### 7.3 Affective Dialog 配置

利用 Gemini Live API 的 Affective Dialog 能力 (需 `v1alpha` API，底层模型已 GA)：

| 场景 | 语调配置 |
|------|---------|
| 用户平静行走 | 低沉、简短 |
| 用户坐下探索 | 温暖、从容、稍微详细 |
| 用户手持文件阅读 | 清晰、有节奏、像朗读者 |
| 检测到熟人 | 轻快、低声 ("嘿，David 来了") |
| 用户心率飙升 (紧张) | 沉稳、安抚、极简 |
| 用户在社交场合 | 低声耳语般，不抢用户社交注意力 |

#### 7.3.1 Proactive Audio 多维上下文融合策略

> **来源**: ContextAgent (NeurIPS 2025) — "assist users unobtrusively"

不要让 Proactive Audio "随便说话"。应基于多维传感器上下文融合来决定是否主动说话：

| 信号 | 优先级 | 行为 | 理由 |
|------|--------|------|------|
| 环境突变 (新人出现、车辆接近) | 🔴 最高 | 立即说 | 安全 |
| 用户正在移动 (步频检测) | 🟠 高 | 主动播报导航 | 任务相关 |
| 用户问题后沉默 | 🟡 中 | 0.8s 后补充 | 对话自然性 |
| 环境平稳无变化 | 🟢 低 | 保持沉默 | 知趣地闭嘴 |
| 用户处于社交场景 | 🟢 低 | 等待被问 | 不打扰社交 |

**技术实现**: Gemini 2.5 Flash Native Audio 已原生支持 "distinguish between the speaker and background conversations" (嘈杂环境说话人识别, Newo.ai 生产验证)。Proactive Audio 的触发逻辑由 Gemini 模型内部决策，我们通过 System Prompt 中的优先级规则引导。

---

## 8. 技术栈与部署

### 8.1 完整技术栈

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **AI Model (Live/Orchestrator)** | Gemini 2.5 Flash Native Audio (Live API 仅支持 2.5) | 实时路由 + 语音对话 |
| **AI Model (Vision)** | Gemini 3.1 Pro (`gemini-3.1-pro-preview`) | 深度视觉理解 (最强推理) |
| **AI Model (Sub-agents)** | Gemini 3 Flash (`gemini-3-flash-preview`) — **FREE** | OCR、导航、Grounding 等 |
| **Embeddings** | `gemini-embedding-001` (GA, native 3072d → truncated to 2048d for Firestore max) | 替代已废弃的 text-embedding-004 |
| **Agent Framework** | Google ADK (Python) — `run_live()` bidi-streaming | Multi-agent 编排 + 实时双向流 |
| **Live Streaming** | Gemini Live API (WebSocket, v1alpha) | 实时双向音视频 |
| **Session Management** | `SessionResumptionConfig` + `ContextWindowCompressionConfig` | 10min 重连、2min 压缩、GoAway 处理 |
| **Audio Pipeline** | AVAudioEngine (capture, PCM 16kHz) + AVAudioPlayerNode (playback, PCM 24kHz) | iOS 原生音频采集与播放 |
| **Face Recognition** | InsightFace (buffalo_l, ONNX) | 人脸库匹配 (99.83% LFW, 独立 pipeline) |
| **Backend** | Cloud Run + FastAPI + ADK (`min_instances=1`, `timeout=3600s`) | WebSocket 长连接代理，无冷启动 |
| **Database** | Firestore | 用户偏好、人脸库、记忆图谱 |
| **Search/Grounding** | Google Search API | 品牌/产品/地点验证，减少幻觉 |
| **Maps** | Google Maps API + Geocoding | 位置感知、POI |
| **Frontend** | Swift Native iOS (AVFoundation + CoreMotion + HealthKit + NWConnection) + watchOS Companion App | iPhone 摄像头/麦克风/传感器接入 + Apple Watch 心率 |
| **Infrastructure** | Terraform + Cloud Build + Secret Manager | 自动化部署 + API Key 安全存储 (+0.2 加分) |
| **Monitoring** | Cloud Logging | 调试和监控 |

### 8.2 项目结构

```
sightline/
├── agents/                          # Python 后端 (Cloud Run)
│   ├── orchestrator.py
│   ├── vision_agent.py
│   ├── ocr_agent.py
│   ├── memory_agent.py
│   └── face_id_agent.py
├── tools/
│   ├── navigate_location.py
│   └── google_search.py
├── lod/
│   ├── lod_engine.py
│   ├── context_fusion.py
│   ├── narrative_tracker.py
│   └── signal_detector.py
├── face/
│   ├── face_library.py
│   └── face_pipeline.py
├── live_api/
│   ├── session_manager.py
│   ├── proactive_logic.py
│   └── stream_handler.py
├── telemetry/
│   ├── telemetry_parser.py
│   └── simulator.py
├── ios/                             # Swift Native iOS App
│   ├── SightLine/
│   │   ├── App/
│   │   │   ├── SightLineApp.swift
│   │   │   └── AppDelegate.swift
│   │   ├── Core/
│   │   │   ├── WebSocketManager.swift      # NWConnection WebSocket
│   │   │   ├── MessageProtocol.swift
│   │   │   └── Config.swift
│   │   ├── Audio/
│   │   │   ├── AudioCaptureManager.swift   # AVAudioEngine 麦克风
│   │   │   ├── AudioPlaybackManager.swift  # AVAudioPlayerNode 播放
│   │   │   └── AudioSessionManager.swift
│   │   ├── Camera/
│   │   │   ├── CameraManager.swift         # AVCaptureSession → JPEG
│   │   │   └── FrameSelector.swift
│   │   ├── Sensors/
│   │   │   ├── SensorManager.swift
│   │   │   ├── MotionManager.swift         # CMMotionActivity + CMPedometer
│   │   │   ├── LocationManager.swift       # CLLocationManager
│   │   │   ├── WatchReceiver.swift         # WCSession 接收心率
│   │   │   ├── HealthKitManager.swift
│   │   │   ├── NoiseMeter.swift
│   │   │   └── TelemetryAggregator.swift
│   │   ├── Interaction/
│   │   │   ├── GestureHandler.swift        # 全屏手势
│   │   │   └── HapticEngine.swift          # 触觉反馈
│   │   └── UI/
│   │       ├── MainView.swift              # 全屏黑色界面
│   │       ├── StatusOverlay.swift
│   │       └── DebugOverlay.swift
│   └── SightLineWatch/                     # watchOS 心率 App (~500-680 行)
│       ├── SightLineWatchApp.swift
│       ├── WorkoutManager.swift
│       ├── PhoneConnector.swift
│       └── ContentView.swift
├── infrastructure/
│   ├── Dockerfile
│   ├── cloudbuild.yaml
│   ├── terraform/
│   └── deploy.sh
├── tests/
├── architecture_diagram.png
└── README.md
```

---

## 9. Demo 视频脚本 (4 分钟)

### 9.1 脚本结构

| 时间 | 内容 | 展示要点 | 屏幕画面 |
|------|------|---------|---------|
| 0:00-0:25 | **情感钩子** "全球 2.85 亿人视力受损。白手杖告诉他们前面有墙，但无法告诉他们墙上贴着什么。" | 建立共情 | 统计数据 + 盲人日常场景 |
| 0:25-0:50 | **产品介绍** "SightLine 不是雷达，是语义翻译官。我们的核心创新：Adaptive LOD — AI 知道何时说话、说多少、何时闭嘴。" | LOD 概念 | 架构图快闪 |
| 0:50-1:10 | **LOD 1 演示 — 行走中** 用户在走路，AI 完全静默。评委看到 Developer Console 显示步频数据。仅偶尔一句："前方是十字路口。" | 静默 = 安全设计 | 手机屏幕 (一个按钮 + 深蓝色) + Developer Console |
| 1:10-1:50 | **LOD 2 演示 — 超市探索** 用户停下脚步，AI 感知步频归零，自动升级到 LOD 2："你正面对饮料区，左手边是可乐，右手边是果汁。" | 自动 LOD 切换 | 摄像头画面 + UI 变暖橙色 |
| 1:50-2:30 | **LOD 3 演示 — 坐下阅读** 用户坐下，手持菜单。AI 进入全量描述模式，逐条朗读菜单。**中途用户打断："旁边什么声音？"** AI 瞬间中断，LOD 降级回答 "有人拉开了椅子"，然后精准从中断点恢复朗读。 | Narrative Snapshot + 打断恢复 | 菜单 OCR 画面 + UI 变柔白 |
| 2:30-2:55 | **人脸识别演示** 摄像头看到一个人走来。AI："David 在向你走来，看起来心情不错。" 评委看到 Developer Console 显示 face match 结果。 | 温情时刻 | 人脸检测 overlay + match 信息 |
| 2:55-3:15 | **Grounding 演示** 用户问 "这是什么牌子的咖啡？" AI 通过 Vision + Google Search Grounding 回答真实品牌名称和简介。 | 防幻觉 | Google Search 调用日志 |
| 3:15-3:45 | **技术深度** 展示：(1) ADK 多 Agent 架构图 (2) Google Cloud Console — Cloud Run 运行中 (3) Firestore 数据 (4) Developer Console 传感器面板 | 满足技术评分 | GCP Console 截图 |
| 3:45-4:00 | **收尾** "We didn't build a radar. We built a semantic interpreter that knows when to speak, when to listen, and when to stay silent. SightLine — seeing the world, together." | 记忆点 | Logo + tagline |

### 9.2 Demo Wow Moments

1. **LOD 自动切换**：用户从走路到停下，AI 从沉默到主动描述，无需任何指令。
2. **Narrative Snapshot**：打断后精准恢复，证明系统有"记忆"。
3. **人脸识别**：识别出熟人并自然地融入描述，温暖有人情味。
4. **Developer Console**：让评委直观看到传感器数据如何影响 AI 行为。

---

## 10. 评分策略逐项攻略

### 10.1 Innovation & Multimodal UX (40%)

| 评分要素 | SightLine 对应 | 预估得分 |
|---------|---------------|---------|
| 打破"文本框"范式 | 视障用户**根本无法使用**文本界面 — 最彻底的"打破" | 5/5 |
| 看/听/说无缝整合 | 摄像头看 + 麦克风听 + 语音说 = 三模态同步 | 5/5 |
| 独特的人格/声音 | 温暖朋友型 AI，利用 Affective Dialog 动态调整语气 | 4/5 |
| 上下文感知的实时交互 | LOD + Context Fusion + Proactive Audio | 5/5 |

**杀手锏**：利用 Gemini 两个独有功能 — **Proactive Audio** (AI 智能决定何时说话) + **Affective Dialog** (根据情境调整语气)。竞争对手无法复制。

### 10.2 Technical Implementation (30%)

| 评分要素 | SightLine 对应 | 预估得分 |
|---------|---------------|---------|
| SDK/ADK 有效利用 | ADK 层级化多 Agent + Live API | 5/5 |
| 稳健的 Google Cloud 托管 | Cloud Run + Firestore + Cloud Logging (5+ GCP 服务) | 5/5 |
| 健全的 Agent 逻辑 | LOD 状态机 + 中断处理 + 叙事恢复 | 4/5 |
| 防幻觉与 Grounding | Google Search Grounding Agent | 4/5 |
| 优雅的错误处理 | 摄像头遮挡/网络中断降级策略 | 4/5 |

### 10.3 Demo & Presentation (30%)

| 评分要素 | SightLine 对应 | 预估得分 |
|---------|---------------|---------|
| 清晰的问题/方案定义 | 2.85 亿视障人群 + 信息剥夺痛点 (25 秒内讲清) | 5/5 |
| 可读架构图 | 专业的多 Agent 拓扑图 | 4/5 |
| Cloud 部署证明 | GCP Console 截图/录屏 | 5/5 |
| 实际软件演示 | 4 个场景全部真实运行 | 5/5 |

### 10.4 加分项 (+1.0)

| 加分项 | 分值 | 执行 |
|--------|------|------|
| 技术博客 (Medium + Dev.to) | +0.6 | 第 4 周写：标题 "Building an Adaptive LOD Engine for the Blind with Gemini Live API" |
| Terraform 自动化部署 | +0.2 | `terraform/` 目录 + `deploy.sh` |
| GDG 会员 | +0.2 | 立即注册 gdg.community.dev |

---

## 11. 开发时间线 (23 天)

### Week 1 (2/22 - 2/28): 核心骨架

- [ ] 项目初始化：ADK + Cloud Run + Firestore
- [ ] Gemini Live API WebSocket 连接建立
- [ ] Orchestrator Agent 基础框架 (意图分类 + 路由)
- [ ] LOD Engine 基础版 (3 级固定切换)
- [ ] WebRTC 前端骨架 (手机摄像头 + 麦克风)
- [ ] 部署到 GCP (尽早验证)
- [ ] 加入 GDG

### Week 2 (3/1 - 3/7): 核心 Agent 开发

- [ ] Vision Sub-Agent (场景描述)
- [ ] OCR Sub-Agent (文字读取)
- [ ] navigate_location tool (Google Maps Function Calling 集成)
- [ ] Face ID Sub-Agent (人脸库注册 + 匹配)
- [ ] Proactive Audio 逻辑
- [ ] Affective Dialog 配置
- [ ] google_search tool (Gemini 内置 Grounding Function Calling)
- [ ] Context Fusion 算法 (三层上下文融合)

### Week 3 (3/8 - 3/12): 打磨与集成

- [ ] Memory Sub-Agent (跨会话记忆)
- [ ] Narrative Snapshot (打断恢复)
- [ ] Developer Console (遥测模拟器)
- [ ] 极简 UI (单按钮 + 色彩变化)
- [ ] 端到端测试
- [ ] 延迟优化
- [ ] 错误处理完善

### Week 4 (3/13 - 3/16): Demo & 提交

- [ ] 3/13: 录制 Demo 视频
- [ ] 3/14: 制作架构图
- [ ] 3/14: 撰写项目描述 + README
- [ ] 3/14: Terraform 部署脚本
- [ ] 3/15: 发布技术博客 (Medium + Dev.to)
- [ ] 3/15: 最终检查 & 提交
- [ ] 3/16: 缓冲日

---

## 12. 风险与缓解

| 风险 | 严重性 | 缓解策略 |
|------|--------|---------|
| Gemini Live API 延迟过高 (> 3s) | 高 | 非阻塞编排：Orchestrator 先说"让我看看"，异步等待结果 |
| **WebSocket ~10min 硬断连** | **高** | `SessionResumptionConfig` — 监听 `GoAway` 信号，缓存 resumption handle，500ms 自动重连，用户无感知（见 §6.4） |
| **Audio+Video 2min 上下文耗尽** | **高** | `ContextWindowCompressionConfig` + `SlidingWindow()` — 自动压缩旧上下文，延长至 ~10min（见 §6.4） |
| 人脸识别准确率不够 | 中 | Demo 中用提前注册的人，控制环境光线 |
| ~~iOS PWA standalone 模式 `getUserMedia` 不可用~~ | **已解决** | 已迁移到 Swift Native iOS App，消除所有 PWA 致命缺陷 |
| Developer Console 传感器模拟不够直观 | 中 | 用大号滑块 + 实时数据可视化，让评委一眼看懂 |
| 评委质疑安全性 | 中 | 明确声明不替代白手杖；LOD 1 只提供宏观语义，不做微观导航 |
| 评委质疑隐私 | 低 | 提交材料中写明人脸库设计：仅 embedding、用户主动注册、可删除 |
| 时间不够 | 高 | 优先级排序：LOD + Vision + Demo > Face ID > Memory > Grounding |

### 12.1 砍功能优先级 (如果时间不够)

| 优先级 | 功能 | 说明 |
|--------|------|------|
| **P0 — 必须有** | LOD Engine (3 级) + Orchestrator + Vision Agent + iOS App (AVFoundation + NWConnection WebSocket) | 没有这些就没有产品 |
| **P0 — 必须有** | Demo 视频 + 架构图 + GCP 部署 | 没有这些无法提交 |
| **P1 — 强烈需要** | Proactive Audio + Affective Dialog | 这是 Gemini 独有功能的展示，直接影响 40% 权重的评分 |
| **P1 — 强烈需要** | OCR Agent + google_search tool (Grounding) | Demo 中需要读文字和验证信息 |
| **P2 — 非常想要** | Face ID Agent (人脸库) | 温情亮点，但非核心 |
| **P2 — 非常想要** | Developer Console (遥测模拟器) | 向评委展示传感器驱动的证据 |
| **P3 — 锦上添花** | Memory Agent (跨会话记忆) | 在 4 分钟 Demo 中难以展示 |
| **P3 — 锦上添花** | Narrative Snapshot (打断恢复) | 精彩但复杂，时间不够就砍 |

---

## 13. Pitch 核心话术

### 英文 (给评委)

> "When building for the visually impaired, the industry makes a fatal mistake: trying to replace the white cane with AI. But a 2-second cloud latency is deadly when crossing a street.
>
> We didn't build a radar. We built a **Semantic Interpreter**.
>
> Our core innovation is **Adaptive Level-of-Detail**. SightLine knows when you are moving and stays absolutely silent — because your ears need to hear traffic, not AI chatter. But when you sit down at a café, it unleashes the full power of Gemini Vision to read the menu, describe the room, and tell you your friend Sarah just walked in with a smile.
>
> We fuse heart rate, step cadence, and spatial context into a real-time Context Awareness engine that drives every word the AI says — or chooses not to say.
>
> We embrace the engineering limits of cloud AI, and we use brilliant software architecture to work around them."

### 中文 (内部理解)

> "我们的 AI 懂得知趣地闭嘴。它不是一个无脑的描述机器，而是一个有上下文意识的伴侣——它知道你在走路就安静下来让你听路，知道你坐下来了就打开全量描述，知道你的朋友来了就轻声告诉你。这就是自适应 LOD 和上下文感知的结合。"

---

## 14. 提交物清单

| 提交项 | 状态 | 负责 |
|--------|------|------|
| Devpost 文字描述 (项目摘要、功能、技术栈) | 待完成 | Week 4 |
| GitHub 公开仓库 (含 README + spin-up 指令) | 待完成 | 持续更新 |
| Google Cloud 部署证明 (Console 截图/录屏) | 待完成 | Week 4 |
| 架构图 (可视化系统图) | 待完成 | Week 4 |
| Demo 视频 (4 分钟内) | 待完成 | Week 4 |
| 技术博客 (Medium + Dev.to) | 待完成 | Week 4 (+0.6) |
| Terraform 部署脚本 | 待完成 | Week 3 (+0.2) |
| GDG 会员注册 | 待完成 | **立即** (+0.2) |

---

## 15. 与前序文档的关系

本文档是以下所有文档的**最终综合定稿**：

| 前序文档 | 本文档对应章节 |
|---------|---------------|
| `SightLine 产品战略重构.md` | §1 产品定位、§2 LOD 系统、§13 Pitch 话术 |
| `SightLine 核心架构_ Agent编排与上下文建模.md` | §3 Context Awareness、§6 Agent 编排 |
| `SightLine 硬件形态与极简部署策略.md` | §5 硬件无关性、§8 技术栈 |
| `SightLine 竞品交叉验证与产品价值评估.md` | §10 评分策略 (基于竞品验证的差异化定位) |
| `Gemini_Live_Agent_Challenge_Deep_Research.md` | §10 评分策略、§11 时间线 |
| `Gemini_Live_Agent_Challenge_Strategy.md` | §9 Demo 脚本、§11 时间线、§14 提交物清单 |
| **新增研究：硬件协议调研** | §5.2 SEP 协议精简版、§5.3 MediaMTX 中继 |
| **新增研究：人脸识别技术调研** | §4 人脸库完整设计 |

---

*本文档为 SightLine 项目的最终技术与产品规格书。所有后续开发工作以本文档为准。*
