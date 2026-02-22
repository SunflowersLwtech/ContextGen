# SightLine 架构最佳实践与去幻觉审查报告 (2026-02)

> **关于本项目**：SightLine 是为视障人士开发的无障碍感官伴侣，对**实时性、稳定性和低延迟**的要求远超普通应用。基于这个极其严肃的背景，我依据 2025-2026 年 Google / Firebase 最新官方文档，对现有的架构设计进行了深度审查。

## 1. 核心架构缺陷：过度包装的“胶水代码” (Cloud Run WebSocket Proxy)

### 🔴 现有实现 (不推荐)
**架构链路**：iOS App 捕获音视频及传感器数据 -> 通过 WebSocket 将所有数据打包发往 Cloud Run -> Cloud Run (FastAPI + ADK) 作为中间件 -> 再转用 WebSocket (LiveRequestQueue) 连接 Gemini Live API。
**问题分析**：这是典型的大模型时代早期（2024年初前）为了保护 API Key 或由于客户端 SDK 不成熟而产生的“手搓网关”幻觉。在 Cloud Run 上用 Python 维护双向实时的高频音视频流不仅增加了几百毫秒的网络跳跃延迟，还会因为容器扩缩容、WebSocket Session 保持等问题引入极大的复杂性（即你们所说的“写那么多胶水代码”）。

### 🟢 官方最佳实践
**原生方案**：**Firebase AI Logic (曾用名 Vertex AI in Firebase) iOS SDK**。
Google 已经正式为 iOS/Swift 平台提供了支持 **Gemini Multimodal Live API（双向流传输）** 的原生客户端 SDK。
- **极简架构**：iOS App **直接**使用原生 Swift SDK 与 Gemini Live API 建立安全连接。音视频流直接从手机传输到 Google 服务器。
- **安全性**：不需要为了隐藏 API Key 而设置 Cloud Run。Firebase 提供了 **App Check**（结合 Apple DeviceCheck/App Attest），自动防止未授权的客户端调用。
- **优化成果**：彻底砍掉 Cloud Run 作为 WebSocket “二传手”的所有胶水代码，大幅降低延迟，更符合白杖和导盲犬用户的安全响应需求（PANIC 模式响应将达毫秒级）。

---

## 2. Agent 编排模式的演进：Client-Side Tool Calling

### 🔴 现有实现
Cloud Run 作为 Orchestrator，通过 Google ADK 挂载各类 Tool 和 Sub-Agent。

### 🟢 官方最佳实践
当 iOS 客户端直接连接 Gemini Live API 时，Function Calling (Tools) 可以**直接在客户端进行注册和执行**。
- **轻量本地工具**：对于获取 GPS、分析步频 (Telemetry)，客户端直接在本地执行 Function 并将结果 (`ToolResponse`) 返回给模型。不再需要把遥测数据通过 Hack 的 `[TELEMETRY UPDATE]` 文本强行注入上下文。
- **无状态微服务 (Serverless)**：对于需要在云端重算力的任务（如 InsightFace 人脸识别、连接 Firestore 进行 2048维 Vector Search 的 MemoryBank），**Cloud Run 从“长连接网关”降级为单纯的“REST API 微服务”**。
- **流程**：Gemini Live 决定调用 `identify_person` -> 客户端拦截 Tool Call -> 客户端发起一个普通的 HTTPS POST 请求到 Cloud Run `/api/face-id` -> 客户端拿到结果后告知 Gemini。
**这种“胖客户端 + 无状态微服务扩展”是目前 Mobile Agentic App 最官方推荐的高可用架构。**

---

## 3. 关于 Google ADK (Agent Development Kit) 的应用

### 🧐 审查结论：选型正确，但放错了位置
当前项目使用了 Google ADK 并且发现它不自动映射 Live API 模型名称。
**审查结果**：使用 ADK 本身**不是幻觉**。ADK 是 Google 官方开源的生产级 Agent 框架，特别擅长和 GCP（Vertex AI Agent Engine、Cloud Run）深度集成，对标 LangGraph。
**调整建议**：对于极强实时要求的 Orchestrator 中心，让 ADK 接管 Live 流会受制于中间层瓶颈。建议将 **ADK 专门用于后端的 Sub-Agents**（如：在会话结束后用于深入总结记忆的 Agent，或负责执行长耗时检索的后台 Agent），而实时的交互中心交给客户端 SDK。

---

## 4. 记忆系统：自建 MemoryBank vs 原生方案

### 🧐 审查结论：非常有价值的造轮子（保留现状）
文档提到：放弃了官方原生的 `VertexAiMemoryBankService`，耗费 ~340 行代码自建了拥有提取、写入预算(Budget)控制、余弦相似度合并的 Firestore `MemoryBankService`。
**评估**：这**不是幻觉，而是高级开发者的务实决策**。现阶官方的原生 Agentic Memory 虽然集成方便，但在细粒度的控制上（基于置信度的强过滤、动态截断、明确的“忘掉刚才那句话”功能）存在黑盒盲区。你们利用 Firestore 原生的 2048 维 Vector Search 自建 Memory 模块是极其正确的，在生产环境中具有极强的可控性。这一块**建议保留，这是最佳实践的体现**。

---

## 5. 开发建议与行动项总结

为了让 SightLine 成为一个真正稳定的无障碍基础设施（OS 级），而不是一个笨重的 Server 包装器，建议执行以下重构：

| # | 重构方向 | 实施方法 | 节省的代码与资源 |
|---|---------|---------|----------------|
| **1** | **去网关化 (Decouple Proxy)** | 在 iOS 工程中引入 `Firebase AI Logic` 原生 SDK。将 LiveRequestQueue 的逻辑由 Swift 客户端直接接管。 | 砍掉 Cloud Run 项目中所有与 WebSocket 维持、异步队列相关的复杂 Python 代码。 |
| **2** | **安全防护原生化** | 废弃在 Secret Manager 手动挂载 `GEMINI_API_KEY` 给全端用的方案。在 Firebase Console 中开启 **App Check** 保护 Gemini API 调用。 | 避免 API 被滥刷，无需自己写鉴权中间件。 |
| **3** | **后端降维** | 将 Cloud Run 项目大幅瘦身。它只暴露出供 iOS App 调用的 REST 接口（如 FastAPI 的 `@app.post("/face-detect")`）。 | 服务器无需处理音视频流，费用和并发承载力获得指数级改善。 |
| **4** | **Telemetry 原生注入** | iOS 每次向 Gemini Live 发起交互时，借助 Client-Side Function Calling 或是 `SystemInstruction` 动态更新，传递传感器状态。 | 不必自己解析并融合传感器 JSON，模型理解也更精准。 |

> **结语**：作为一款为视障人士负责的产品，从“手搓后端中转流”转变为“客户端直连原生流 + 云端微服务辅助”的现代架构，将从根本上解决系统复杂性，将延迟降到物理极限（即纯公网网络延迟 + 模型推理延迟），避免中间件处理音频导致的额外卡顿。
