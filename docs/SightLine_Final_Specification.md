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
   - 实时心率 / HRV (若可用)
   - 步频 (若可用)
   - 头部转动频率 (若可用)
   - 用户语音打断信号

2. 读取会话期上下文 (Session):
   - 用户今天的出行目的 ("我要去面试")
   - 当前空间类型 (室内/室外/交通工具)
   - 近 N 分钟步频均值
   - 当前对话话题和叙事位置

3. 读取长期上下文 (Long-term):
   - 用户偏好 (语速、详细程度偏好)
   - 已知人脸库
   - 常去地点
   - 历史压力触发器

4. 融合决策:
   - 如果 Ephemeral 触发 PANIC → 强制 LOD 1，清空播放队列
   - 否则加权融合三层 Context，计算目标 LOD
   - 平滑过渡 (避免频繁跳级)
```

### 2.3 "知趣地闭嘴" 设计原则

这是 LOD 的灵魂。实现要点：

- **默认偏向静默**：没有充分理由不说话。LOD 1 不等于"少说"，等于"几乎不说"。
- **说话有成本**：系统内部给每次发声分配一个"认知成本"分数，当用户物理活动水平高时，成本阈值大幅提高，只有高价值信息才能突破阈值。
- **打断即降级**：用户任何时候说"停"或物理状态变化 (开始走路)，立即降级。
- **恢复有记忆**：LOD 降级时保存叙事快照 (Narrative Snapshot)。当条件恢复后，AI 从中断点继续，而不是从头开始。

---

## 3. Context Awareness 多维上下文建模

### 3.1 上下文数据源与生命周期

| 层级 | 时间尺度 | 数据源 | 用途 |
|------|---------|--------|------|
| **Ephemeral** | 毫秒~秒 | 视频帧、音频打断、心率突变、陀螺仪剧烈晃动 | 最高中断优先级；危险信号立即清空 TTS 队列 |
| **Session** | 分钟~小时 | 出行目的、空间类型、步频均值、对话历史 | 维持系统平稳运行；例如知道用户"正在喝咖啡"→ LOD 稳定在 3 |
| **Long-term** | 跨会话 | Firestore 存储：用户偏好、人脸库、常去地点、压力触发器 | 个性化；让 AI 越来越"懂"用户 |

### 3.2 Hackathon 中的 Context 输入方式

| 数据类型 | Hackathon 实现 | 生产级实现 |
|---------|---------------|-----------|
| 视频流 | 手机摄像头 via WebRTC (PWA) | 智能眼镜、胸前摄像头 via SEP-Vision |
| 音频 | 手机麦克风 via WebRTC | 骨传导耳机、助听器 via SEP-Audio |
| 心率 | Developer Console 滑块模拟注入 | Apple Watch / 运动手环 via SEP-Telemetry |
| 步频 | Developer Console 滑块模拟注入 | 手表计步器 / 鞋垫传感器 |
| 头部转动 | Developer Console 模拟注入 | AirPods Pro IMU / 耳机 IMU |
| 地理位置 | 手机 GPS (真实) | 同左 + 更精确的 UWB 定位 |

**Developer Console 设计**：Web 界面上的公开透明传感器控制台，通过滑块和按钮按照 SEP-Telemetry JSON 协议向云端持续注入数据。在 Demo 中向评委展示这个控制台，证明：(1) 云端 Agent 是 100% 真实运行的，(2) 只要硬件按协议发送数据就能即插即用。

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
Face Detection (ML Kit / OpenCV)                          │  "relationship": "boss"}
     │                                                    │
     ▼                                                    │
Face Embedding (face_recognition / ArcFace)               │
     │                                                    │
     ▼                                                    │
Cosine Similarity Match vs Library ──── if match ────────>┘
```

#### 注册流程 (由视力正常的亲属操作)

1. 拍照 → 人脸检测 → 裁剪对齐
2. 生成 128 维 face embedding (使用 `face_recognition` 库或 FaceNet)
3. 存入数据库：
```json
{
  "person_id": "uuid",
  "name": "David",
  "relationship": "boss",
  "embedding": [0.023, -0.114, ...],
  "registered_by": "user_wife",
  "created_at": "2026-02-21T10:00:00Z"
}
```
4. 每人存储 3-5 张不同角度/光线的 embedding 以提高识别率。

#### 实时匹配流程

1. 从视频流中抽帧 (1-2 FPS 足够)
2. 人脸检测 → 找到所有人脸 bounding box
3. 对每张脸生成 embedding
4. 与库中所有 embedding 计算 cosine similarity
5. 若 max_similarity > 0.6 → 匹配成功
6. 将匹配结果通过 Function Calling 返回给 Gemini：
   - Gemini 调用 `identify_person` tool
   - 返回 `{"name": "David", "relationship": "boss"}`
   - Gemini 融合视觉描述 + 身份信息，生成自然语言："你的老板 David 走过来了，看起来心情不错。"

#### Hackathon MVP 实现

| 组件 | 技术选择 | 理由 |
|------|---------|------|
| 人脸检测+嵌入 | `face_recognition` (Python, pip install) | 一行代码生成 encoding，最简 API |
| 人脸库存储 | Firestore (JSON 文档) | 和其他数据存储统一；50 人以内 brute-force 匹配 < 1ms |
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
| **WebRTC (Opus)** | 所有设备 (浏览器抽象了蓝牙层) | 浏览器的 `getUserMedia()` 自动处理 HFP/A2DP 蓝牙协商 |
| HFP (Hands-Free Profile) | 所有蓝牙耳机、助听器、骨传导 | 双向单声道 8-16kHz，语音 AI 完全够用 |

**关键洞察**：不需要写任何蓝牙协议代码。WebRTC 在浏览器层已经抽象掉了蓝牙细节。用户连什么蓝牙设备，浏览器会自动用 HFP 建立双向音频通道。

#### SEP-Telemetry (遥测通道)

标准化 JSON 格式：
```json
{
  "timestamp": "2026-02-21T10:30:00Z",
  "heart_rate": 78,
  "hrv_ms": 45,
  "step_cadence": 0,
  "head_yaw_rate": 12.5,
  "gps": { "lat": 37.7749, "lng": -122.4194 },
  "device_type": "simulation_console"
}
```

Hackathon 中：Developer Console 发送模拟数据。
赛后：Apple Watch / 可穿戴设备通过 companion app 发送真实数据。

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

### 6.1 层级化子智能体 (Hierarchical Sub-Agent)

```
[SEP API Gateway (WebRTC + Telemetry JSON)]
         │
         ▼
【Orchestrator Agent】←── Adaptive LOD Engine
  │  (Gemini 2.5 Flash Native Audio — Live API 仅支持 2.5)
  │
  ├──▶ [Vision Sub-Agent]     Gemini 3.1 Pro — 帧解析、场景描述、表情识别
  ├──▶ [OCR Sub-Agent]        Gemini 3 Flash — 文字/标签/菜单/药品读取 [FREE]
  ├──▶ [Memory Sub-Agent]     Firestore + gemini-embedding-001 — 跨会话偏好读写、人脸库查询
  ├──▶ [Face ID Sub-Agent]    InsightFace (ONNX) + Firestore — 人脸匹配
  │
  ├── Tools (Function Calling) ──────────────────────────
  ├──🔧 navigate_location()   Gemini 3 Flash + Google Maps API — 位置、方向、POI [FREE]
  └──🔧 google_search()       Gemini 内置 Grounding — 验证品牌/产品/地点信息
```

### 6.2 编排规则

1. **Single Voice**：只有 Orchestrator 有权和用户"说话"。所有 Sub-Agent 以 JSON/Text 向 Orchestrator 汇报。
2. **极速路由**：Orchestrator 用 Flash 模型做意图判断，按需挂载重量级 Sub-Agent (Vision Pro)。
3. **中断优先级**：Ephemeral Context 触发 PANIC → 任何 Sub-Agent 的任务被即时终止，Orchestrator 切入安全响应。
4. **非阻塞**：Vision 解析耗时 → Orchestrator 先回复 "让我看看..."，异步等待 Vision 结果，再补充完整描述。
5. **人脸匹配并行**：Face ID Sub-Agent 独立运行，通过 Function Calling 将结果注入 Gemini 上下文。
6. **轻量工具调用**：导航 (`navigate_location`) 和搜索验证 (`google_search`) 作为 Orchestrator 的 Function Calling tools 直接调用，不经过独立 Agent。

### 6.3 核心编排伪代码

```python
async def process_input(input_stream, telemetry):
    # 1. Context Loading
    user_profile = await MemoryAgent.fetch_profile(user_id)
    current_lod = LODManager.get_current_level()

    # 2. Telemetry Interrupt Check
    if telemetry.is_panic():  # 心率 > 120 或步频突变
        LODManager.force_downgrade(level=1)
        return Orchestrator.safety_response()

    # 3. LOD-Aware Routing
    intent = await IntentClassifier.analyze(input_stream)

    if intent in ["read_text", "describe_scene"]:
        vision_ctx = await VisionAgent.analyze(camera_buffer)
    if intent == "who_is_this":
        face_ctx = await FaceIDAgent.identify(camera_buffer)
    if intent == "where_am_i":
        geo_ctx = await tools.navigate_location(gps=telemetry.gps)

    # 4. Context Fusion → Dynamic Prompt
    system_prompt = build_prompt(
        lod=current_lod,
        memory=user_profile,
        vision=vision_ctx,
        face=face_ctx,
        geo=geo_ctx
    )

    # 5. Gemini Live Streaming Output
    async for audio_chunk in GeminiLive.stream(system_prompt, input_stream):
        yield audio_chunk

    # 6. Async Memory Consolidation
    asyncio.create_task(
        MemoryAgent.save_new_facts(conversation_history)
    )
```

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

### 7.2 UI 设计

**极简原则**：全屏只有一个按钮。

```
┌─────────────────────────────────┐
│                                 │
│                                 │
│                                 │
│           ┌───────┐             │
│           │       │             │
│           │   ●   │  ← 主按钮   │
│           │       │    (彩色渐变)│
│           └───────┘             │
│                                 │
│     按住说话 / 点击暂停/恢复     │
│                                 │
└─────────────────────────────────┘
   背景色随 LOD 状态柔和变化:
   LOD 1 = 深蓝 (安静/安全)
   LOD 2 = 暖橙 (探索中)
   LOD 3 = 柔白 (全量描述)
```

**彩色设计的意义**：即便用户看不见，他们可能通过家人转述、或残存视力感知到颜色变化。这是温情的设计细节——一个为看不见的人设计的彩色世界。如果在 Demo 中被评委注意到，会成为一个小的 "Aha Moment"。

**交互逻辑**：
- 打开 App → 自动启动 (不需要登录/注册流程)
- 按住按钮 = Push-to-talk (主动提问)
- 系统也会主动说话 (Proactive Audio)，按钮区域会有柔和的呼吸灯效果
- 长按 3 秒 = 紧急暂停 (全静音)
- 双击 = 重复上一句

### 7.3 Affective Dialog 配置

利用 Gemini Live API 的 Affective Dialog 能力：

| 场景 | 语调配置 |
|------|---------|
| 用户平静行走 | 低沉、简短 |
| 用户坐下探索 | 温暖、从容、稍微详细 |
| 用户手持文件阅读 | 清晰、有节奏、像朗读者 |
| 检测到熟人 | 轻快、低声 ("嘿，David 来了") |
| 用户心率飙升 (紧张) | 沉稳、安抚、极简 |
| 用户在社交场合 | 低声耳语般，不抢用户社交注意力 |

---

## 8. 技术栈与部署

### 8.1 完整技术栈

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **AI Model (Live/Orchestrator)** | Gemini 2.5 Flash Native Audio (Live API 仅支持 2.5) | 实时路由 + 语音对话 |
| **AI Model (Vision)** | Gemini 3.1 Pro (`gemini-3.1-pro-preview`) | 深度视觉理解 (最强推理) |
| **AI Model (Sub-agents)** | Gemini 3 Flash (`gemini-3-flash-preview`) — **FREE** | OCR、导航、Grounding 等 |
| **Embeddings** | `gemini-embedding-001` (GA, 3072 dims) | 替代已废弃的 text-embedding-004 |
| **Agent Framework** | Google ADK (Python) | Multi-agent 编排 |
| **Live Streaming** | Gemini Live API (WebSocket, v1alpha) | 实时双向音视频 |
| **Face Recognition** | InsightFace (buffalo_l, ONNX) | 人脸库匹配 (99.83% LFW, 独立 pipeline) |
| **Backend** | Cloud Run (Serverless) | 无服务器部署 |
| **Database** | Firestore | 用户偏好、人脸库、记忆图谱 |
| **Search/Grounding** | Google Search API | 品牌/产品/地点验证，减少幻觉 |
| **Maps** | Google Maps API + Geocoding | 位置感知、POI |
| **Frontend** | React PWA (WebRTC) | 手机摄像头/麦克风接入 |
| **Infrastructure** | Terraform + Cloud Build | 自动化部署 (+0.2 加分) |
| **Monitoring** | Cloud Logging | 调试和监控 |

### 8.2 项目结构

```
sightline/
├── agents/
│   ├── orchestrator.py        # 中央调度 + LOD Engine
│   ├── vision_agent.py        # 场景理解 (Gemini Pro Vision)
│   ├── ocr_agent.py           # 文字/标签读取
│   ├── memory_agent.py        # 跨会话记忆读写
│   └── face_id_agent.py       # 人脸库匹配 (face_recognition)
├── tools/
│   ├── navigate_location.py   # Google Maps API + Geocoding (Function Calling tool)
│   └── google_search.py       # Google Search Grounding (Function Calling tool)
├── lod/
│   ├── lod_engine.py          # 自适应 LOD 核心算法
│   ├── context_fusion.py      # 三层 Context 融合
│   ├── narrative_tracker.py   # 叙事位置追踪 + 快照恢复
│   └── signal_detector.py     # 用户意图信号检测
├── face/
│   ├── face_library.py        # 人脸注册/存储/匹配
│   └── face_pipeline.py       # 实时帧人脸检测+匹配 pipeline
├── live_api/
│   ├── session_manager.py     # Gemini Live API WebSocket 管理
│   ├── proactive_logic.py     # 主动发声决策
│   └── stream_handler.py      # 音视频流处理
├── telemetry/
│   ├── telemetry_parser.py    # SEP-Telemetry JSON 解析
│   └── simulator.py           # Developer Console 模拟器
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # 极简单按钮 UI
│   │   ├── WebRTCClient.ts    # WebRTC 音视频连接
│   │   ├── TelemetryConsole.tsx  # Developer Console (模拟器)
│   │   └── LODIndicator.tsx   # LOD 状态色彩指示
│   ├── public/
│   └── package.json
├── infrastructure/
│   ├── Dockerfile
│   ├── cloudbuild.yaml        # CI/CD pipeline
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── cloud_run.tf
│   │   ├── firestore.tf
│   │   └── variables.tf
│   └── deploy.sh              # 一键部署
├── tests/
├── architecture_diagram.png   # 系统架构图 (评审要求)
└── README.md                  # 含 spin-up 指令
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
| 人脸识别准确率不够 | 中 | Demo 中用提前注册的人，控制环境光线 |
| Developer Console 传感器模拟不够直观 | 中 | 用大号滑块 + 实时数据可视化，让评委一眼看懂 |
| 评委质疑安全性 | 中 | 明确声明不替代白手杖；LOD 1 只提供宏观语义，不做微观导航 |
| 评委质疑隐私 | 低 | 提交材料中写明人脸库设计：仅 embedding、用户主动注册、可删除 |
| 时间不够 | 高 | 优先级排序：LOD + Vision + Demo > Face ID > Memory > Grounding |

### 12.1 砍功能优先级 (如果时间不够)

| 优先级 | 功能 | 说明 |
|--------|------|------|
| **P0 — 必须有** | LOD Engine (3 级) + Orchestrator + Vision Agent + 前端 WebRTC | 没有这些就没有产品 |
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
