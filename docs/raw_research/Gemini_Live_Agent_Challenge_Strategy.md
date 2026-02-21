# Gemini Live Agent Challenge - 冠军战略报告

> 生成日期: 2026-02-21
> 比赛截止: 2026-03-16 5:00 PM PDT
> 剩余时间: ~23 天
>
> ⚠️ **状态说明 (2026-02-22)**：本文为 L3 层级原始策略文档。关键决策已被 `SightLine_Consolidated_Development_Reference.md` 吸收。以下内容中，产品名已从 "Wanderer" 更名为 **SightLine**；前端已从 React PWA / Flutter 迁移到 **Swift Native iOS App**（详见 `SightLine_iOS_Native_Infra_Design.md`）；技术栈中的模型名称、Agent 架构等以 Consolidated Reference 为准。本文仅作竞赛要求、评审标准和 iMeanPiper 迁移分析的历史参考。

---

## 目录

1. [比赛完整信息](#1-比赛完整信息)
2. [iMeanPiper 项目当前状态](#2-imeanpiper-项目当前状态)
3. [契合度分析](#3-契合度分析)
4. [冠军级产品方案](#4-冠军级产品方案)
5. [技术架构设计](#5-技术架构设计)
6. [从 iMeanPiper 迁移策略](#6-从-imeanpiper-迁移策略)
7. [23天冲刺计划](#7-23天冲刺计划)
8. [评审维度逐项攻略](#8-评审维度逐项攻略)
9. [Demo 视频制作指南](#9-demo-视频制作指南)
10. [风险管理](#10-风险管理)
11. [Bonus 加分项](#11-bonus-加分项)
12. [竞争对手分析与差异化](#12-竞争对手分析与差异化)
13. [参考资源](#13-参考资源)

---

## 1. 比赛完整信息

### 1.1 基本信息

| 项目 | 详情 |
|------|------|
| **比赛名称** | Gemini Live Agent Challenge |
| **主题** | "Redefining Interaction: From Static Chatbots to Immersive Experiences" |
| **平台** | Devpost (geminiliveagentchallenge.devpost.com) |
| **主办方** | Google (通过 Devpost 管理) |
| **开始日期** | 2026年2月16日 1:15 PM EST |
| **截止日期** | 2026年3月16日 5:00 PM PDT (8:00 PM EDT) |
| **形式** | 线上比赛 |
| **当前参赛者** | 1,623 人 |

### 1.2 奖金分布 (总计 $80,000)

| 奖项 | 金额 | 数量 | 额外福利 |
|------|------|------|----------|
| **Grand Prize** | **$25,000** | 1 | $3,000 GCP credits, Google coffee chat, 2张 Google Cloud Next 门票 + 旅行补贴 (每人最高$3,000), demo 展示机会 |
| Best Live Agents | $10,000 | 1 | $1,000 GCP credits, Google coffee chat, 2张会议门票 |
| Best Creative Storytellers | $10,000 | 1 | $1,000 GCP credits, Google coffee chat, 2张会议门票 |
| Best UI Navigators | $10,000 | 1 | $1,000 GCP credits, Google coffee chat, 2张会议门票 |
| Best Multimodal Integration & UX | $5,000 | 1 | $500 GCP credits |
| Best Technical Execution & Architecture | $5,000 | 1 | $500 GCP credits |
| Best Innovation & Thought Leadership | $5,000 | 1 | $500 GCP credits |
| Honorable Mentions | $2,000 | 5 | 每人 $500 GCP credits |

**Grand Prize 福利要点**: 除了 $25,000 现金奖金外，最重要的是 2 张 Google Cloud Next 门票 + 每人最高 $3,000 旅行补贴 — 这就是去美国的机票和会议通行证。

### 1.3 三个赛道详情

#### Track 1: Live Agents

- **定义**: 实时音频/视觉交互的 AI Agent
- **典型案例**: 实时翻译器、视觉增强的导师、能自然处理打断的语音客服
- **强制要求**: 必须使用 Gemini Live API 或 ADK，必须部署在 Google Cloud
- **评审重点**: 实时性、多模态交互的自然度、中断处理能力

#### Track 2: Creative Storyteller

- **定义**: 多模态叙事，交织文本、图像、音频、视频的输出
- **典型案例**: 交互式故事书、营销素材生成器、教育解说器
- **强制要求**: 必须使用 Gemini 的 interleaved/mixed output 能力，Google Cloud 托管
- **评审重点**: 多模态输出的无缝融合、叙事质量

#### Track 3: UI Navigator

- **定义**: 视觉 UI 理解和 Agent 自主操作
- **典型案例**: Agent 观察屏幕显示、解释视觉元素、基于意图执行操作
- **强制要求**: 必须使用 Gemini multimodal 能力解释截图/录屏，Google Cloud 托管
- **评审重点**: 视觉理解准确度、操作执行的可靠性

**推荐赛道: Live Agents** — 与 iMeanPiper 的核心能力 (实时语音 + 自适应响应 + 地理感知) 高度匹配。

### 1.4 强制技术要求

所有参赛项目必须满足以下三个条件:

1. **必须使用 Gemini 模型** — 任意 Gemini 变体均可
2. **必须使用 Google GenAI SDK 或 ADK (Agent Development Kit)** — 不能用第三方框架直接调用
3. **必须使用至少一个 Google Cloud 服务** — Cloud Run, Firestore, Cloud Functions 等

### 1.5 提交物清单

| 提交项 | 具体要求 |
|--------|---------|
| **文字描述** | 项目摘要、功能特性、使用技术、数据来源、发现与学习 |
| **公开代码仓库** | 必须包含 README 中的 spin-up 指令 |
| **Google Cloud 部署证明** | 屏幕录像展示后端在 GCP 运行，或代码文件展示 GCP 服务使用 |
| **架构图** | 可视化系统架构，展示 Gemini 的连接方式 |
| **Demo 视频** | 4分钟以内，展示实时多模态功能 (禁止 mockup)，包含问题/价值 pitch |

### 1.6 评审标准详解

#### Innovation & Multimodal User Experience (40%)

这是权重最高的维度，直接决定是否能拿冠军:

- **打破"文本框"范式**: 交互方式必须超越传统的打字→回复模式
- **看/听/说的无缝整合**: 多模态不是简单堆砌，而是自然流畅的融合
- **独特的 persona/voice**: Agent 要有辨识度高的个性和声音
- **上下文感知的实时交互**: 能根据环境、状态、用户行为动态调整

#### Technical Implementation & Agent Architecture (30%)

- **SDK/ADK 的有效利用**: 不是简单调用 API，要深度使用框架能力
- **稳健的 Google Cloud 托管**: 不只是 demo 级别，要有生产级的部署
- **健全的 Agent 逻辑**: 状态管理、错误处理、边界情况
- **防幻觉与 Grounding**: 使用 Google Search grounding 或外部数据验证事实
- **优雅的错误处理**: 网络断开、API 超时等场景的处理

#### Demo & Presentation (30%)

- **清晰的问题/解决方案定义**: 开头 30 秒必须让评委理解你在解决什么问题
- **可读的架构图**: 专业、清晰，不是 draw.io 默认模板
- **可视化的云部署证明**: 截屏或录屏展示 GCP 控制台
- **实际软件演示**: 必须是真实运行的软件，不能是录播/mockup

### 1.7 参赛资格

- 参赛者必须达到其所在国家的法定成年年龄
- 部分国家/地区被排除 (需查看完整规则)
- 线上参赛，无地理限制 (排除名单外)

---

## 2. iMeanPiper 项目当前状态

### 2.1 项目概览

| 维度 | 详情 |
|------|------|
| **项目名称** | iMeanPiper (Interactive Meaningful Experience - Piper) |
| **核心定位** | 自适应实时语音 AI 助手 |
| **核心创新** | Adaptive Level-of-Detail (LOD) 系统 — 根据用户上下文智能调节响应细节深度 |
| **代码规模** | 后端 16,199 行 Python, 前端 11 个 React 组件 + 7 个 Custom Hooks |
| **模块数量** | 70+ Python 模块 |
| **开发阶段** | Phase 7-8 (End-to-End 集成 + 智能切换) |
| **成熟度** | Pre-production (架构健壮、功能完整，待负载测试和可观测性) |

### 2.2 当前技术栈

#### 后端

| 技术 | 版本/详情 | 用途 |
|------|----------|------|
| **Python** | 3.11+ | 主语言 |
| **LiveKit Agents** | 1.3.9 | 实时语音框架 (WebRTC) |
| **FastAPI** | >=0.115.0 | Token Server / API |
| **Pydantic** | >=2.7.0 | 数据模型验证 |
| **Google Gemini** | via livekit-agents | LLM |
| **Deepgram** | via livekit-agents | 语音转文字 (STT) |
| **Silero VAD** | via livekit-agents | 语音活动检测 |
| **loguru** | >=0.7.3 | 日志 |
| **aiohttp** | >=3.10.0 | 异步 HTTP |
| **uvicorn** | >=0.32.0 | ASGI 服务器 |

#### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18 | UI 框架 |
| **TypeScript** | - | 类型安全 |
| **Vite** | 6.0.5 | 构建工具 |
| **@livekit/components-react** | 2.9.10 | LiveKit UI 组件 |
| **livekit-client** | 2.9.6 | LiveKit 客户端 SDK |
| **CSS Modules** | - | 样式 |

#### 外部 API 集成

| API | 用途 | 对应环境变量 |
|-----|------|-------------|
| Google Gemini | LLM 对话生成 | `GOOGLE_API_KEY` |
| Deepgram | 语音转文字 | `DEEPGRAM_API_KEY` |
| Google Places API | POI 搜索、地点详情、评分 | `GOOGLE_PLACES_API_KEY` |
| Google Routes API | 路线规划、距离计算 | `GOOGLE_ROUTES_API_KEY` |
| Google Geocoding API | 逆向地理编码 (经纬度→地址) | `GOOGLE_Geocoding_API_KEY` |
| Google Search API | 上下文搜索 | - |

### 2.3 核心模块详细清单

#### 2.3.1 LOD 基础系统

| 文件 | 模块 | 功能 | 行数概估 |
|------|------|------|---------|
| `lod/config.py` | LODConfig | LOD 级别定义，frozen 不可变配置，LODLevel 枚举 (MINIMAL/BALANCED/DETAILED) | 核心 |
| `lod/manager.py` | LODManager | LOD 状态中央协调器，sequence-based 同步防竞态 | 核心 |
| `lod/state.py` | LODState | LOD 状态管理，叙事位置追踪 (HOOK/BODY_START/BODY_MIDDLE/BODY_END/CONCLUSION) | 核心 |
| `lod/models.py` | Core Models | UserContext, ActivityType, LocationType 等核心数据结构 | 核心 |

#### 2.3.2 冷启动 & 基础 LOD (Phase 1-4)

| 文件 | 功能 |
|------|------|
| `lod/cold_start_engine.py` | 基于 room metadata 和 UserContext 的初始 LOD 决策 |
| `lod/context_parser.py` | JSON metadata 解析为 UserContext (支持前后端字段映射) |
| `lod/prompt_manager.py` | 动态系统 prompt 生成，LOD 级别特定指令，中英双语支持 |
| `lod/tts_manager.py` | 每个 LOD 级别的 TTS 风格指令 (语速、语调、表达力) |

#### 2.3.3 热交互 & 信号检测 (Phase 2-3)

| 文件 | 功能 |
|------|------|
| `lod/signal_detector.py` | 从用户话语中检测意图信号 (LOD_UP, LOD_DOWN, REPEAT 等) |
| `lod/intent_classifier.py` | 用户意图分类 (WANT_DETAIL, WANT_BRIEF, WANT_BALANCED, WANT_RESTORE 等) |
| `lod/transition_analyzer.py` | 分析是否需要 LOD 过渡，计算目标 LOD |
| `lod/interrupt_handler.py` | 处理 Agent 响应期间的用户打断 |

#### 2.3.4 高级生成 (Phase 5-6)

| 文件 | 功能 |
|------|------|
| `lod/segmented_generator.py` | 分段生成响应，LOD 级别特定的 pattern (hook, main, conclusion) |
| `lod/buffered_llm.py` | 包装 LiveKit LLM 流，token 缓冲为完整句子，平滑 TTS 播放 |
| `lod/transition_handler.py` | LOD 过渡管理，保持叙事连续性 |
| `lod/narrative_tracker.py` | 追踪叙事状态和在响应中的位置 |

#### 2.3.5 智能切换 (Phase 7+)

| 文件 | 功能 |
|------|------|
| `lod/snapshot_manager.py` | 叙事快照管理 — LOD 降级时保存状态，允许后续恢复 |
| `lod/topic_aware_manager.py` | 话题感知的状态管理 — 每个话题维护独立的 LOD 状态 |
| `lod/topic_state.py` | 话题状态集合和生命周期管理 |
| `lod/topic_detector.py` | 检测话题切换 vs 话题延续 |
| `lod/models_intelligent.py` | 智能切换数据模型 (TopicState, NarrativeSnapshot, FastPathResult) |

#### 2.3.6 地理感知模块 (`lod/geo/`)

| 文件 | 功能 |
|------|------|
| `geo_models.py` | 核心模型: GeoLocation, GeoContext, PointOfInterest, POICategory |
| `google_services.py` | 集成 Google Places, Routes, Geocoding, Search API |
| `geo_enhancer.py` | 用附近 POI、地址、位置类型丰富 GeoContext |
| `poi_resolver.py` | 从 Google API 解析兴趣点 |
| `poi_ranker.py` | 按相关性和距离对 POI 排序 |
| `geo_prompt.py` | 构建位置感知的系统 prompt |

#### 2.3.7 旅行状态管理 (`lod/travel/`)

| 文件 | 功能 |
|------|------|
| `travel_models.py` | TripContext, VisitRecord, TripStatus (PLANNING/ACTIVE/COMPLETED) |
| `trip_manager.py` | 管理当前旅行和旅行历史 |
| `trip_detector.py` | 从用户话语中检测旅行信号 |
| `trip_memory.py` | 持久化旅行记录，聚合旅行数据 |

#### 2.3.8 用户偏好学习 (`lod/preference/`)

| 文件 | 功能 |
|------|------|
| `preference_models.py` | UserPreferenceProfile: LODPreference, ContentPreference, TravelPreference |
| `preference_learner.py` | 基于反馈更新偏好，可配置学习率 (默认 0.1) |
| `feedback_collector.py` | 收集反馈信号: LOD_UP, LOD_DOWN, POSITIVE, NEGATIVE |

#### 2.3.9 持久化 & 记忆

| 文件 | 功能 |
|------|------|
| `lod/memory_storage.py` | 统一存储系统，从 src/data (demo) 和 ~/.imeanpiper/data (运行时) 加载 |
| `lod/data_loader.py` | 用户配置、POI、旅行记录加载，类级别缓存 |
| `lod/checkpoint.py` | 响应生成恢复的检查点管理 |

#### 2.3.10 质量 & 调试

| 文件 | 功能 |
|------|------|
| `lod/debug_api.py` | 调试端点，监控 LOD 系统状态 |
| `lod/sanitization.py` | 输出净化，安全过滤 |
| `lod/trace_collector.py` | 执行追踪收集，用于分析 |

#### 2.3.11 集成层

| 文件 | 功能 |
|------|------|
| `lod/agent_mixin.py` | LODAgentMixin — 基础 LOD 集成协议 |
| `lod/enhanced_agent_mixin.py` | EnhancedAgentMixin — 扩展 LODAgentMixin，集成 geo/travel/preferences |
| `lod/enhanced_context.py` | EnhancedContext — 组合 UserContext + GeoContext + TripContext + Profile |
| `lod/enhanced_manager.py` | EnhancedLODManager — 编排所有组件的总管理器 |

### 2.4 LOD 三级体系详解

| 级别 | 名称 | 字数 | 结构 | 语音风格 |
|------|------|------|------|---------|
| **LOD 1** | Brief/Minimal | 15-40 词 | 单句，仅核心事实 | 快速、高效 |
| **LOD 2** | Standard/Balanced | 80-150 词 | 引言 + 2-3 要点 + 结论 | 中等语速、清晰 |
| **LOD 3** | Detailed/Narrative | 400-800 词 | 完整叙事弧: HOOK → BODY → CONCLUSION | 慢速、富有表现力 |

LOD 切换触发机制:

- **冷启动决策**: 基于 room metadata (activity, time, location, preferences)
- **热交互调整**: 基于用户实时信号 (语音内容、打断行为、话题切换)
- **活动感知调整**: 行走中自动降级, 静止时允许升级
- **话题独立状态**: 切换话题保留前一话题的 LOD 状态，可恢复

### 2.5 数据结构

```
src/data/
├── users/              # Demo 用户配置文件 (JSON)
│   ├── xiaoming.json   # 小明 — 测试用户
│   ├── xiaohong.json   # 小红 — 测试用户
│   └── xiaogang.json   # 小刚 — 测试用户
├── pois/               # 兴趣点数据库 (按城市)
│   ├── paris.json      # 巴黎 POI (含分类、评分)
│   └── tokyo.json      # 东京 POI (含分类、评分)
└── trips/              # 示例旅行记录
    ├── xiaoming_paris_trip1.json
    └── xiaohong_tokyo_trip1.json
```

### 2.6 服务架构

```
当前 iMeanPiper 运行需要启动三个服务:

1. Token Server (FastAPI) — 端口 8000
   - 生成 LiveKit tokens 用于客户端连接
   - Agent Dispatch 自动分配 Agent 到 Room
   - 端点: /api/token, /api/geocode

2. Agent Process — 运行 iMeanPiperAgent
   - 通过 LiveKit 监听用户连接
   - 处理语音输入 → LLM → 语音输出
   - 管理 LOD, preferences, geographic context

3. Frontend (React/Vite) — 端口 5173 (dev)
   - 对话视图
   - 上下文面板 (用户配置和设置)
   - 位置显示 (地理上下文)
   - LOD 调试面板 (监控系统状态)
   - 音频控制和日志面板
```

### 2.7 独特技术创新 (10项)

1. **自适应 Level-of-Detail 系统**: 三级细节自动切换，非一刀切回复
2. **叙事快照管理**: LOD 降级时保存叙事状态，用户可随时恢复
3. **话题感知状态管理**: 每个话题独立维护 LOD/叙事状态
4. **句子级 LLM 缓冲**: 自定义句子边界缓冲，防止 TTS 播放碎片化 token
5. **快速路径意图检测**: 规则匹配常见意图 (~即时响应)，复杂意图回退 LLM
6. **分段响应生成**: LOD3 响应按叙事段落 (HOOK/BODY/CONCLUSION) 分段生成
7. **冷启动+热交互双阶段决策**: 冷启动基于元数据，热交互基于实时信号
8. **活动特化偏好学习**: 不仅全局学习偏好，还按活动分类 (driving_lod/walking_lod/stationary_lod)
9. **序列号状态同步**: 防并发竞态的 sequence-based 版本控制
10. **地理上下文丰富**: 实时逆向地理编码 + POI 发现 + 位置感知 prompt 注入

### 2.8 代码质量评估

| 维度 | 评分 | 说明 |
|------|------|------|
| **文档质量** | ★★★★★ | 完整 docstring，引用 "iMeanPiper LOD System - Technical Design Document v1.1" |
| **模块化设计** | ★★★★★ | 70+ 模块，职责清晰分离 |
| **类型安全** | ★★★★☆ | 全面使用 type hints, dataclass, Pydantic |
| **错误处理** | ★★★★☆ | try-catch 配合 loguru 日志 |
| **异步模式** | ★★★★☆ | asyncio.Lock 保证线程安全 |
| **配置管理** | ★★★★★ | frozen dataclass 不可变配置 |
| **设计模式** | ★★★★★ | Mixin, Factory, State Machine, Decorator, Protocol |

### 2.9 近期开发历史

```
2cd3ff6 feat: Implement narrative snapshot management and topic-aware state management
969e3a8 feat: add enhanced LOD system with geographic awareness, travel management, and user preferences
f2f5eaa fix: update BufferedLLM to match new LiveKit Agents API
e718c85 feat: enhance LOD functionality with job metadata support, improve greeting consistency, and optimize LOD transition analysis
bde7626 chore: update .gitignore to exclude dev/ directory and cache files
00e4f65 feat: enhance LOD state with reasoning and last agent response, add LOD3 progress indicator, and refine cold start greetings
```

开发轨迹: 基础 LOD → LiveKit API 对齐 → Geo/Travel/Preferences 增强 → 智能切换 + Snapshot

---

## 3. 契合度分析

### 3.1 高度契合的能力

| iMeanPiper 能力 | 比赛价值 | 契合度 | 详细说明 |
|-----------------|---------|--------|---------|
| **自适应 LOD 系统** | 直击 "Innovation" 40% 权重 | ★★★★★ | 市面上没有任何竞品有这个概念，这是真正的原创创新，不是 wrapper |
| **地理感知 (Google APIs)** | 已用 Google 生态，迁移零成本 | ★★★★★ | Places/Routes/Geocoding 全是 Google API，完美契合 |
| **实时语音对话** | 比赛基本要求 | ★★★★★ | 核心能力已验证，只需换底层框架 |
| **旅行状态管理** | 极佳的 demo 场景 | ★★★★☆ | 旅行是最直观的多模态场景，评委一看就懂 |
| **用户偏好学习** | 个性化是评委看重的差异化 | ★★★★☆ | 跨会话记忆 + 活动特化学习 = 展示 Agent 智能 |
| **Narrative Snapshot** | 独特交互创新 | ★★★★☆ | "记住你说到哪了"，非常 human-like 的能力 |
| **Topic-Aware State** | 对话管理成熟度 | ★★★★☆ | 展示 Agent 架构的深度 |
| **中断处理** | Live Agent 赛道核心要求 | ★★★★★ | 赛道描述明确提到 "handling interruptions naturally" |

### 3.2 需要替换的技术栈

| 当前技术 | 替换为 | 原因 | 迁移难度 |
|----------|--------|------|---------|
| LiveKit Agents | **Google ADK** | 比赛强制要求使用 GenAI SDK 或 ADK | ★★★★☆ 高 — 框架范式不同 |
| Deepgram STT | **Gemini Live API native audio** | 全 Google 生态 + 更低延迟 | ★★★☆☆ 中 — API 替换 |
| LiveKit TTS | **Gemini Live API audio output** | 原生双向音频流 | ★★★☆☆ 中 — API 替换 |
| 自建 Token Server | **Cloud Run 服务** | 比赛要求 GCP 部署 | ★★☆☆☆ 低 — Dockerfile + deploy |
| React + LiveKit UI | **React/Flutter + WebSocket** | LiveKit components 不可用 | ★★★☆☆ 中 — 重写 UI 层 |

### 3.3 必须新增的能力

| 能力 | 为什么必须新增 | 优先级 |
|------|--------------|--------|
| **视觉输入 (Camera/Video)** | 40% 的 Multimodal UX 权重，纯音频不够差异化 | P0 |
| **Gemini Grounding** | 评审标准明确提到 "grounding evidence" 和 "hallucination prevention" | P0 |
| **Multi-Agent 架构** | ADK 的核心设计理念，展示技术深度 | P1 |
| **Google Cloud 深度集成** | 越多 GCP 服务 = 越高技术分，至少 3-4 个 | P1 |
| **移动端适配** | 旅行场景必须在手机上可用 | P1 |
| **IaC 自动部署** | Bonus 加分项 | P2 |

### 3.4 契合度总结

```
整体契合度: ████████░░ 80%

可直接复用:   ~60% 的核心逻辑 (LOD系统、Geo、Travel、Preference)
需要重写:     ~30% 的胶水代码 (框架集成层、流式处理)
需要新增:     ~10% 的新能力 (视觉输入、Multi-Agent 编排)
```

**结论**: iMeanPiper 的核心创新 (LOD 系统) 和领域逻辑 (Geo/Travel/Preference) 可以大量复用，但框架层需要从 LiveKit 迁移到 Google ADK。这不是从零开始，而是"换引擎保留车身"。

---

## 4. 冠军级产品方案

### 4.1 产品定位

**名称**: **Wanderer** — 能看、能听、能感知你所在世界的 AI 旅行伙伴

**一句话定位**:
> "We don't just answer questions. We sense how much you need to know, right now, in this moment."

**核心差异化**: 不是又一个聊天机器人，而是一个能通过手机摄像头看到你眼前的世界、听到你的声音、知道你在哪里、并根据你当前状态智能调节对话深度的实时 AI 伙伴。

### 4.2 为什么这个方案能拿冠军

| 维度 | 优势 | 竞争对手可能做什么 |
|------|------|-------------------|
| **多模态** | 视觉 + 语音 + 位置 三模态同时在线 | 大多数只做语音，少数加视觉 |
| **创新性** | LOD 系统是真正的学术级创新 | 简单的 prompt engineering |
| **Demo 效果** | 旅行场景天然丰富，4分钟能讲完整故事 | 通用对话，缺乏具象场景 |
| **技术深度** | 16,000+ 行经过打磨的核心代码 | 大多数是 hackathon 级原型 |
| **Google 生态** | 6+ Google 服务自然集成 | 可能只用 1-2 个 |
| **用户体验** | 上下文感知 + 个性化 + 记忆 | 每次对话从零开始 |

### 4.3 核心场景设计

#### 场景 1: 建筑识别 + 自适应讲解

```
[用户在巴黎街头，手机摄像头对着埃菲尔铁塔]

用户: "Hey Wanderer, what am I looking at?"

Wanderer: [LOD1 - 简洁模式，因为用户在行走中]
  "That's the Eiffel Tower, built in 1889. You're about
   200 meters from the south entrance."

用户: "Tell me more about it"

Wanderer: [LOD1 → LOD2 过渡]
  "The Eiffel Tower was designed by Gustave Eiffel for the
   1889 World's Fair. Standing at 330 meters, it was the
   world's tallest structure for 41 years. The south entrance
   ahead of you has the shortest queue right now."
```

#### 场景 2: 深度叙事 + Snapshot

```
[用户在咖啡馆坐下]

用户: "Now I've got time. Tell me the whole story."

Wanderer: [LOD2 → LOD3，叙事模式激活]
  "So here's the fascinating story... [HOOK]
   When Gustave Eiffel first proposed this iron tower,
   Parisians absolutely HATED it. A group of 300 artists
   signed a petition calling it 'a disgrace to the city'...
   [BODY - 展开历史叙事]
   ..."

用户: [打断] "Wait, how tall is it exactly?"

Wanderer: [Narrative Snapshot 保存当前位置]
  "330 meters to the tip. Want me to continue the story
   from where we left off?"

用户: "Yes, go on"

Wanderer: [从 Snapshot 恢复]
  "Right, so where were we... The petition. Despite the
   outrage, Eiffel had a clever plan..."
```

#### 场景 3: 视觉模态切换

```
[用户将摄像头对准一个法语餐厅菜单]

Wanderer: [检测到视觉内容变化，自动切换模态]
  "I see a French bistro menu. The duck confit at €24
   is their specialty — rated 4.5 on Google. The crème
   brûlée is also highly recommended."

用户: "What about allergies? I'm allergic to nuts."

Wanderer: [结合视觉 + 用户偏好记忆]
  "Looking at the menu... the salade niçoise and the
   grilled sea bass both appear nut-free. I'd recommend
   asking the waiter about the duck confit sauce though —
   French sauces sometimes contain trace amounts."
```

#### 场景 4: 动态状态感知

```
[用户从咖啡馆起身开始走路]

Wanderer: [检测到运动状态变化，LOD 自动降级]
  "I see you're on the move. Quick tip: the best photo spot
   is Trocadéro, about 10 minutes walk north. Want directions?"

[用户上了出租车]

Wanderer: [检测到交通工具，进一步简化]
  "ETA to your hotel: 15 minutes via Pont d'Iéna."
```

### 4.4 功能全景

#### Tier 1: 核心功能 (必须实现)

- [x] 实时双向语音对话 (Gemini Live API)
- [x] 自适应 LOD 系统 (3级)
- [x] 视觉输入理解 (摄像头画面)
- [x] 地理位置感知 (GPS + Google Maps)
- [x] POI 发现与推荐
- [x] 中断处理与叙事恢复

#### Tier 2: 差异化功能 (强烈推荐)

- [x] Narrative Snapshot (叙事快照保存/恢复)
- [x] Topic-Aware State (话题级独立状态)
- [x] 用户偏好学习 (跨会话)
- [x] 活动感知 LOD 调整 (行走/驾车/静止)
- [x] Multi-Agent 架构 (ADK)

#### Tier 3: 锦上添花 (如果时间允许)

- [ ] 多语言支持 (中/英/法/日)
- [ ] 旅行行程规划
- [ ] AR 覆盖 (摄像头画面上叠加信息)
- [ ] 离线模式 (基础功能)
- [ ] 社交分享 (旅行记录导出)

---

## 5. 技术架构设计

### 5.1 系统架构图

```
┌───────────────────────────────────────────────────────────┐
│                      Mobile Client                         │
│                  (React PWA / Flutter)                      │
│                                                            │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐ │
│  │  Camera     │  │  Microphone│  │  GPS / Geolocation   │ │
│  │  Stream     │  │  Stream    │  │  Stream              │ │
│  └──────┬─────┘  └──────┬─────┘  └──────────┬───────────┘ │
│         │               │                    │             │
│         └───────┬───────┘                    │             │
│            WebSocket                         │             │
│         (audio + video                       │             │
│          + text frames)               HTTP/REST            │
└─────────────┬───────────────────────────┬──────────────────┘
              │                           │
              │    Google Cloud Platform   │
    ┌─────────▼───────────────────────────▼──────────────────┐
    │                                                        │
    │  ┌──────────────────────────────────────────────────┐  │
    │  │              Cloud Run Service                    │  │
    │  │                                                   │  │
    │  │  ┌─────────────────────────────────────────────┐  │  │
    │  │  │        ADK Orchestrator Agent (Root)         │  │  │
    │  │  │                                              │  │  │
    │  │  │  - Session management                        │  │  │
    │  │  │  - Agent dispatch & routing                  │  │  │
    │  │  │  - LOD decision engine                       │  │  │
    │  │  │  - Context aggregation                       │  │  │
    │  │  └──────┬──────────┬──────────┬────────────────┘  │  │
    │  │         │          │          │                    │  │
    │  │  ┌──────▼───┐ ┌───▼──────┐ ┌─▼────────────────┐  │  │
    │  │  │  Voice    │ │  Vision  │ │  Geo Agent        │  │  │
    │  │  │  Agent    │ │  Agent   │ │                   │  │  │
    │  │  │          │ │          │ │ - Google Places    │  │  │
    │  │  │ Gemini   │ │ Gemini   │ │ - Google Routes   │  │  │
    │  │  │ Live API │ │ Vision   │ │ - Geocoding       │  │  │
    │  │  │ (bidi    │ │ (image   │ │ - POI ranking     │  │  │
    │  │  │  audio)  │ │  analysis│ │                   │  │  │
    │  │  └──────────┘ └──────────┘ └───────────────────┘  │  │
    │  │         │                                          │  │
    │  │  ┌──────▼──────────────────────────────────────┐  │  │
    │  │  │  Memory Agent                                │  │  │
    │  │  │                                              │  │  │
    │  │  │  - User preferences (LOD/Content/Travel)     │  │  │
    │  │  │  - Trip records & history                    │  │  │
    │  │  │  - Narrative snapshots                       │  │  │
    │  │  │  - Cross-session state                       │  │  │
    │  │  └──────────────────────────────────────────────┘  │  │
    │  │                                                   │  │
    │  └───────────────────────────────────────────────────┘  │
    │                                                        │
    │  ┌────────────┐ ┌────────────┐ ┌──────────────────┐   │
    │  │ Firestore   │ │ Cloud      │ │ Secret Manager   │   │
    │  │             │ │ Storage    │ │                   │   │
    │  │ - User state│ │ - Vision   │ │ - API keys       │   │
    │  │ - Prefs     │ │   snapshots│ │ - Credentials    │   │
    │  │ - Trips     │ │ - Audio    │ │                   │   │
    │  │ - Snapshots │ │   cache    │ │                   │   │
    │  └────────────┘ └────────────┘ └──────────────────┘   │
    │                                                        │
    │  ┌────────────┐ ┌────────────┐ ┌──────────────────┐   │
    │  │ Cloud       │ │ Artifact   │ │ Cloud Logging    │   │
    │  │ Functions   │ │ Registry   │ │                   │   │
    │  │             │ │            │ │ - Structured logs │   │
    │  │ - Geocode   │ │ - Docker   │ │ - Metrics        │   │
    │  │   proxy     │ │   images   │ │ - Traces         │   │
    │  └────────────┘ └────────────┘ └──────────────────┘   │
    │                                                        │
    └────────────────────────────────────────────────────────┘
              │                    │
    ┌─────────▼────────┐  ┌───────▼──────────┐
    │ Google Maps       │  │ Google Search     │
    │ Platform          │  │ Grounding         │
    │                   │  │                   │
    │ - Places API      │  │ - Fact checking   │
    │ - Routes API      │  │ - Real-time info  │
    │ - Geocoding API   │  │                   │
    └───────────────────┘  └───────────────────┘
```

### 5.2 Multi-Agent 架构 (ADK)

| Agent | 职责 | Gemini 模型 | ADK 类型 |
|-------|------|------------|---------|
| **Orchestrator** (Root) | 会话管理、Agent 调度、LOD 决策引擎、上下文聚合 | gemini-2.5-pro | LlmAgent (root) |
| **Voice Agent** | 实时双向语音、Gemini Live API 流、中断检测与处理 | gemini-2.5-flash-native-audio | LlmAgent (sub) |
| **Vision Agent** | 摄像头画面理解、场景描述、OCR、物体识别 | gemini-2.5-pro (vision) | LlmAgent (sub) |
| **Geo Agent** | 位置感知、POI 推荐、路线规划、地理上下文丰富 | gemini-2.5-flash + Tools | LlmAgent (sub) |
| **Memory Agent** | 用户偏好管理、旅行记录、跨会话状态、叙事快照 | gemini-2.5-flash + Firestore | LlmAgent (sub) |

#### Agent 间通信模式

```
用户语音 ──→ Voice Agent ──→ Orchestrator ──→ [决策: 需要哪些 Agent?]
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
              Vision Agent   Geo Agent    Memory Agent
                    │             │             │
                    └─────────────┼─────────────┘
                                  │
                            Orchestrator ──→ LOD Manager ──→ 生成响应
                                  │
                            Voice Agent ──→ 用户 (语音输出)
```

### 5.3 Google Cloud 服务集成清单

| 服务 | 用途 | 必要性 | 加分项 |
|------|------|--------|--------|
| **Cloud Run** | 托管 ADK Agent 后端 (容器化部署) | 必须 | ✅ 核心部署 |
| **Firestore** | 用户状态、偏好、旅行记录持久化 | 必须 | ✅ GCP 深度集成 |
| **Cloud Storage** | 视觉快照缓存、音频文件存储 | 推荐 | ✅ 多媒体管理 |
| **Secret Manager** | API Key 安全管理 | 推荐 | ✅ 安全最佳实践 |
| **Cloud Logging** | 结构化日志、指标、追踪 | 推荐 | ✅ 可观测性 |
| **Cloud Functions** | Geocoding 代理、Webhook | 可选 | ✅ Serverless |
| **Artifact Registry** | Docker 容器镜像管理 | 推荐 | ✅ CI/CD |
| **Maps Platform** | Places/Routes/Geocoding API | 已有 | ✅ Google 生态 |

### 5.4 数据流详解

#### 语音交互流 (主流程)

```
1. 用户说话
2. 客户端捕获音频流 → WebSocket → Cloud Run
3. ADK 接收音频 → Gemini Live API (bidi streaming)
4. Gemini 进行 STT → 文本
5. Orchestrator 接收文本:
   a. Signal Detector 检测意图信号
   b. Intent Classifier 分类意图
   c. LOD Manager 决策当前 LOD 级别
   d. 按需调度 Vision/Geo/Memory Agent
6. Orchestrator 生成响应 (带 LOD 控制的 system prompt)
7. Gemini 生成文本 → Live API 转语音
8. 语音流 → WebSocket → 客户端播放
```

#### 视觉输入流 (并行)

```
1. 客户端摄像头捕获帧 (按需/定时)
2. 帧 → WebSocket → Cloud Run
3. Vision Agent 接收帧 → Gemini Vision 分析
4. 分析结果 → Orchestrator (更新 context)
5. 如果检测到显著变化 (新建筑、菜单、标志):
   → 主动触发相关信息推送 (如果 LOD 允许)
```

#### 地理位置流 (持续)

```
1. 客户端 GPS 持续上报位置 (间隔 30s)
2. Geo Agent 接收新位置:
   a. 逆向地理编码 → 当前地址
   b. 附近 POI 发现 → 排序
   c. 运动状态检测 (静止/步行/驾车)
3. 地理上下文更新 → Orchestrator
4. 如果位置显著变化 → 触发 LOD 重新评估
```

### 5.5 Gemini Live API 技术规格

| 参数 | 规格 |
|------|------|
| **音频输入格式** | 16-bit PCM, 16kHz, mono |
| **音频输出采样率** | 24kHz |
| **连接方式** | WebSocket (双向流) |
| **默认模型** | gemini-2.5-flash-native-audio-preview |
| **支持模态** | 音频 + 视频 + 文本 (输入), 音频 + 文本 (输出) |
| **内置功能** | VAD, 函数调用, 会话管理, 临时令牌 |
| **中断处理** | 内置 VAD 触发音频队列清除 |

### 5.6 ADK 流式架构关键组件

| 组件 | 作用 |
|------|------|
| **LiveRequestQueue** | 管理上行消息流: 发送文本、音频、视频和活动信号，支持并发 |
| **run_live()** | 处理下行事件: 文本/音频转录、自动工具执行、多 Agent 工作流 |
| **RunConfig** | 控制响应模态、流式模式、会话管理、上下文压缩、配额处理 |
| **Streaming Tools** | 工具返回中间结果，Agent 动态响应 (如实时 POI 查询) |
| **Session Resumption** | 断线后继续会话 |

---

## 6. 从 iMeanPiper 迁移策略

### 6.1 可直接复用的模块 (节省大量时间)

| 模块 | 文件路径 | 迁移难度 | 预估工作量 | 说明 |
|------|---------|---------|-----------|------|
| LOD Config | `lod/config.py` | ⭐ | 0.5h | 配置定义，完全不依赖框架 |
| Core Models | `lod/models.py` | ⭐ | 0.5h | 纯数据模型 |
| Signal Detector | `lod/signal_detector.py` | ⭐ | 0h | 纯文本处理，零依赖 |
| Intent Classifier | `lod/intent_classifier.py` | ⭐ | 0h | 纯文本处理，零依赖 |
| Transition Analyzer | `lod/transition_analyzer.py` | ⭐⭐ | 1h | 小幅适配新 context 格式 |
| LOD State | `lod/state.py` | ⭐ | 0.5h | 纯状态管理 |
| Prompt Manager | `lod/prompt_manager.py` | ⭐⭐ | 2h | 适配 Gemini prompt 格式 |
| Geo Models | `lod/geo/geo_models.py` | ⭐ | 0h | 纯数据模型 |
| Google Services | `lod/geo/google_services.py` | ⭐ | 0h | 直接复用 (已是 Google API) |
| Geo Enhancer | `lod/geo/geo_enhancer.py` | ⭐ | 0h | 纯逻辑 |
| POI Resolver | `lod/geo/poi_resolver.py` | ⭐ | 0h | 纯逻辑 |
| POI Ranker | `lod/geo/poi_ranker.py` | ⭐ | 0h | 纯逻辑 |
| Geo Prompt | `lod/geo/geo_prompt.py` | ⭐ | 0.5h | 微调 prompt 格式 |
| Travel Models | `lod/travel/travel_models.py` | ⭐ | 0h | 纯数据模型 |
| Trip Manager | `lod/travel/trip_manager.py` | ⭐⭐ | 1h | 存储层适配 Firestore |
| Trip Detector | `lod/travel/trip_detector.py` | ⭐ | 0h | 纯文本分析 |
| Trip Memory | `lod/travel/trip_memory.py` | ⭐⭐ | 1h | 存储层适配 Firestore |
| Preference Models | `lod/preference/preference_models.py` | ⭐ | 0h | 纯数据模型 |
| Preference Learner | `lod/preference/preference_learner.py` | ⭐ | 0h | 纯算法逻辑 |
| Feedback Collector | `lod/preference/feedback_collector.py` | ⭐ | 0h | 纯逻辑 |
| Snapshot Manager | `lod/snapshot_manager.py` | ⭐⭐ | 2h | 适配新 Agent session 模型 |
| Topic Detector | `lod/topic_detector.py` | ⭐ | 0h | 纯文本分析 |
| Topic State | `lod/topic_state.py` | ⭐ | 0.5h | 微调 |
| Topic Aware Manager | `lod/topic_aware_manager.py` | ⭐⭐ | 2h | 适配新 Agent 架构 |
| Sanitization | `lod/sanitization.py` | ⭐ | 0h | 纯文本处理 |
| Trace Collector | `lod/trace_collector.py` | ⭐⭐ | 1h | 适配 Cloud Logging |
| Data Loader | `lod/data_loader.py` | ⭐⭐ | 2h | 适配 Firestore |
| Intelligent Models | `lod/models_intelligent.py` | ⭐ | 0h | 纯数据模型 |

**可复用模块预估总工作量: ~15 小时** (大部分是 0-1 小时的微调)

### 6.2 必须重写的模块

| 模块 | 原文件 | 原因 | 预估工作量 | 详细说明 |
|------|--------|------|-----------|---------|
| **Agent 主入口** | `agent.py` | LiveKit Agent → ADK Agent 范式完全不同 | 16h | 需要按 ADK 的 LlmAgent 模式重新构建，包括 Orchestrator + 子 Agent 定义 |
| **Buffered LLM** | `lod/buffered_llm.py` | LiveKit LLMStream → Gemini Live API stream | 8h | 缓冲逻辑可复用，但流接口完全不同 |
| **Agent Mixin** | `lod/agent_mixin.py` | LiveKit Mixin → ADK Agent callback | 12h | 集成点完全不同，需要用 ADK 的 tool/callback 机制 |
| **Enhanced Mixin** | `lod/enhanced_agent_mixin.py` | 同上 | 8h | 依赖 Agent Mixin |
| **LOD Manager** | `lod/manager.py` | 需要适配 ADK session 管理 | 6h | 核心逻辑复用，但状态同步机制需要适配 |
| **Enhanced Manager** | `lod/enhanced_manager.py` | 同上 | 4h | 组合层适配 |
| **Token Server** | `token_server.py` | 改为 Cloud Run + ADK session | 4h | 简化 (ADK 自带 session 管理) |
| **前端 GUI** | `src/gui/` | LiveKit components → WebSocket + Audio API | 20h | UI 逻辑可参考，但组件层全部重写 |
| **Interrupt Handler** | `lod/interrupt_handler.py` | LiveKit interrupt → Gemini Live API VAD | 4h | Gemini Live API 内置 VAD，逻辑可简化 |
| **TTS Manager** | `lod/tts_manager.py` | LiveKit TTS → Gemini Live API audio output | 3h | Gemini 原生音频，TTS 指令通过 voice config |
| **Segmented Generator** | `lod/segmented_generator.py` | 流式接口变化 | 6h | 分段逻辑复用，适配 ADK 流式输出 |
| **Vision Agent** (新) | 无 | 全新模块 | 12h | Gemini Vision API + 摄像头流处理 |
| **Grounding 集成** (新) | 无 | 全新模块 | 4h | Google Search Grounding |

**必须重写模块预估总工作量: ~107 小时**

### 6.3 迁移优先级排序

```
优先级 P0 (Day 1-5): 基础能跑
├── ADK 项目框架搭建
├── Voice Agent (Gemini Live API 双向音频)
├── Cloud Run 部署
└── 前端 WebSocket 音频连通

优先级 P1 (Day 6-12): 核心逻辑
├── LOD Manager (ADK 版)
├── Signal Detector + Intent Classifier (直接复用)
├── Prompt Manager (适配 Gemini)
├── Geo Agent (复用 google_services.py)
├── Firestore 集成
└── Vision Agent (基础版)

优先级 P2 (Day 13-18): 差异化
├── Narrative Snapshot (适配)
├── Topic-Aware State (适配)
├── Multi-Agent 编排完善
├── Preference Learning (复用 + Firestore)
├── Travel State Management (复用)
└── Grounding 集成

优先级 P3 (Day 19-23): 打磨
├── Demo 视频录制
├── 架构图制作
├── README 完善
├── Edge case 处理
├── Bonus 项 (博客、IaC、GDG)
└── 最终测试
```

### 6.4 存储层迁移: 本地文件 → Firestore

当前 iMeanPiper 使用本地 JSON 文件 + `~/.imeanpiper/data` 目录。迁移到 Firestore 的映射:

| 当前存储 | Firestore Collection | 文档结构 |
|---------|---------------------|---------|
| `src/data/users/*.json` | `users/{userId}` | 用户 profile + 偏好 |
| `src/data/pois/*.json` | `pois/{city}/items/{poiId}` | POI 数据 |
| `src/data/trips/*.json` | `users/{userId}/trips/{tripId}` | 旅行记录 |
| `~/.imeanpiper/data` (运行时) | `sessions/{sessionId}` | 会话状态、LOD 状态 |
| Narrative Snapshots | `users/{userId}/snapshots/{topicId}` | 叙事快照 |
| Preference Updates | `users/{userId}` (子文档) | 偏好更新记录 |

---

## 7. 23天冲刺计划

### Phase 1: 基础搭建 (Day 1-5, 2/22-2/26)

| 天 | 任务 | 交付物 | 检验标准 |
|-----|------|--------|---------|
| Day 1 | 搭建 ADK Python 项目框架 | 可运行的 ADK 空项目 | `adk web` 能启动 |
| Day 1 | 学习 ADK 文档 + 样例 | 理解 ADK 范式 | 能解释 Agent/Tool/Session 关系 |
| Day 2 | 实现基础 Voice Agent (Gemini Live API) | 能双向语音对话 | 说话 → 回复 → 听到声音 |
| Day 3 | 前端基础 (WebSocket 音频流) | 浏览器能说话并听到回复 | 浏览器打开即可对话 |
| Day 4 | 部署到 Cloud Run | 云端可访问 | 公网 URL 能对话 |
| Day 5 | 集成 Firestore (基础) | 用户状态可持久化 | 刷新页面后状态不丢 |

**Phase 1 目标**: 一个能在 Cloud Run 上运行的基础语音 Agent，浏览器可访问。

### Phase 2: 核心迁移 (Day 6-12, 2/27-3/5)

| 天 | 任务 | 交付物 |
|-----|------|--------|
| Day 6 | 迁移 LOD Config + Models + State | LOD 基础框架就位 |
| Day 7 | 迁移 Signal Detector + Intent Classifier + Transition Analyzer | LOD 信号检测链就位 |
| Day 8 | 实现 ADK 版 LOD Manager + Prompt Manager | LOD 决策 + prompt 生成可用 |
| Day 9 | 集成 Geo Agent (复用 google_services.py) | 位置感知可用 |
| Day 10 | 实现 Vision Agent (基础版) | 摄像头画面 → 场景描述 |
| Day 11 | Multi-Agent 编排 (Orchestrator 调度) | 多 Agent 协作可用 |
| Day 12 | 集成测试 + Bug 修复 | 核心流程端到端跑通 |

**Phase 2 目标**: LOD 系统 + Geo + Vision 在 ADK 上完整运行。

### Phase 3: 差异化特性 (Day 13-18, 3/6-3/11)

| 天 | 任务 | 交付物 |
|-----|------|--------|
| Day 13 | 迁移 Narrative Snapshot Manager | 叙事快照保存/恢复可用 |
| Day 14 | 迁移 Topic-Aware State Management | 话题级独立 LOD 状态可用 |
| Day 15 | 迁移 Travel State Management | 旅行状态检测与管理可用 |
| Day 16 | 迁移 Preference Learning | 跨会话偏好学习可用 |
| Day 17 | Grounding 集成 (Google Search) | 防幻觉可用 |
| Day 18 | 全流程集成测试 + 性能优化 | 所有功能联调通过 |

**Phase 3 目标**: 全部差异化功能就位，系统功能完整。

### Phase 4: 打磨 & 提交 (Day 19-23, 3/12-3/16)

| 天 | 任务 | 交付物 |
|-----|------|--------|
| Day 19 | Edge case 处理 + 错误恢复 | 系统鲁棒性提升 |
| Day 20 | 制作架构图 (专业工具) | 提交用架构图 |
| Day 20 | 完善 README (含 spin-up 指令) | 完整可运行的文档 |
| Day 21 | 录制 Demo 视频 (第1版) | 4分钟内完整 demo |
| Day 22 | 修改 Demo 视频 (基于自评) | 优化版 demo |
| Day 22 | 发布博客 (#GeminiLiveAgentChallenge) | Bonus 加分 |
| Day 23 | GCP 部署截屏 + 最终提交 | 所有提交物就绪 |
| Day 23 | 加入 Google Developer Group | Bonus 加分 |

**Phase 4 目标**: 所有提交物就绪，按时提交。

### 每日时间分配建议

```
每天可用时间假设: 8-10 小时

7:00-8:00   回顾昨日进展，规划当天任务
8:00-12:00  核心编码 (4h)
12:00-13:00 午休
13:00-17:00 核心编码 (4h)
17:00-18:00 测试 + 记录问题
18:00-19:00 晚饭
19:00-21:00 修复 Bug + 准备明天 (2h, 可选)
```

---

## 8. 评审维度逐项攻略

### 8.1 Innovation & Multimodal UX (40%) — 最高权重

这是决定冠军的维度。你的策略:

#### 8.1.1 打破"文本框"范式

**LOD 系统就是你的答案。** 传统 AI 助手无论用户在什么状态下，都给出同样长度和深度的回复。Wanderer 根据:
- 用户的物理状态 (行走/驾车/静止)
- 当前话题的深度
- 用户的实时反馈信号
- 历史偏好

动态调整响应。这不是简单的 "长回复 vs 短回复"，而是一个有学术深度的自适应系统。

**包装话术**: "We invented Adaptive Level-of-Detail for conversational AI — a system that senses your context and adjusts not just what it says, but how much it says."

#### 8.1.2 看/听/说的无缝整合

三个模态不是分开工作的，而是协同的:
- **视觉** 检测到新建筑 → **语音** 自动介绍 (如果 LOD 允许)
- **位置** 检测到进入博物馆 → LOD 自动调整为 "详细" (适合参观)
- **语音** 用户说 "tell me more" → 视觉上下文辅助生成更丰富的回答
- **中断**: 用户打断时，系统保存叙事快照，视觉/位置上下文继续更新

#### 8.1.3 独特 Persona

Wanderer 不是一个冰冷的助手，而是一个 "博学的旅伴":
- LOD1: 简洁、高效，像经验丰富的导游快速指路
- LOD2: 友好、信息丰富，像知识渊博的朋友
- LOD3: 叙事性强，像一个讲故事的人，有 hook、悬念和结论

#### 8.1.4 上下文感知的实时交互

展示链:
```
GPS 检测到运动 → LOD 自动降级 → 响应变短
停下来 → LOD 恢复 → 可以展开讲
摄像头看到新东西 → 主动提供信息 (不需要用户问)
切换话题 → 新话题独立 LOD → 旧话题状态保存
回到旧话题 → 自动恢复之前的叙事位置
```

### 8.2 Technical Implementation & Agent Architecture (30%)

#### 8.2.1 ADK 深度利用

不是简单的 "用 ADK 包一层"，而是:
- **Multi-Agent**: 5 个专职 Agent (Orchestrator, Voice, Vision, Geo, Memory)
- **Streaming Tools**: Geo Agent 使用流式工具返回实时 POI 数据
- **Session Management**: ADK 内置 session + Firestore 持久化
- **Voice Configuration**: 每个 LOD 级别有不同的语音配置

#### 8.2.2 Google Cloud 深度集成

展示至少 6 个 GCP 服务的有意义使用:
1. Cloud Run — 容器化部署
2. Firestore — 状态持久化
3. Cloud Storage — 媒体缓存
4. Secret Manager — 密钥管理
5. Cloud Logging — 可观测性
6. Maps Platform — 地理服务

#### 8.2.3 防幻觉与 Grounding

- **Google Search Grounding**: 对事实性问题 (历史年份、建筑高度等) 使用 Grounding
- **Google Places API**: POI 信息直接来自 Google 数据，不是 LLM 生成
- **明确的 fallback**: 当不确定时，明确说 "I'm not sure about that" 而不是编造

#### 8.2.4 错误处理

从 iMeanPiper 继承的鲁棒机制:
- Sequence-based 防竞态
- LOD 降级作为 fallback (如果 LOD3 生成失败，回退到 LOD2)
- 网络断开时的 Session Resumption
- API 超时的优雅降级

### 8.3 Demo & Presentation (30%)

详见下一章。

---

## 9. Demo 视频制作指南

### 9.1 4分钟脚本 (秒级)

```
[0:00-0:30] 开场 — 问题定义
━━━━━━━━━━━━━━━━━━━━━━━━━
画面: 城市街道快进 + 各种 AI 助手界面的对比
旁白: "Every voice assistant talks to you the same way —
       whether you're driving 80mph or sitting in a quiet café.
       We built Wanderer to change that."
文字卡: "Wanderer — An AI that senses how much you need to know"

[0:30-1:00] 技术概述
━━━━━━━━━━━━━━━━━━━
画面: 架构图 (动画展示)
旁白: "Wanderer is a multi-agent system powered by Gemini Live API
       and Google ADK, deployed on Google Cloud. It combines real-time
       voice, camera vision, and GPS awareness with our novel
       Adaptive Level-of-Detail engine."
展示: 架构图中高亮 Gemini → ADK → Cloud Run → Firestore 连线

[1:00-1:45] 场景1 — 步行中的视觉识别
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
画面: 真实手机屏幕录制，对着一个建筑
操作:
  - 举起手机对着建筑
  - 说 "What am I looking at?"
  - Wanderer 用 LOD1 简洁回答 (因为在走路)
  - 说 "Tell me more"
  - Wanderer 过渡到 LOD2
展示要点: 视觉识别 + 语音交互 + LOD 自动调整

[1:45-2:30] 场景2 — 坐下来的深度叙事
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
画面: 咖啡馆场景
操作:
  - 坐下后说 "I've got time now. Tell me the full story."
  - Wanderer 进入 LOD3 叙事模式
  - 中途打断: "Wait, how tall is it?"
  - Wanderer 保存 Snapshot，简短回答
  - "Go on" → Wanderer 从 Snapshot 恢复
展示要点: LOD3 叙事 + Narrative Snapshot + 自然打断处理

[2:30-3:00] 场景3 — 摄像头模态切换
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
画面: 对准餐厅菜单
操作:
  - 摄像头扫过菜单
  - Wanderer 自动识别菜品并推荐
  - 结合 Google Places 评分
展示要点: 视觉理解 + Google 数据 Grounding + 实用场景

[3:00-3:30] 技术展示
━━━━━━━━━━━━━━━━━━━
画面: 分屏 — 左侧 GCP Console, 右侧应用
展示:
  - Cloud Run 服务运行状态
  - Firestore 数据面板
  - Cloud Logging 日志流
  - Architecture diagram (最终版)

[3:30-4:00] 总结与愿景
━━━━━━━━━━━━━━━━━━━━━━
画面: Wanderer logo + 使用场景蒙太奇
旁白: "Wanderer doesn't just respond. It adapts. It remembers.
       It sees what you see. And it knows exactly how much you
       need to know."
文字卡:
  - "5 specialized agents"
  - "3-level adaptive detail"
  - "6 Google Cloud services"
  - "Built with Gemini Live API + ADK"
```

### 9.2 Demo 视频制作注意事项

1. **必须是实时运行的软件** — 不能是 mockup 或预录旁白配假画面
2. **控制在 4 分钟以内** — 超时可能被扣分
3. **音频质量**: 用好的麦克风录制旁白，AI 语音要清晰可听
4. **多录几遍**: 至少录 3 遍，选最好的
5. **展示问题意识**: 开头 30 秒必须让评委明白你在解决什么问题
6. **展示真实场景**: 如果可能，在真实的户外场景录制 (更有说服力)
7. **展示 GCP**: 必须有 GCP Console 画面作为部署证明

### 9.3 架构图制作

推荐工具:
- **Excalidraw** (手绘风格，亲和力强)
- **draw.io/diagrams.net** (专业，免费)
- **Mermaid** (代码生成，版本控制友好)

架构图必须展示:
- 客户端 → Cloud Run → Gemini 的数据流
- Multi-Agent 架构 (5 个 Agent 的关系)
- Google Cloud 服务的连接
- 数据存储 (Firestore)
- 外部 API (Maps Platform)

---

## 10. 风险管理

### 10.1 高优先级风险

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| **ADK 学习曲线导致延期** | 中 | 高 | 前 3 天集中学习 ADK，使用官方 quickstart + samples，不要自己摸索 |
| **23天时间不够** | 高 | 高 | 严格按 Phase 优先级砍功能，P0 > P1 > P2 > P3。如果 Phase 2 延期，砍 Phase 3 的低优先级功能 |
| **视觉+音频同时流的复杂度** | 高 | 中 | Vision Agent 独立于 Voice Agent，异步处理。不要让视觉处理阻塞语音流 |
| **Gemini Live API 延迟不稳定** | 中 | 中 | 使用 `gemini-2.5-flash` 低延迟模型 + 客户端预缓冲 + LOD1 作为 fallback |

### 10.2 中优先级风险

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| **前端移动端适配** | 中 | 中 | 使用 PWA (Progressive Web App)，不做原生 App。优先保证 Chrome mobile 体验 |
| **Cloud Run 冷启动延迟** | 中 | 低 | 设置 min-instances=1，保持至少一个实例常驻 |
| **Firestore 延迟影响实时性** | 低 | 中 | 热数据用内存缓存，Firestore 作为持久化层异步写入 |
| **Demo 录制时网络不稳** | 中 | 高 | 使用本地 + 云端双模式，Demo 时优先用稳定网络 |
| **Gemini API 配额限制** | 低 | 高 | 提前申请更高配额，Demo 录制前测试 |

### 10.3 低优先级风险

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| **ADK 框架 Bug** | 低 | 中 | 关注 GitHub Issues，必要时用 GenAI SDK 直接调用 |
| **多语言支持复杂度** | 低 | 低 | 只做英语，不做多语言 (除非时间充裕) |
| **评审偏好不确定** | 中 | 中 | 覆盖所有三个评审维度，不偏科 |

### 10.4 应急方案 (如果严重延期)

**最小可行提交 (Minimum Viable Submission)**:

如果到 Day 16 还没完成 Phase 2，立即执行最小方案:
1. 保留: Voice Agent + LOD 系统 (基础版) + Cloud Run 部署
2. 砍掉: Vision Agent, Multi-Agent 架构, Preference Learning
3. 专注: Demo 视频质量 (30% 权重，投入产出比最高)

---

## 11. Bonus 加分项

### 11.1 发布内容 (#GeminiLiveAgentChallenge)

**建议**: 写一篇中等长度的博客 (Medium / Dev.to / 个人博客)

主题建议: "Building an Adaptive Voice Agent with Gemini Live API: How We Invented Level-of-Detail for Conversational AI"

内容大纲:
1. 问题: 为什么所有 AI 助手都是 one-size-fits-all
2. 方案: Adaptive LOD 系统的设计思路
3. 技术: Gemini Live API + ADK 的集成经验
4. 挑战: 视觉+语音+位置三模态协调的难点
5. 学习: 使用 Google Cloud 部署实时 Agent 的心得

发布时带上 `#GeminiLiveAgentChallenge` hashtag。

### 11.2 自动化云部署

**建议**: 使用 Terraform 或 gcloud CLI 脚本

```
部署脚本应该包含:
1. Cloud Run service 创建
2. Firestore database 初始化
3. Secret Manager secrets 设置
4. IAM 权限配置
5. 一键部署命令: `./deploy.sh`
```

放在仓库的 `infra/` 目录下，README 中注明 "Automated deployment with Infrastructure-as-Code"。

### 11.3 Google Developer Group

注册 Google Developer Group (https://developers.google.com/community/gdg)，在提交时提供公开 profile 链接。

---

## 12. 竞争对手分析与差异化

### 12.1 典型竞争对手画像

基于 1,623 参赛者，预计大多数项目会是:

| 类型 | 占比估计 | 典型特征 | 弱点 |
|------|---------|---------|------|
| **简单语音聊天** | 40% | Gemini + 语音，通用对话 | 无差异化，无深度 |
| **客服/助手类** | 25% | 特定领域问答，RAG 集成 | 不够 "immersive"，缺多模态 |
| **翻译/教育类** | 15% | 实时翻译、语言教学 | 创新性有限 |
| **创意/故事类** | 10% | 多模态叙事生成 | 技术深度可能不足 |
| **高水平竞争者** | 10% | 多模态 + 深度技术 | 你的直接竞争对手 |

### 12.2 你的护城河

| 差异化点 | 为什么竞争对手无法复制 |
|---------|---------------------|
| **LOD 系统** | 16,000+ 行代码，7个开发阶段的迭代，不是 23 天能从零实现的 |
| **Narrative Snapshot** | 需要深度理解叙事状态管理，不是简单的 "记住上下文" |
| **Topic-Aware State** | 需要话题检测 + 独立状态管理 + 恢复机制的组合 |
| **活动特化偏好学习** | 需要持续的反馈收集 + 学习率调优 + 多维偏好模型 |
| **三模态协同 (非堆砌)** | 视觉/语音/位置不是分开的，而是协同影响 LOD 决策 |

### 12.3 应对策略

对于 10% 的高水平竞争者:
1. **Demo 质量**: 投入足够时间打磨 Demo，确保场景真实、流畅
2. **技术叙事**: 在提交描述中清晰阐述 LOD 系统的学术价值
3. **架构深度**: Multi-Agent + 多 GCP 服务，展示系统工程能力
4. **Grounding**: 确保所有事实性回答有据可查

---

## 13. 参考资源

### 13.1 官方文档

| 资源 | 链接 |
|------|------|
| 比赛页面 | https://geminiliveagentchallenge.devpost.com/ |
| Gemini Live API 文档 | https://ai.google.dev/gemini-api/docs/live |
| Gemini Live API (Vertex) | https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api |
| ADK 官方文档 | https://google.github.io/adk-docs/ |
| ADK 流式指南 | https://google.github.io/adk-docs/streaming/ |
| ADK Python 快速开始 | https://google.github.io/adk-docs/get-started/python/ |
| ADK 流式快速开始 | https://google.github.io/adk-docs/get-started/streaming/quickstart-streaming/ |
| ADK Multi-Agent | https://google.github.io/adk-docs/agents/multi-agents/ |
| ADK Gemini 集成 | https://google.github.io/adk-docs/agents/models/google-gemini/ |

### 13.2 代码资源

| 资源 | 链接 |
|------|------|
| ADK Python GitHub | https://github.com/google/adk-python |
| ADK 样例代码 | https://github.com/google/adk-samples/tree/main/python/agents/ |
| ADK 流式开发指南 Part 1-5 | https://google.github.io/adk-docs/streaming/dev-guide/part1/ |

### 13.3 博客 & 教程

| 资源 | 链接 |
|------|------|
| Build a real-time voice agent with Gemini & ADK | https://cloud.google.com/blog/products/ai-machine-learning/build-a-real-time-voice-agent-with-gemini-adk |
| Build voice-driven applications with Live API | https://cloud.google.com/blog/products/ai-machine-learning/build-voice-driven-applications-with-live-api |
| Building Collaborative AI: Multi-Agent Systems with ADK | https://cloud.google.com/blog/topics/developers-practitioners/building-collaborative-ai-a-developers-guide-to-multi-agent-systems-with-adk |
| Google Codelabs: Multi-Agent with ADK | https://codelabs.developers.google.com/codelabs/production-ready-ai-with-gc/3-developing-agents/build-a-multi-agent-system-with-adk |

### 13.4 比赛策略参考

| 资源 | 链接 |
|------|------|
| Gemini Live Agent Challenge 解析 (algo-mania) | https://algo-mania.com/en/blog/hackathons-coding/gemini-live-agent-challenge-create-immersive-ai-agents-with-google-gemini-live/ |
| 2026 Top Hackathons | https://www.analyticsvidhya.com/blog/2026/01/top-hackathons-to-participate-in/ |

---

## 附录 A: 关键 ADK 代码模式

### A.1 基础 Agent 定义

```python
from google.adk.agents import LlmAgent

# Root Agent (Orchestrator)
orchestrator = LlmAgent(
    name="wanderer_orchestrator",
    model="gemini-2.5-pro",
    instruction="""You are Wanderer, an adaptive AI travel companion.
    You coordinate with specialized agents to provide context-aware
    responses with dynamic Level-of-Detail adjustment.""",
    sub_agents=[voice_agent, vision_agent, geo_agent, memory_agent],
    tools=[lod_tool, grounding_tool],
)
```

### A.2 流式 Voice Agent

```python
from google.adk.agents import LlmAgent

voice_agent = LlmAgent(
    name="voice_agent",
    model="gemini-2.5-flash-native-audio",
    instruction="Handle real-time voice interaction with the user.",
    # Voice configuration per LOD level
    generate_content_config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Kore"  # or dynamic per LOD
                )
            )
        ),
    ),
)
```

### A.3 ADK Streaming 入口

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

runner = Runner(
    agent=orchestrator,
    app_name="wanderer",
    session_service=InMemorySessionService(),
)

# FastAPI WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    live_request_queue = LiveRequestQueue()

    async def send_audio():
        async for event in runner.run_live(
            session_id=session_id,
            live_request_queue=live_request_queue,
            config=run_config,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.inline_data:
                        await websocket.send_bytes(part.inline_data.data)

    async def receive_audio():
        while True:
            data = await websocket.receive_bytes()
            live_request_queue.send_content(
                types.Content(
                    role="user",
                    parts=[types.Part(inline_data=types.Blob(
                        mime_type="audio/pcm",
                        data=data
                    ))]
                )
            )

    await asyncio.gather(send_audio(), receive_audio())
```

---

## 附录 B: iMeanPiper 关键文件路径索引

```
/Volumes/T7/work/iMean/iMeanPiper/
├── README.md                           # 项目文档
├── src/
│   ├── agent.py                        # 主 Agent 入口
│   ├── token_server.py                 # Token 服务
│   ├── lod/
│   │   ├── config.py                   # LOD 配置定义
│   │   ├── manager.py                  # LOD 状态管理器
│   │   ├── state.py                    # LOD 状态
│   │   ├── models.py                   # 核心数据模型
│   │   ├── models_intelligent.py       # 智能切换模型
│   │   ├── cold_start_engine.py        # 冷启动决策
│   │   ├── context_parser.py           # 上下文解析
│   │   ├── prompt_manager.py           # Prompt 管理
│   │   ├── tts_manager.py              # TTS 风格管理
│   │   ├── signal_detector.py          # 信号检测
│   │   ├── intent_classifier.py        # 意图分类
│   │   ├── transition_analyzer.py      # 过渡分析
│   │   ├── transition_handler.py       # 过渡处理
│   │   ├── interrupt_handler.py        # 中断处理
│   │   ├── segmented_generator.py      # 分段生成
│   │   ├── buffered_llm.py             # LLM 缓冲
│   │   ├── narrative_tracker.py        # 叙事追踪
│   │   ├── snapshot_manager.py         # 叙事快照
│   │   ├── topic_aware_manager.py      # 话题感知管理
│   │   ├── topic_state.py              # 话题状态
│   │   ├── topic_detector.py           # 话题检测
│   │   ├── agent_mixin.py              # Agent 混入
│   │   ├── enhanced_agent_mixin.py     # 增强混入
│   │   ├── enhanced_context.py         # 增强上下文
│   │   ├── enhanced_manager.py         # 增强管理器
│   │   ├── memory_storage.py           # 记忆存储
│   │   ├── data_loader.py              # 数据加载
│   │   ├── checkpoint.py               # 检查点
│   │   ├── debug_api.py                # 调试 API
│   │   ├── sanitization.py             # 输出净化
│   │   ├── trace_collector.py          # 追踪收集
│   │   ├── geo/                        # 地理模块
│   │   │   ├── geo_models.py
│   │   │   ├── google_services.py
│   │   │   ├── geo_enhancer.py
│   │   │   ├── poi_resolver.py
│   │   │   ├── poi_ranker.py
│   │   │   └── geo_prompt.py
│   │   ├── travel/                     # 旅行模块
│   │   │   ├── travel_models.py
│   │   │   ├── trip_manager.py
│   │   │   ├── trip_detector.py
│   │   │   └── trip_memory.py
│   │   └── preference/                 # 偏好模块
│   │       ├── preference_models.py
│   │       ├── preference_learner.py
│   │       └── feedback_collector.py
│   ├── data/                           # 示例数据
│   │   ├── users/
│   │   ├── pois/
│   │   └── trips/
│   ├── gui/                            # React 前端
│   │   └── src/
│   │       ├── components/             # 11 个组件
│   │       └── hooks/                  # 7 个 Hooks
│   └── scripts/                        # 启动脚本
│       ├── start_agent.sh
│       ├── start_token_server.sh
│       └── start_gui.sh
└── dev/
    ├── docs/                           # 开发文档
    ├── debug/
    ├── demo/
    ├── logs/
    └── tests/
```

---

*本报告基于 2026-02-21 对比赛要求和 iMeanPiper 项目的深度分析生成。*
*比赛截止日期: 2026-03-16, 请严格按照冲刺计划执行。*
