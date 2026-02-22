# SightLine Subtasks & Roadmap (Rebuilt)

> Version: 2.0 (Clean Foundation)
> Last Updated: 2026-02-22
> Deadline: 2026-03-16 17:00 PDT
> Delivery Track: Swift Native iOS + Cloud Run ADK Server-to-Server
> Status: Active

---

## 0. Document Foundation (Single Source of Truth)

| Priority | Document | Role |
|---|---|---|
| L0 | `docs/SightLine_Final_Specification.md` | 产品与技术最终规格（功能边界、架构、评分策略） |
| L0 | `docs/SightLine_Consolidated_Development_Reference.md` | 跨文档矛盾裁定与开发统一口径 |
| L1 | `SightLine/CLAUDE.md` | 开发硬约束（环境、模型、版本、Git 规范、操作日志要求） |
| L1 | `SightLine/dev/docs/operation_log.md` | 已完成环境与基础设施的事实记录 |
| L1 | `SightLine/dev/docs/SightLine_Environment_Setup_Guide.md` | 本地/云端依赖安装与版本说明 |
| L2 | `docs/engine/Context_Engine_Implementation_Guide.md` | Context/LOD 具体实现指南 |
| L2 | `docs/engine/Memory_System_Research_and_Integration.md` | Memory 方案选型与集成路径 |

### 0.1 Frozen Decisions (Do Not Re-open During Hackathon)

1. 架构固定为 **Server-to-Server**：iOS -> Cloud Run -> Gemini Live API（不做前端直连）。
2. 前端固定为 **Swift Native iOS + watchOS**（PWA 路线全部废弃）。
3. LOD 决策引擎为 **规则引擎**（毫秒级），非 LLM 判定。
4. `step_cadence` 单位统一为 **steps/minute**。
5. LOD 3 静止场景视频帧率统一为 **0.3-0.5 FPS**。
6. Memory 首选 **Vertex AI Memory Bank**，Mem0 仅 fallback。
7. 导航能力作为 **Orchestrator 的 function tool**，不是独立 Sub-Agent。
8. 模型名必须按平台切换：
   - Gemini Developer API: `gemini-2.5-flash-native-audio-preview-12-2025`
   - Vertex AI: `gemini-live-2.5-flash-native-audio`
9. Python 运行环境固定：`conda activate sightline`（Python 3.12）。

---

## 1. Baseline Snapshot (As-Is)

### 1.1 Environment & Infra Status

| Item | Status | Evidence |
|---|---|---|
| Conda `sightline` + Python 3.12 | DONE | `operation_log.md` 阶段 2 |
| 核心依赖安装（ADK/Firestore/InsightFace/ONNX/Maps） | DONE | `operation_log.md` 阶段 3 |
| InsightFace `buffalo_l` 模型安装验证 | DONE | `operation_log.md` 阶段 4 |
| GCP API 启用（11 个） | DONE | `operation_log.md` 阶段 5.2 |
| Firestore Native + 向量索引（512/2048） | DONE | `operation_log.md` 阶段 5.3/5.6 |
| Secret Manager（Gemini/Maps key） | DONE | `operation_log.md` 阶段 5.5 |
| SA + IAM 角色 | DONE | `operation_log.md` 阶段 5.4/5.9 |
| Firebase CLI + MCP 配置 | DONE（需按会话确认登录状态） | `operation_log.md` 阶段 5.10/6.4 |

### 1.2 Codebase Reality Check

| Area | Current State | Gap |
|---|---|---|
| iOS | 仅 Xcode skeleton（`ContentView.swift`, `SightLineApp.swift`） | 需要完整音视频/传感器/WebSocket 管线 |
| Backend | 尚未落地 `FastAPI + ADK run_live` 主链路 | 需要从 0 到可用服务 |
| Agents/Tools | 尚未实现 | 需要按 Phase 逐步实现 |
| Tests/CI | 尚未建立 | 需要最小可用验证与回归保障 |

---

## 2. Milestones & Timeline

| Milestone | Date Range | Goal |
|---|---|---|
| M0 | 2026-02-22 | 基线确认与任务拆分冻结（本文件） |
| M1 | 2026-02-22 ~ 2026-02-26 | 打通端到端 Live 音视频主链路（本地 + Cloud Run） |
| M2 | 2026-02-27 ~ 2026-03-03 | 完成 LOD + Context Fusion + Telemetry 驱动 |
| M3 | 2026-03-04 ~ 2026-03-08 | 完成 Vision/OCR/Nav/Search/FaceID 核心能力 |
| M4 | 2026-03-09 ~ 2026-03-12 | Memory + 稳定性 + 演示质量打磨 |
| M5 | 2026-03-13 ~ 2026-03-16 | Demo、文档、提交流程闭环 |

---

## 3. Subtasks (Unified IDs)

### Phase 0 - Completed Foundations (Carry Forward, No Rework)

| ID | Subtask | Priority | Status | Deliverable |
|---|---|---|---|---|
| SL-00 | 锁定 Python 3.12 + `sightline` Conda 环境 | P0 | DONE | 可复现本地运行环境 |
| SL-01 | 安装并验证后端核心依赖 | P0 | DONE | `requirements.txt` + 导入验证 |
| SL-02 | 安装 InsightFace 模型并验证推理 | P0 | DONE | `~/.insightface/models/buffalo_l` |
| SL-03 | 创建并配置 GCP 项目与 API | P0 | DONE | `sightline-hackathon` 可用 |
| SL-04 | Firestore + 向量索引初始化 | P0 | DONE | `face_library` / `memories` index READY |
| SL-05 | Secret Manager + SA + IAM | P0 | DONE | 密钥/角色可用 |
| SL-06 | Firebase CLI/MCP 基础配置 | P1 | DONE | MCP 可连通（会话态认证） |

### Phase 1 - Core Live Loop (M1)

| ID | Subtask | Priority | Status | Depends | Deliverable | Acceptance |
|---|---|---|---|---|---|---|
| SL-10 | 建立后端目录骨架（`agents/`, `live_api/`, `lod/`, `telemetry/`, `tools/`） | P0 | DONE | SL-00 | 清晰模块结构 | 目录与模块可导入 |
| SL-11 | 实现 `FastAPI` WebSocket 入口 `/ws/{user_id}/{session_id}` | P0 | DONE | SL-10 | 可持续连接通道 | 能收发 JSON/bytes |
| SL-12 | 接入 ADK `Runner.run_live()` + `LiveRequestQueue` | P0 | DONE | SL-11 | 后端到 Gemini Live 通路 | 能收到 Live 事件流 |
| SL-13 | 实现 `RunConfig` 基线（BIDI/AUDIO/transcription/proactive/affective） | P0 | DONE | SL-12 | 正确配置 Live 会话 | 语音首包返回 < 3s |
| SL-14 | 启用 `SessionResumptionConfig` + handle 缓存 | P0 | DONE | SL-13 | 10 分钟连接可续接 | 人工断线后可恢复上下文 |
| SL-15 | 启用 `ContextWindowCompression` + SlidingWindow | P0 | DONE | SL-13 | 音视频会话不在 2 分钟硬断 | 连续会话 > 5 分钟 |
| SL-16 | 实现上行协议解析（audio/image/telemetry/activity_start/end） | P0 | DONE | SL-11 | 统一消息协议 | 5 类消息全通过 |
| SL-17 | 实现下行事件转发（audio bytes + transcription text） | P0 | DONE | SL-12 | 前端可实时播放与显示字幕 | 音频连续播放无阻塞 |
| SL-18 | iOS `WebSocketManager`（NWConnection）实现 | P0 | DONE | SL-11 | iOS 到后端稳定连接 | 连续 10 分钟不掉线 |
| SL-19 | iOS 音频链路（`AVAudioEngine` 采集 16k + `AVAudioPlayerNode` 播放 24k） | P0 | DONE | SL-18 | 实时双向语音 | 用户可对话 |
| SL-20 | iOS 视频链路（`AVCaptureSession` -> JPEG 768x768） | P0 | DONE | SL-18 | 1 FPS 帧上传 | 后端收到图像帧 |
| SL-21 | Cloud Run 首次部署（`min_instance_count=1`） | P0 | DONE | SL-12 | 云端可访问服务 | 远端真机可连通 |

### Phase 2 - LOD & Context Engine (M2)

| ID | Subtask | Priority | Status | Depends | Deliverable | Acceptance |
|---|---|---|---|---|---|---|
| SL-30 | iOS 传感器聚合（motion/cadence/noise/gps/time/hr） | P0 | DONE | SL-18 | 标准 telemetry payload | 字段完整率 > 95% |
| SL-31 | LOD-aware Telemetry 节流（LOD1:3-4s / LOD2:2-3s / LOD3:5-10s） | P0 | DONE | SL-30 | 发送策略稳定 | 高频抖动可控 |
| SL-32 | 后端 Telemetry 语义化解析与标准化 | P0 | DONE | SL-16 | Ephemeral Context 输入 | 可供 LOD 引擎直接消费 |
| SL-33 | 规则式 LOD 决策引擎（panic/motion/noise/context） | P0 | DONE | SL-32 | LOD 1/2/3 稳定决策 | 单元测试覆盖关键分支 |
| SL-34 | PANIC 中断机制（清空播放队列 + 强制 LOD1） | P0 | DONE | SL-33 | 安全优先中断 | 触发后 < 500ms 生效 |
| SL-35 | Dynamic System Prompt 构建器（persona->rules->guardrails） | P0 | DONE | SL-33 | LOD 感知 prompt | 输出结构固定可审计 |
| SL-36 | LOD 驱动 VAD 参数动态切换 | P1 | DONE | SL-33 | LOD 级别下交互差异化 | 误打断率下降 |
| SL-37 | Narrative Snapshot（降级保存、恢复续读） | P1 | DONE | SL-33 | 打断恢复能力 | 恢复点偏差 <= 1 段 |
| SL-38 | 断线本地降级（iOS force LOD1 + 触觉 + 本地语音提示） | P1 | DONE | SL-18 | 网络异常安全回退 | 断网即时提示 |
| SL-39 | LOD Decision Log（可解释日志） | P0 | DONE | SL-33 | 每次决策可追踪 | 日志含输入/规则/结果 |

### Phase 3 - Agent Capabilities & Tools (M3)

| ID | Subtask | Priority | Status | Depends | Deliverable | Acceptance |
|---|---|---|---|---|---|---|
| SL-50 | Vision Sub-Agent（`gemini-3.1-pro-preview`） | P0 | TODO | SL-12 | 场景理解能力 | 对典型场景输出稳定 |
| SL-51 | Proactive-Oriented Vision Prompt（按 LOD 分级提取） | P1 | TODO | SL-50 | LOD1安全/LOD2导航/LOD3全量 | 输出与 LOD 对齐 |
| SL-52 | OCR Sub-Agent（`gemini-3-flash-preview`） | P1 | TODO | SL-12 | 菜单/标识朗读 | OCR 场景通过率 > 90% |
| SL-53 | `navigate_location()` tool（Maps/Routes/Geocoding） | P1 | TODO | SL-12 | 基础导航说明 | 返回时钟方位可用 |
| SL-54 | `google_search()` grounding tool | P1 | TODO | SL-12 | 外部事实校验 | 响应可附来源摘要 |
| SL-55 | tool behavior 策略（INTERRUPT/WHEN_IDLE/SILENT） | P0 | TODO | SL-53 | 工具调用调度稳定 | 不打断主对话节奏 |
| SL-56 | Face pipeline（InsightFace detection + embedding + match） | P2 | TODO | SL-02, SL-12 | 人脸识别服务能力 | 单帧匹配延迟 < 300ms |
| SL-57 | 人脸注册流程（helper 模式 + 多样本） | P2 | TODO | SL-56 | 可维护 face library | 单人 3-5 样本入库 |
| SL-58 | `identify_person()` 集成（SILENT 注入） | P2 | TODO | SL-56 | 身份信息自然融合 | 不产生硬打断 |
| SL-59 | Face 数据删除/隐私 API（清除机制） | P2 | TODO | SL-57 | 隐私合规操作 | 一键清空可验证 |

### Phase 4 - Memory, Reliability, Demo Hardening (M4)

| ID | Subtask | Priority | Status | Depends | Deliverable | Acceptance |
|---|---|---|---|---|---|---|
| SL-70 | SessionService 从 InMemory 迁移到 VertexAiSessionService | P1 | TODO | SL-12 | 会话持久化 | 重启后会话可恢复 |
| SL-71 | 接入 VertexAiMemoryBankService + PreloadMemoryTool | P1 | TODO | SL-70 | 长期记忆基础链路 | top-K 记忆可注入 prompt |
| SL-72 | Memory 提取策略 + 写入预算（max 5/session） | P1 | TODO | SL-71 | 记忆膨胀受控 | 每会话写入上限生效 |
| SL-73 | Memory 检索排序（relevance/recency/importance） | P2 | TODO | SL-71 | 相关记忆优先 | 检索结果质量可解释 |
| SL-74 | `forget_recent_memory()` 预留接口 | P2 | TODO | SL-71 | 用户可撤销近期记忆 | 删除后不可检索 |
| SL-75 | 性能优化：帧去重、预反馈、流式播放细化 | P0 | TODO | SL-20 | 感知延迟优化 | 首响应体验明显改善 |
| SL-76 | 稳定性矩阵：断网/GoAway/API异常/摄像头失败 | P0 | TODO | SL-14 | 可预期降级路径 | 关键异常全可恢复 |
| SL-77 | DebugOverlay（LOD/Telemetry/Latency/Memory Top3） | P1 | TODO | SL-39 | 演示可观测面板 | 评委可见因果链路 |
| SL-78 | 最小测试集（unit + e2e smoke） | P0 | TODO | SL-33 | 回归保障 | 关键路径自动化通过 |

### Phase 5 - Demo & Submission (M5)

| ID | Subtask | Priority | Status | Depends | Deliverable | Acceptance |
|---|---|---|---|---|---|---|
| SL-90 | 锁定 4 分钟脚本与 4 个关键场景 | P0 | TODO | SL-75 | 演示脚本 V1 | 全员可按脚本走通 |
| SL-91 | 端到端彩排与故障清单修复 | P0 | TODO | SL-90 | 彩排报告 | 连续彩排 3 次通过 |
| SL-92 | 架构图定稿（数据流+Agent+GCP） | P0 | TODO | SL-91 | 可提交图片 | 与实现一致 |
| SL-93 | Demo 视频录制与剪辑（<=4 分钟） | P0 | TODO | SL-91 | 提交视频文件 | 时长/叙事符合要求 |
| SL-94 | README + 启动说明 + 已知限制 | P0 | TODO | SL-91 | 仓库说明完备 | 新成员可按文档启动 |
| SL-95 | Devpost 文案 + 云部署证据整理 | P0 | TODO | SL-92 | 提交文案包 | 与视频一致 |
| SL-96 | 可选加分：Terraform、技术博客、GDG | P2 | TODO | SL-95 | Bonus 资产 | 不影响 P0 提交 |
| SL-97 | 最终提交与回执存档 | P0 | TODO | SL-93, SL-95 | 提交完成 | 截止前完成确认 |

---

## 4. Critical Path

`SL-11 -> SL-12 -> SL-13 -> SL-21 -> SL-33 -> SL-50 -> SL-53 -> SL-75 -> SL-91 -> SL-93 -> SL-97`

说明：任何关键路径节点延迟超过 1 天，必须触发 Cut-Line。

---

## 5. Cut-Line (If Schedule Slips)

| Tier | Keep / Cut | Decision |
|---|---|---|
| Tier A (Never Cut) | LOD Engine、Vision、Cloud 部署、Demo 视频、最终提交 | 必须保留 |
| Tier B (Cut Last) | OCR、Maps 导航、Grounding、稳定性 hardening | 次优先保留 |
| Tier C (Cut Earlier) | Face ID、Memory 深化、DebugOverlay 高级指标 | 时间不足时可降级 |
| Tier D (Cut First) | Terraform bonus、博客 bonus | 首先砍掉 |

---

## 6. Immediate Next 10 Tasks (Execution Queue)

1. `SL-10` 后端目录骨架建立。
2. `SL-11` WebSocket 入口完成。
3. `SL-12` ADK `run_live()` 接通。
4. `SL-13` RunConfig 基线可运行。
5. `SL-18` iOS WebSocket 接入。
6. `SL-19` iOS 音频采集与播放。
7. `SL-20` iOS 视频帧上传。
8. `SL-21` Cloud Run 首次部署。
9. `SL-30` iOS Telemetry 聚合。
10. `SL-33` 规则式 LOD 决策引擎。

---

## 7. Maintenance Rules

1. 所有状态变更必须同步更新本文件 `Status` 字段和 `SightLine/dev/docs/operation_log.md`。
2. 新任务必须使用 `SL-xx` 编号，不允许临时命名。
3. 出现跨文档冲突时，按 `L0 -> L1 -> L2` 顺序裁定并记录到本文件顶部。
4. 每日收工前更新：完成项、阻塞项、次日 Top 3。

