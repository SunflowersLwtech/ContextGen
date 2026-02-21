# Context-Driven Response Engine: Open-Source Frameworks Comparison

> Research Date: 2026-02-21
> Scope: RAG 框架、记忆引擎、Agent 编排、实时上下文聚合

---

## 1. Context-Aware AI Engines

### 1.1 ContextAgent (NeurIPS 2025)

| 属性 | 详情 |
|------|------|
| **功能** | 首个上下文感知*主动* LLM Agent 框架。从感官感知（第一人称视频、可穿戴音频）和人格上下文（用户习惯、偏好）中提取信息，预测何时需要主动协助以及调用哪些工具 |
| **Context/Memory 处理** | 两层上下文提取：(1) 感官上下文——来自连续第一人称摄像头/音频流；(2) 人格上下文——来自历史用户交互模式。上下文感知推理器融合两者以决定是否说话和说什么 |
| **License** | Open source ([GitHub: openaiotlab/ContextAgent](https://github.com/openaiotlab/ContextAgent)) |
| **社区** | 学术项目（NeurIPS 2025）；GitHub 仓库近期发布；小但在增长 |
| **与 SightLine 的关系** | **非常高** -- 最接近 SightLine 架构的学术类比。主动预测机制（基于传感器 + 人格上下文决定何时说话）直接映射到 SightLine 的 LOD 系统。第一人称可穿戴优先设计和 ContextAgentBench（1,000 样本，9 个日常场景，20 个工具）提供了 SightLine 可以采用的验证方法论 |

### 1.2 ContextLLM (ACM 2025)

| 属性 | 详情 |
|------|------|
| **功能** | 通过分层 LLM 管道将稀疏传感器/设备数据转化为丰富的描述性上下文。Layer 1：原始可穿戴数据收集。Layer 2：稀疏推理聚合。Layer 3：有意义的上下文描述生成 |
| **Context/Memory 处理** | 分层聚合——原始信号逐步丰富为自然语言上下文描述，然后注入 LLM prompt |
| **License** | 学术发表（ACM）；实现状态不明 |
| **与 SightLine 的关系** | **高** -- 三层传感器到上下文的管道在架构上类似于 SightLine 的 Ephemeral/Session/Long-term 上下文层级。将原始传感器读数转化为自然语言上下文再供 LLM 消费的方法直接适用 |

---

## 2. RAG Frameworks with User-Specific Memory

### 2.1 LlamaIndex

| 属性 | 详情 |
|------|------|
| **功能** | 领先的 LLM 应用数据框架。提供 300+ 数据源连接器、高级索引/检索、Agent 工作流。现在也是文档 Agent 和 OCR 平台 |
| **Context/Memory 处理** | 支持可组合索引、子问题查询分解和流式数据摄入。记忆基于索引——对话历史和用户数据存储为可检索索引 |
| **License** | Open source (MIT). [GitHub: run-llama/llama_index](https://github.com/run-llama/llama_index) |
| **GitHub Stars** | ~42,000+ |
| **与 SightLine 的关系** | **中等** -- 适合构建长期记忆检索层（用户偏好、已知位置、历史交互）。不太适合 SightLine 需要的实时、亚秒级传感器融合管道。可作为当前 SightLine 架构中 Memory Sub-Agent 的检索后端 |

### 2.2 LangChain + LangGraph

| 属性 | 详情 |
|------|------|
| **功能** | LangChain：连接 LLM 与工具、记忆和数据源的综合编排框架。LangGraph：构建在 LangChain 之上，将 Agent 工作流建模为有状态有向图，支持循环、分支和持久检查点 |
| **Context/Memory 处理** | 三个记忆层：**对话记忆**（聊天历史）、**实体记忆**（提取的实体事实）、**摘要记忆**（压缩的对话摘要）。LangGraph 添加**线程范围短期记忆**（通过检查点）和**跨会话长期记忆**（通过持久存储）。Redis 集成实现高性能实时记忆检索 |
| **License** | Open source (MIT). [GitHub](https://github.com/langchain-ai/langchain) / [LangGraph](https://github.com/langchain-ai/langgraph) |
| **GitHub Stars** | LangChain: ~70,000+ / LangGraph: ~11,700+（但 420 万月下载量） |
| **与 SightLine 的关系** | **中等** -- LangGraph 的有状态图方法很好地映射到 SightLine 的 Orchestrator 到 Sub-Agent 路由。实体记忆层可存储用户特定上下文（已知面孔、地点）。然而，SightLine 使用 Google ADK 进行编排并原生使用 Gemini，采用 LangChain 会增加不必要的抽象层。最好作为参考架构而非直接依赖 |

### 2.3 Haystack (by deepset)

| 属性 | 详情 |
|------|------|
| **功能** | 构建生产就绪 RAG 管道、Agent 和多模态搜索系统的开源 AI 框架。强调管道即 DAG 架构，每个组件（检索器、阅读器、生成器、路由器）都是模块化、可替换的节点 |
| **Context/Memory 处理** | 显式管道中心方法：记忆、检索、路由和生成是独立的 DAG 节点。支持多步决策流的分支和循环管道。管道可序列化、云无关且 Kubernetes 就绪 |
| **License** | Open source (Apache 2.0). [GitHub](https://github.com/deepset-ai/haystack) |
| **GitHub Stars** | ~18,000+ |
| **与 SightLine 的关系** | **低-中** -- 干净的管道架构是 SightLine Sub-Agent 路由的好参考，但 Haystack 针对文档检索/搜索优化，而非实时传感器融合 |

### 2.4 Letta (formerly MemGPT)

| 属性 | 详情 |
|------|------|
| **功能** | 构建具有持久、自编辑记忆的有状态 Agent 的平台。首创 LLM 的 OS 式记忆层级：将上下文窗口视为"RAM"，外部存储视为"磁盘"，Agent 自主管理数据在层级间的移动 |
| **Context/Memory 处理** | **Core Memory（上下文内，类似 RAM）**：始终可见的用户和角色事实。**Archival Memory（外部，类似磁盘）**：通过 embedding 可搜索的无限长期存储。**Recall Memory**：可搜索的对话历史。Agent 使用自编辑记忆循环自主决定何时在各层级间读/写/搜索 |
| **License** | Open source (Apache 2.0). [GitHub: letta-ai/letta](https://github.com/letta-ai/letta) |
| **GitHub Stars** | ~38,000+（MemGPT + Letta 合计） |
| **与 SightLine 的关系** | **高** -- OS 式记忆层级（core/archival/recall）与 SightLine 的三层上下文模型（Ephemeral/Session/Long-term）是强概念匹配。自编辑记忆循环——Agent 决定记住什么和忘记什么——映射到 SightLine 的"Narrative Snapshot"功能。Agent 文件（.af）格式用于序列化 Agent 状态可用于持久化用户档案 |

---

## 3. Memory & Personalization Engines

### 3.1 Mem0

| 属性 | 详情 |
|------|------|
| **功能** | AI 应用的通用记忆层。自动从对话中提取事实、偏好和上下文信息，存储在混合数据存储中（向量 + 图）。提供按相关性、重要性和时近性排名的智能检索 |
| **Context/Memory 处理** | **自动提取**：LLM 从每次交互中提取关键信息无需显式开发者工具化。**混合存储**：结合向量搜索和结构化存储。**智能排名**：考虑相关性、重要性、时近性和衰减。**持续学习**：自动更新/细化记忆，解决矛盾。支持用户级、会话级和 Agent 级记忆范围 |
| **License** | Open source core (Apache 2.0) + managed cloud. [GitHub: mem0ai/mem0](https://github.com/mem0ai/mem0) |
| **GitHub Stars** | ~41,000+（1400 万下载量，每季度 1.86 亿 API 调用） |
| **与 SightLine 的关系** | **高** -- Mem0 的自动偏好提取和用户范围记忆直接适用于 SightLine 的长期用户档案系统（偏好冗余度、已知位置、压力触发器）。相关性/时近性排名与 SightLine 在正确时间呈现正确长期上下文的需求一致。可作为 Memory Sub-Agent 的后端，替代或增强 Firestore 向量搜索 |

### 3.2 Zep (powered by Graphiti)

| 属性 | 详情 |
|------|------|
| **功能** | 基于时序知识图谱的上下文工程平台。捕获不断演变的用户交互和业务数据作为理解关系如何随时间变化的图谱。Zep 是商业平台；Graphiti 是底层开源引擎 |
| **Context/Memory 处理** | **时序知识图谱**：实体和关系带有时间戳，支持"用户上周偏好什么 vs 现在"的查询。**增量更新**：新数据集成无需重新计算整个图谱。**关系感知检索**：超越向量相似性理解事实间的语义连接。在 Deep Memory Retrieval 基准上以最高 18.5% 的准确率和 90% 更低的延迟超越 MemGPT |
| **License** | Graphiti: open source. [GitHub: getzep/graphiti](https://github.com/getzep/graphiti)（~20,000 stars）。Zep 平台：商业带免费层 |
| **与 SightLine 的关系** | **中-高** -- 时序知识图谱用于跟踪用户偏好、熟悉路线和压力模式如何随时间演变很有吸引力。增量更新模型适合 SightLine 的持续学习需求。但图谱查询开销对实时 Ephemeral 上下文路径可能太重。最适合 Long-term 上下文层 |

### 3.3 CrewAI

| 属性 | 详情 |
|------|------|
| **功能** | 基于角色的 AI Agent 协作的多 Agent 编排框架。Agent 被分配专门角色并通过共享上下文和记忆协作 |
| **Context/Memory 处理** | 四种记忆类型：**短期**（任务内）、**长期**（跨任务学习）、**实体记忆**（特定实体事实）和**上下文记忆**（情境感知上下文） |
| **License** | Open source (MIT). [GitHub: crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) |
| **GitHub Stars** | ~44,000+ |
| **与 SightLine 的关系** | **低-中** -- 多 Agent 角色模式概念上类似 SightLine 的 Sub-Agent 架构。但 SightLine 已用 Google ADK 进行编排。CrewAI 的记忆系统更多关于 Agent 间协作而非用户个性化。作为设计参考有用 |

---

## 4. Real-Time Context Aggregation Platforms

### 4.1 Dify

| 属性 | 详情 |
|------|------|
| **功能** | 构建 Agentic AI 工作流的生产就绪平台，带可视化工作流构建器。支持 RAG 管道、工具使用 Agent、prompt 编排和多模型集成 |
| **License** | Open source. [GitHub: langgenius/dify](https://github.com/langgenius/dify) |
| **GitHub Stars** | ~114,000+（全球 Top 100 开源项目） |
| **与 SightLine 的关系** | **低** -- 通用 LLM 应用构建器。可视化工作流方法对 SightLine 的实时传感器融合需求太高级别。无流式传感器数据、自适应响应密度或可访问性特定功能的原生支持 |

### 4.2 Model Context Protocol (MCP)

| 属性 | 详情 |
|------|------|
| **功能** | Anthropic 发起的开放协议，标准化 LLM 连接外部数据源和工具的方式。提供上下文注入的通用接口 |
| **Context/Memory 处理** | 标准化 LLM 应用和外部上下文源（数据库、API、传感器流）之间的连接。通过服务器-客户端架构实现实时上下文注入 |
| **与 SightLine 的关系** | **中等** -- MCP 可以标准化 SightLine 的 Sub-Agent 如何向 Orchestrator 暴露上下文。但 SightLine 建立在 Gemini 原生 function calling 上，服务类似目的。值得在生态系统成熟时关注 |

---

## 5. Open-Source Assistive Technology Projects

### 5.1 Raspberry Pi Offline Assistive System (PMC 2025)

| 属性 | 详情 |
|------|------|
| **功能** | 运行在 Raspberry Pi 5 上的完全自主离线辅助系统。结合 YOLOv8 物体检测、Tesseract OCR 和语音引导的人脸识别注册 |
| **与 SightLine 的关系** | **低** -- SightLine 是云优先（Gemini Live API）。离线方法是正交的。但人脸识别管道（InsightFace ONNX + 本地 embedding）直接相关且已是 SightLine 架构的一部分 |

### 5.2 Visionauta (2026)

| 属性 | 详情 |
|------|------|
| **功能** | 由一位前谷歌盲人工程师开发的免费 Android 应用。提供文本阅读、纸币识别、电子放大镜、语音命令物体查找和 AI 场景描述 |
| **与 SightLine 的关系** | **中等** -- 有用的竞品参考。展示盲人用户期望的功能集。SightLine 通过自适应密度和上下文感知而非功能广度来差异化 |

---

## 6. Framework Selection Recommendations

| SightLine 组件 | 最佳框架 | 理由 |
|----------------|---------|------|
| **Ephemeral Context** | **ContextAgent**（架构参考） | 唯一建模第一人称传感器流主动决策的框架 |
| **Session Context** | **Letta/MemGPT**（core memory 概念） | "core memory as RAM"模式映射到始终在 LLM 上下文窗口中的会话上下文 |
| **Long-term Memory** | **Mem0**（主选）或 **Zep/Graphiti**（需时序查询时） | Mem0 用于自动偏好提取和用户范围记忆。Zep 用于"用户行为如何随时间变化"的查询 |
| **Orchestrator 路由** | **Google ADK**（已选择） | SightLine 已用 ADK。LangGraph 是有状态路由模式的好参考但会增加不必要的抽象 |
| **已知实体检索** | **LlamaIndex** 或 **Firestore 向量搜索**（已选择） | 如果检索复杂度超出 Firestore 原生能力则用 LlamaIndex |

### 核心洞察

没有单一框架覆盖 SightLine 的全部需求。**实时传感器融合 + 自适应响应密度**组合是独特的。最接近的类比是 ContextAgent，但它专注于是否主动协助，而非提供多少细节（LOD）。SightLine 的三层上下文层级加 LOD 驱动的响应塑造是现有框架没有直接实现的新贡献。

---

## Sources

- [ContextAgent GitHub](https://github.com/openaiotlab/ContextAgent)
- [LlamaIndex GitHub](https://github.com/run-llama/llama_index)
- [LangChain GitHub](https://github.com/langchain-ai/langchain)
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [Haystack GitHub](https://github.com/deepset-ai/haystack)
- [Letta/MemGPT GitHub](https://github.com/letta-ai/letta)
- [Mem0 GitHub](https://github.com/mem0ai/mem0)
- [Graphiti GitHub](https://github.com/getzep/graphiti)
- [CrewAI GitHub](https://github.com/crewAIInc/crewAI)
- [Dify GitHub](https://github.com/langgenius/dify)
