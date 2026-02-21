# SightLine Memory System: 方案调研与集成策略

> Date: 2026-02-21
> Status: Research complete — Integration decision made
> Related: `Context_Engine_Implementation_Guide.md` §4 (Long-term Context)

---

## 1. 调研背景

Context Engine 原设计方案（见 Implementation Guide §4）采用 Firestore + 自建 Mem0 式提取逻辑 + 向量搜索，需要 200-500 行胶水代码。经过对 Google 官方服务、开源框架和托管平台的系统调研，发现 Google 已提供开箱即用的方案。

---

## 2. 方案对比总览

| 方案 | 胶水代码 | Google 原生 | 自动记忆提取 | 语义检索 | 跨会话持久化 | 成本 |
|------|---------|------------|------------|---------|------------|------|
| **Vertex AI Memory Bank** | ~30 行 | ADK 原生 | 内置 | 内置 | 内置 | 公开预览免费至 2026-02-11；之后按 vCPU/GiB 计费 |
| Vertex AI RAG Engine | ~20 行 | 原生 | 无（需自建） | 内置 | 通过 MemoryCorpus | RAG Engine 免费；Spanner 后端按量计费 |
| Mem0 (开源/托管) | ~50 行 | 有 ADK 集成文档 | 内置 | 内置 | 内置 | 托管版 Hobby 免费 (10K memories)；Pro $249/mo |
| Firestore 自建 RAG | 200-500 行 | 原生 | 需自建 | 需自建 | 需自建 | Firestore 标准计费 |
| Zep Cloud | ~80 行 | 无原生集成 | 内置 | 内置 | 内置 | 信用额度制；OSS 版已废弃 |
| LangChain + Firestore | ~100 行 | Firestore 原生 | 无（仅存原始消息） | 无 | 有 | Firestore 标准计费 |

---

## 3. 推荐方案：Vertex AI Memory Bank（首选）

### 3.1 为什么选它

- **ADK 原生集成**：`VertexAiMemoryBankService` 直接插入 ADK Runner，零额外依赖
- **自动记忆提取**：Gemini 驱动，从对话中自动提取事实、偏好、关系，不需要自己写 extraction prompt
- **记忆演化**：新事实与旧记忆自动合并（非简单追加），支持记忆修订历史追踪
- **语义检索**：内置，通过 `PreloadMemoryTool` 每轮自动加载相关记忆
- **身份隔离**：按 agent_name + user_id 作用域隔离
- **TTL 支持**：可配置记忆过期时间
- **底层存储**：使用 Firestore，与现有技术栈一致

### 3.2 集成代码

```python
import os
import vertexai
from google import adk
from google.adk.memory import VertexAiMemoryBankService
from google.adk.sessions import VertexAiSessionService
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
os.environ["GOOGLE_CLOUD_PROJECT"] = "PROJECT_ID"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

# 1. 创建 Agent Engine 实例（一次性操作）
client = vertexai.Client(project="PROJECT_ID", location="us-central1")
agent_engine = client.agent_engines.create()
agent_engine_id = agent_engine.api_resource.name.split("/")[-1]

# 2. 记忆自动提取回调（每轮对话结束后执行）
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_events_to_memory(
        events=callback_context.session.events[-5:-1]
    )
    return None

# 3. 定义 Agent（挂载记忆工具）
agent = adk.Agent(
    model="gemini-2.5-flash",
    name="sightline_assistant",
    instruction="""你是 SightLine，为视障用户提供环境语义翻译的 AI 助手。
    使用过去对话中的记忆来个性化响应。
    记住用户偏好、认识的人、常去的地点和行为模式。""",
    tools=[PreloadMemoryTool()],
    after_agent_callback=generate_memories_callback
)

# 4. 初始化服务
memory_service = VertexAiMemoryBankService(
    project="PROJECT_ID", location="us-central1",
    agent_engine_id=agent_engine_id
)
session_service = VertexAiSessionService(
    project="PROJECT_ID", location="us-central1",
    agent_engine_id=agent_engine_id
)
runner = adk.Runner(
    agent=agent, app_name="sightline",
    session_service=session_service,
    memory_service=memory_service
)

# 5. 使用
session = await session_service.create_session(
    app_name="sightline", user_id="user_123"
)
async for event in runner.run_async(
    user_id="user_123", session_id=session.id,
    new_message=types.Content(
        role='user',
        parts=[types.Part(text="我喜欢先听左边再听右边的描述")]
    )
):
    if event.is_final_response():
        print(event.content.parts[0].text)
```

### 3.3 ADK 三层上下文原生支持

| ADK 概念 | 对应 SightLine 上下文层 | 说明 |
|---------|---------------------|------|
| **Session** (对话历史) | Ephemeral + Session Context | 当前会话内的所有事件；支持持久化到 `VertexAiSessionService` |
| **State** (键值状态) | Session Context 结构化字段 | `state["current_lod"]`, `state["space_type"]`, `state["trip_purpose"]` 等 |
| **Memory** (长期记忆) | Long-term Context | Memory Bank 自动提取和检索 |

### 3.4 CLI 测试

```bash
adk web path/to/agents_dir \
  --session_service_uri="agentengine://AGENT_ENGINE_ID" \
  --memory_service_uri="agentengine://AGENT_ENGINE_ID"
```

---

## 4. 补充方案：RAG Engine MemoryCorpus（可选增强）

与 Memory Bank 互补，用于 Live API 场景。

### 4.1 它做什么

- Live API 对话自动索引到 MemoryCorpus
- 后续 Session 可语义检索历史对话片段
- Memory Bank 提取的是事实；MemoryCorpus 保留的是原始对话上下文

### 4.2 集成方式

```python
from vertexai import rag

# 创建 Memory Corpus
embedding_config = rag.RagEmbeddingModelConfig(
    vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
        publisher_model="publishers/google/models/text-embedding-005"
    )
)
memory_corpus = rag.create_corpus(
    display_name="sightline_conversation_memory",
    backend_config=rag.RagVectorDbConfig(
        rag_embedding_model_config=embedding_config
    ),
)

# Live API WebSocket 配置中启用
live_api_tools = {
    "retrieval": {
        "vertex_rag_store": {
            "rag_resources": {
                "rag_corpus": memory_corpus.name
            }
        }
    }
}
# 设置 store_context=true → 对话自动写入 MemoryCorpus
```

### 4.3 是否推荐

Hackathon 阶段**可选**。Memory Bank 已覆盖核心需求。如果 Demo 需要展示"AI 能回忆上次对话的具体细节"（而非提炼后的事实），再加这一层。

---

## 5. 备选方案详情

### 5.1 Mem0

如果 Memory Bank 遇到限制（提取逻辑不够灵活、需要 Graph Memory 等），Mem0 是最强备选。

**优势**：
- 41K+ GitHub stars，社区活跃
- 官方 ADK 集成文档：https://docs.mem0.ai/integrations/google-ai-adk
- 支持 Gemini 作为 LLM + Embedding 提供者
- 支持 Vertex AI Vector Search 作为向量存储后端
- Google GKE AI Labs 有完整部署教程（Terraform + CloudSQL）
- Graph Memory 支持关系网络建模（适合 SightLine 的社交关系拓扑）

**集成代码**：

```python
from mem0 import Memory

config = {
    "llm": {
        "provider": "google",
        "config": {"model": "gemini-2.0-flash-001", "temperature": 0.1}
    },
    "embedder": {
        "provider": "google",
        "config": {"model": "models/text-embedding-004"}
    },
    "vector_store": {
        "provider": "vertex_ai_vector_search",
        "config": {
            "project_id": "PROJECT_ID",
            "region": "us-central1",
            "index_id": "INDEX_ID",
            "endpoint_id": "ENDPOINT_ID",
            "deployment_index_id": "DEPLOYMENT_INDEX_ID"
        }
    }
}

m = Memory.from_config(config)

# 存储记忆
m.add("用户称腾讯大厦B座为'公司'", user_id="user_123", metadata={"category": "location"})

# 检索记忆
results = m.search("用户的公司在哪里", user_id="user_123")
```

**ADK 集成**（作为 Function Tool）：

```python
from google.adk.agents import Agent

def search_memory(query: str, user_id: str) -> dict:
    """检索用户的历史记忆和偏好"""
    return mem0_client.search(query, user_id=user_id)

def save_memory(data: str, user_id: str) -> dict:
    """保存用户的重要信息"""
    return mem0_client.add(data, user_id=user_id)

agent = Agent(
    name="sightline",
    model="gemini-2.5-flash",
    tools=[search_memory, save_memory]
)
```

**定价**：
| 层级 | 价格 | 记忆条数 | API 调用/月 |
|------|------|---------|-----------|
| Hobby | 免费 | 10,000 | 1,000 |
| Starter | $19/mo | 50,000 | 5,000 |
| Pro | $249/mo | 无限 | 50,000 |

### 5.2 Vertex AI RAG Engine

**适用场景**：如果 SightLine 需要从大量文档（用户手册、地图数据、无障碍指南）中检索信息。

**核心能力**：
- 全托管 RAG 管线：数据摄入 → 分块 → Embedding → 索引 → 检索 → 生成
- 支持 GCS、Google Drive、本地文件
- RAG Engine 本身免费，计费来自 Spanner 后端和 Embedding 调用
- MemoryCorpus 类型专为 Live API 对话记忆设计

```python
from vertexai import rag
from vertexai.generative_models import GenerativeModel, Tool

# 创建 Corpus
rag_corpus = rag.create_corpus(
    display_name="sightline_knowledge",
    backend_config=rag.RagVectorDbConfig(
        rag_embedding_model_config=rag.RagEmbeddingModelConfig(
            vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                publisher_model="publishers/google/models/text-embedding-005"
            )
        )
    ),
)

# 导入文件
rag.import_files(
    rag_corpus.name,
    paths=["gs://my_bucket/accessibility_guides/"],
    transformation_config=rag.TransformationConfig(
        chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100),
    ),
)

# 作为 Tool 挂载到 Gemini
rag_tool = Tool.from_retrieval(
    retrieval=rag.Retrieval(
        source=rag.VertexRagStore(
            rag_resources=[rag.RagResource(rag_corpus=rag_corpus.name)],
            rag_retrieval_config=rag.RagRetrievalConfig(top_k=3),
        ),
    )
)
model = GenerativeModel("gemini-2.5-flash", tools=[rag_tool])
```

### 5.3 Firestore 向量搜索（已有能力）

**状态**：GA（2024 年 9 月起）

**技术规格**：
- 最大维度：2048
- 距离度量：EUCLIDEAN, COSINE, DOT_PRODUCT
- 支持预过滤（`.where()` + `find_nearest()`）
- SDK：Python, Node.js, Go, Java

**当前定位**：在推荐架构中，Firestore 向量搜索用于**结构化数据的精确检索**（如 Face ID 向量匹配），而非通用语义记忆。Memory Bank 负责后者。

```python
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

# 人脸向量匹配示例
face_query = db.collection("face_embeddings") \
    .where("user_id", "==", uid) \
    .find_nearest(
        vector_field="embedding",
        query_vector=Vector(detected_face_vector),
        distance_measure=DistanceMeasure.COSINE,
        limit=1,
        distance_threshold=0.6
    )
```

---

## 6. OpenClaw Memory System 参考

调研中对比了 OpenClaw (openclaw.ai) 的记忆架构，以下设计模式值得参考：

### 6.1 心智模型文件结构

| 文件 | 用途 | SightLine 对应 |
|------|------|---------------|
| `SOUL.md` | AI 的自我认知（人格定义） | System Prompt 中的角色定义 |
| `IDENTITY.md` | AI 对用户的认知模型 | Memory Bank 自动提取的用户画像 |
| `USER.md` | 用户显式填写的档案 | Firestore UserProfile |
| `MEMORY.md` | 策展式长期记忆 | Memory Bank 提炼的事实 |
| `memory/YYYY-MM-DD.md` | 每日追加日志 | Session 摘要（可选实现） |
| `HEARTBEAT.md` | 系统状态心跳 | ADK Session State |

### 6.2 可借鉴的技术细节

- **时间衰减**：`decayedScore = score × e^(-λ × ageInDays)`，half-life 30 天。Memory Bank 内部可能已实现类似机制；如果不够，可在检索结果上叠加衰减
- **混合检索**：BM25 关键词 + Vector 语义。Vertex AI RAG Engine 支持混合检索模式
- **MMR 重排**：Maximal Marginal Relevance (lambda=0.7) 平衡相关性与多样性。减少检索结果中的冗余记忆
- **Context Compaction 前自动 Flush**：在上下文压缩前触发记忆写入。SightLine 可在 Session 结束时用 `generate_memories_callback` 实现相同效果

---

## 7. 推荐实施路径

### Phase 1: Hackathon MVP

```
Memory Bank (自动提取 + 语义检索)
  + Firestore (UserProfile 显式偏好 + Face ID 向量)
  + ADK Session State (LOD、空间类型等实时状态)
```

集成工作量：~30 行代码 + Firestore schema 设计（已有）

### Phase 2: 增强（赛后）

- 加入 RAG Engine MemoryCorpus 保留完整对话上下文
- 评估 Mem0 Graph Memory 用于社交关系拓扑建模
- 实现 OpenClaw 式时间衰减（如 Memory Bank 原生不支持）
- Session 结束摘要持久化（类似 `memory/YYYY-MM-DD.md`）

---

## 8. 关键参考链接

### Google 官方文档

- [Vertex AI Memory Bank Overview](https://docs.cloud.google.com/agent-builder/agent-engine/memory-bank/overview)
- [Memory Bank ADK Quickstart](https://docs.cloud.google.com/agent-builder/agent-engine/memory-bank/quickstart-adk)
- [Memory Bank Public Preview Blog](https://cloud.google.com/blog/products/ai-machine-learning/vertex-ai-memory-bank-in-public-preview)
- [ADK Sessions / State / Memory](https://google.github.io/adk-docs/sessions/memory/)
- [Building Stateful Agents Codelab](https://codelabs.developers.google.com/codelabs/agent-memory/instructions)
- [Vertex AI RAG Engine Overview](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/rag-overview)
- [RAG Engine Quickstart](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/rag-quickstart)
- [Use RAG in Multimodal Live API](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/use-rag-in-multimodal-live)
- [RAG Engine Billing](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/rag-engine-billing)
- [Firestore Vector Search](https://firebase.google.com/docs/firestore/vector-search)

### 开源框架

- [Mem0 GitHub](https://github.com/mem0ai/mem0) — 41K+ stars
- [Mem0 Google ADK Integration](https://docs.mem0.ai/integrations/google-ai-adk)
- [Mem0 Vertex AI Vector Search Backend](https://docs.mem0.ai/components/vectordbs/dbs/vertex_ai)
- [Mem0 Gemini LLM Config](https://docs.mem0.ai/components/llms/models/gemini)
- [GKE AI Labs: ADK + Mem0 Deployment](https://gke-ai-labs.dev/docs/agentic/adk-memory/)

### 第三方参考

- [OpenClaw Memory System](https://docs.openclaw.ai/concepts/memory)
- [Gemini + Mem0 Integration Blog (Phil Schmid)](https://www.philschmid.de/gemini-with-memory)
- [GCP RAG Spectrum Comparison](https://medium.com/google-cloud/the-gcp-rag-spectrum-vertex-ai-search-rag-engine-and-vector-search-which-one-should-you-use-f56d50720d5a)

---

## 9. 决策记录

| 决策项 | 选择 | 理由 |
|-------|------|------|
| 长期记忆主方案 | Vertex AI Memory Bank | ADK 原生、零胶水、自动提取、Google 第一方 |
| 结构化数据存储 | Firestore (保持现有) | UserProfile、Face ID 向量需要精确查询 |
| 会话状态管理 | ADK Session State | 原生 key-value，无需额外服务 |
| 备选记忆方案 | Mem0 | 如果 Memory Bank 提取逻辑不够灵活，可切换 |
| RAG MemoryCorpus | Phase 2 可选 | MVP 阶段 Memory Bank 已覆盖核心需求 |
| 自建 RAG 管线 | 放弃 | 工程量大，已有现成替代 |
