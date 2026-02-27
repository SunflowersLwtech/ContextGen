# SightLine 基础设施报告：数据库设计、MCP 与 Vibe Coding 可行性

> **生成日期**: 2026-02-22
> **基于**: Consolidated Development Reference + 全部 35 份文档交叉验证
> **定位**: Infra 准备阶段的执行指南，明确哪些任务可由 AI 通过 MCP/CLI 直接完成

---

## 1. 数据库设计

### 1.1 设计原则

SightLine 使用 **Firestore (Native mode)** 作为唯一数据库，理由：

| 因素 | 说明 |
|------|------|
| 自建 MemoryBankService 底层 | `memory/memory_bank.py` 直接使用 Firestore，技术栈统一 |
| ADK 原生支持 | `VertexAiSessionService` 直接用 Firestore 持久化 |
| 原生向量搜索 | 人脸 512-D + 记忆 2048-D 向量检索，无需额外向量数据库 |
| Hackathon 评分 | Google Cloud 服务数越多，Technical Implementation 得分越高 |
| 免费额度 | 50K 读/20K 写/天，Hackathon 期间零成本 |

数据分为**手动管理**（我们写代码操作）和**托管自动管理**（Google 服务内部处理）两类。

### 1.2 手动管理的集合

#### Collection: `users/{user_id}`

用户档案，由用户（或其视力正常的亲属）主动填写。

| 字段 | 类型 | 枚举/范围 | 说明 |
|------|------|----------|------|
| `vision_status` | string | `totally_blind` \| `low_vision` | 视力状态 |
| `blindness_onset` | string | `congenital` \| `acquired` | 盲的发生时间（分离设计，见矛盾裁定 #8） |
| `onset_age` | number \| null | 0-100 | 后天盲的发生年龄，先天盲为 null |
| `has_guide_dog` | boolean | — | 有导盲犬 → 不预警地面障碍 |
| `has_white_cane` | boolean | — | 有白杖 → 不预警碰撞 |
| `tts_speed` | number | 1.0 ~ 3.0 | TTS 语速倍率（BLV 偏好 2.0-3.0x） |
| `verbosity_preference` | string | `minimal` \| `standard` \| `detailed` | 描述详细度偏好 |
| `language` | string | BCP-47 | `en-US` \| `zh-CN` 等 |
| `description_priority` | string | `spatial` \| `object` \| `text` | 先天盲优先空间，后天盲优先物体 |
| `color_description` | boolean | — | false if congenital blind |
| `om_level` | string | `beginner` \| `intermediate` \| `advanced` | O&M 定向行走训练水平 |
| `travel_frequency` | string | `daily` \| `weekly` \| `rarely` | 出行频率 |
| `created_at` | timestamp | — | 创建时间 |
| `updated_at` | timestamp | — | 最后更新 |

**设计依据**：
- `vision_status` + `blindness_onset` 分离设计：`totally_blind + congenital` 不描述颜色，`totally_blind + acquired` 可以用颜色（Consolidated Doc 矛盾裁定 #8）
- `om_level` + `travel_frequency`：Beyond the Cane (ACM 2022) 证明这两个是信息需求量的最强预测因子
- `has_guide_dog`：有导盲犬的用户不需要地面障碍预警

#### Subcollection: `users/{user_id}/face_library/{face_id}`

人脸库，由视力正常的亲属操作注册。

| 字段 | 类型 | 说明 |
|------|------|------|
| `person_name` | string | 人名，如 "David" |
| `relationship` | string | 关系，如 "boss" \| "wife" \| "friend" \| "colleague" |
| `embedding` | Vector(512) | InsightFace ArcFace 512-D，L2 归一化 |
| `photo_index` | number | 1~5（每人 3-5 张不同角度/光线） |
| `registered_by` | string | 注册者标识，如 "user_wife" |
| `created_at` | timestamp | 注册时间 |

**设计要点**：
- 每人存 3-5 条文档（不同角度），匹配时取 max similarity
- `< 100 人`场景：会话启动时加载全部 embedding 到内存，brute-force 余弦相似度 `< 1ms`
- 匹配阈值：`cosine_similarity > 0.4`（InsightFace 推荐）
- 隐私：不存储原始照片，仅存储数学特征向量

#### Subcollection: `users/{user_id}/sessions_meta/{session_id}` （可选）

会话元数据，用于历史追踪和分析。

| 字段 | 类型 | 说明 |
|------|------|------|
| `start_time` | timestamp | 会话开始 |
| `end_time` | timestamp \| null | 会话结束 |
| `trip_purpose` | string \| null | 出行目的 |
| `lod_distribution` | map | `{"lod1": 45, "lod2": 30, "lod3": 25}` 百分比 |
| `space_transitions` | array | `["outdoor→lobby", "lobby→elevator"]` |
| `total_interactions` | number | 总交互次数 |

#### Collection: `memories/{memory_id}` （仅 Fallback 方案需要）

> **注意**：此集合由自建 `MemoryBankService`（`memory/memory_bank.py`）管理，为**当前采用方案**。Vertex AI Memory Bank 已降级为备选，不迁移。

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_id` | string | 所属用户 |
| `category` | string | `preference` \| `location` \| `person` \| `behavior` \| `stress_trigger` \| `routine` |
| `content` | string | 记忆内容文本 |
| `source` | string | `conversation_extraction` \| `behavior_pattern` |
| `confidence` | number | 0.0~1.0（< 0.7 不存储） |
| `embedding` | Vector(2048) | gemini-embedding-001（native 3072d → truncated） |
| `created_at` | timestamp | 创建时间 |
| `last_accessed` | timestamp | 最后访问 |
| `access_count` | number | 访问次数 |
| `decay_score` | number | `0.95^days_since_last_access` |

### 1.3 托管服务自动管理的数据

这些数据由 Google 托管服务内部管理，开发者**无需**手动创建集合或写入逻辑。

| 服务 | 管理的数据 | 底层存储 | 集成代码量 |
|------|----------|---------|-----------|
| **自建 Firestore Memory Bank** | 长期记忆（提取的事实/偏好/关系） | Firestore `users/{user_id}/memories` 子集合 | ~340 行（开发者手动管理） |
| **VertexAiSessionService** | 对话历史 + ADK Session State | 内部 Firestore | ~5 行 |
| **ADK Session State** | `current_lod`, `space_type`, `trip_purpose` 等实时状态 | 内存 或 Session Service | 0 行（ADK 原生） |

### 1.4 Firestore 向量索引

必须手动创建，否则向量搜索无法工作：

```bash
# 人脸向量索引 (512-D, COSINE)
gcloud firestore indexes composite create \
  --collection-group=face_library \
  --query-scope=COLLECTION \
  --field-config field-path=embedding,vector-config='{"dimension":"512","flat":"{}"}'

# 记忆向量索引 (2048-D, COSINE) — 仅 fallback 方案需要
gcloud firestore indexes composite create \
  --collection-group=memories \
  --query-scope=COLLECTION \
  --field-config field-path=embedding,vector-config='{"dimension":"2048","flat":"{}"}'
```

### 1.5 Firestore 安全规则

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    function isAuthenticated() {
      return request.auth != null;
    }

    function isOwner(userId) {
      return isAuthenticated() && request.auth.uid == userId;
    }

    function validFaceWrite(userId) {
      return request.resource.data.person_name is string
        && request.resource.data.relationship is string
        && request.resource.data.photo_index is int
        && request.resource.data.registered_by is string
        && request.resource.data.registered_by == userId
        && (
          !('reference_photo_base64' in request.resource.data)
          || (
            request.resource.data.consent_confirmed == true
            && request.resource.data.reference_photo_base64 is string
            && request.resource.data.reference_photo_base64.size() <= 350000
          )
        );
    }

    // 用户档案：仅本人可读写
    match /users/{userId} {
      allow read, write: if isOwner(userId);

      // 人脸库：仅本人可读写，写入需数据校验
      match /face_library/{faceId} {
        allow read: if isOwner(userId);
        allow create, update: if isOwner(userId) && validFaceWrite(userId);
        allow delete: if isOwner(userId);
      }

      // 会话元数据：仅本人可读写
      match /sessions_meta/{sessionId} {
        allow read, write: if isOwner(userId);
      }

      // 用户级记忆：仅本人可读写
      match /memories/{memoryId} {
        allow read, write: if isOwner(userId);
      }
    }

    // 顶层记忆集合（fallback）：仅本人可读写
    match /memories/{memoryId} {
      allow read, write: if isAuthenticated()
        && request.auth.uid == resource.data.user_id;
      allow create: if isAuthenticated()
        && request.auth.uid == request.resource.data.user_id;
    }

    // 默认拒绝所有其他访问
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

### 1.6 数据流关系图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Firestore Database                           │
│                                                                     │
│  ┌──────────────────────┐   ┌───────────────────────┐               │
│  │ users/{uid}          │   │ memories/{mid}        │               │
│  │  - vision_status     │   │  - user_id            │  ← Fallback  │
│  │  - blindness_onset   │   │  - category           │    方案才用   │
│  │  - tts_speed         │   │  - embedding(2048)    │               │
│  │  - om_level ...      │   │  - confidence ...     │               │
│  │                      │   └───────────────────────┘               │
│  │  └─ face_library/    │                                           │
│  │      - person_name   │   ┌───────────────────────┐               │
│  │      - embedding(512)│   │ [自建] MemoryBankService│              │
│  │      - relationship  │   │  Firestore memories/  │  ← 已采用    │
│  │                      │   │  memory_bank.py       │               │
│  └──────────────────────┘   └───────────────────────┘               │
│                                                                     │
│                             ┌───────────────────────┐               │
│                             │ [Auto] ADK Sessions   │               │
│                             │  内部 Firestore 集合   │               │
│                             └───────────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘

数据消费关系:
  users/{uid}             → LOD Engine (UserProfile) + System Prompt (Persona)
  face_library/{fid}      → Face ID Sub-Agent (实时匹配)
  memories 子集合          → preload_memory() (会话开始时加载 top-K)
  ADK Session State       → Context Fusion (LOD 决策) + Narrative Snapshot
```

---

## 2. MCP 插件评估

### 2.1 需要安装的 MCP

#### Firebase MCP（官方，强烈推荐）

| 属性 | 值 |
|------|---|
| **来源** | Google 官方：https://firebase.google.com/docs/ai-assistance/mcp-server |
| **安装方式** | Claude Code 中运行 `/install-mcp firebase` 或手动配置 `.mcp.json` |
| **能力** | Firestore CRUD、查询文档、管理安全规则、Auth 用户管理 |
| **对 SightLine 的价值** | 直接创建/查询 users、face_library 集合；调试数据；验证安全规则 |

**配置示例** (`.mcp.json`)：
```json
{
  "mcpServers": {
    "firebase": {
      "command": "npx",
      "args": ["-y", "firebase-tools@latest", "experimental:mcp"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account.json"
      }
    }
  }
}
```

#### Firestore Remote MCP（Google 托管）

| 属性 | 值 |
|------|---|
| **来源** | Google Cloud 托管：https://docs.cloud.google.com/firestore/native/docs/use-firestore-mcp |
| **启用方式** | `gcloud beta services mcp enable` (2026-03-17 后自动启用) |
| **能力** | 远程操作 Firestore 文档，OAuth 2.0 认证 |
| **适用场景** | 生产环境远程数据库操作 |

#### firebase-mcp（社区）

| 属性 | 值 |
|------|---|
| **来源** | https://github.com/gannonh/firebase-mcp |
| **能力** | Firestore + Auth + Storage 完整操作 |
| **适用场景** | Firebase MCP 官方版不足时的备选 |

### 2.2 MCP 选型决策

```
推荐路径:
  Firebase MCP (官方)     ← 首选，覆盖 Firestore + Auth
    ↓ 如果不足
  firebase-mcp (社区)     ← 更完整的 Firebase 操作
```

---

## 3. 环境变量与配置

### 3.1 后端环境变量 (.env)

```bash
# === GCP 基础 ===
GOOGLE_CLOUD_PROJECT=sightline-hackathon       # GCP 项目 ID
GOOGLE_CLOUD_LOCATION=us-central1              # 区域
GOOGLE_GENAI_USE_VERTEXAI=TRUE                 # ADK 通过 Vertex AI 调用

# === Gemini API ===
GOOGLE_API_KEY=<from-secret-manager>           # Gemini API Key

# ⚠️ ADK 不会自动映射 Live API 模型名称（见 ADK Part 5: How to Handle Model Names）
# Gemini Developer API (VERTEXAI=FALSE): gemini-2.5-flash-native-audio-preview-12-2025
# Vertex AI            (VERTEXAI=TRUE):  gemini-live-2.5-flash-native-audio (GA, 至 2026-12-12)
# 下面的值必须与 GOOGLE_GENAI_USE_VERTEXAI 设置匹配！
GEMINI_LIVE_MODEL=gemini-live-2.5-flash-native-audio   # ← Vertex AI GA 稳定版

GEMINI_VISION_MODEL=gemini-3.1-pro-preview
GEMINI_FLASH_MODEL=gemini-3-flash-preview
GEMINI_EMBEDDING_MODEL=gemini-embedding-001

# === Memory Bank ===
AGENT_ENGINE_ID=<optional>                     # SessionService persistence only (does not affect Memory)

# === Google Maps ===
GOOGLE_MAPS_API_KEY=<from-secret-manager>      # Maps/Places/Geocoding

# === Cloud Run ===
MIN_INSTANCE_COUNT=1                           # 消除冷启动
TIMEOUT=3600                                   # WebSocket 长连接 (秒)
MEMORY=2Gi                                     # 容器内存
CPU=2                                          # vCPU 数

# === InsightFace ===
FACE_MATCH_THRESHOLD=0.4                       # 余弦相似度匹配阈值
MAX_FACES_IN_LIBRARY=100                       # 内存加载上限
```

### 3.2 iOS 前端配置（Local / Cloud 零切换）

`Config.swift` 使用 `#if DEBUG` 条件编译，Debug 连本地、Release 连 Cloud Run，无需改代码：

```swift
// Config.swift
#if DEBUG
static let serverBaseURL = "ws://Lius-MacBook-Air.local:8100"   // 本地 mDNS
#else
static let serverBaseURL = "wss://sightline-backend-kp47ssyf4q-uc.a.run.app"
#endif
```

| 构建配置 | 连接目标 | ATS | Info.plist |
|----------|---------|-----|-----------|
| Debug | `ws://Lius-MacBook-Air.local:8100` | `NSAllowsLocalNetworking = true` | `Info-Debug.plist` |
| Release | `wss://...run.app` | 默认严格 | 无额外 plist |

**本地开发流程**：
```bash
conda activate sightline && cd SightLine && python server.py   # 监听 0.0.0.0:8100
# Xcode Debug build → 真机自动连 ws://Mac.local:8100
# 改 server.py → 重启进程即可，无需重新 build iOS
```

> `server.py` 默认端口改为 `8100`（避免与常用 8080 冲突）。Cloud Run 通过 `PORT` 环境变量注入 `8080`，不受影响。

### 3.3 Secret Manager 存储项

| Secret 名称 | 内容 | 引用方式 |
|------------|------|---------|
| `gemini-api-key` | Gemini API Key | Cloud Run 环境变量注入 |
| `google-maps-api-key` | Maps API Key | Cloud Run 环境变量注入 |

```bash
# 创建
echo -n "YOUR_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
echo -n "YOUR_MAPS_KEY" | gcloud secrets create google-maps-api-key --data-file=-

# Cloud Run 绑定
gcloud run deploy sightline \
  --set-secrets="GOOGLE_API_KEY=gemini-api-key:latest,GOOGLE_MAPS_API_KEY=google-maps-api-key:latest"
```

---

## 4. Google Credentials 清单

### 4.1 需要的凭证

| # | 凭证 | 用途 | 获取方式 | 人工/AI |
|---|------|------|---------|--------|
| 1 | GCP 项目 ID | 所有 GCP 服务的基础 | Console 创建项目 | **人工** |
| 2 | Gemini API Key | Gemini Live/REST API 调用 | AI Studio 生成 | **人工** |
| 3 | Service Account JSON | Cloud Run → Firestore/Memory Bank/Maps | `gcloud iam` CLI | AI |
| 4 | Google Maps API Key | Places/Routes/Geocoding | Console 启用 + 生成 | **人工** |
| 5 | OAuth 2.0 Client ID | 前端用户认证（如需要） | Console → APIs & Services | **人工** |

### 4.2 需要启用的 GCP API

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  maps-backend.googleapis.com \
  places-backend.googleapis.com \
  geocoding-backend.googleapis.com \
  routes.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  generativelanguage.googleapis.com
```

### 4.3 Service Account 权限

```bash
# 创建 Service Account
gcloud iam service-accounts create sightline-backend \
  --display-name="SightLine Backend"

# 绑定角色
PROJECT_ID=sightline-hackathon
SA=sightline-backend@${PROJECT_ID}.iam.gserviceaccount.com

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/datastore.user"          # Firestore
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/aiplatform.user"         # Vertex AI
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor"  # Secrets
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" --role="roles/run.invoker"             # Cloud Run
```

---

## 5. 部署配置

### 5.1 Cloud Run 配置

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/sightline-backend', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/sightline-backend']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'run'
      - 'deploy'
      - 'sightline-backend'
      - '--image=gcr.io/$PROJECT_ID/sightline-backend'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--min-instances=1'
      - '--max-instances=10'
      - '--timeout=3600'
      - '--memory=2Gi'
      - '--cpu=2'
      - '--cpu-throttling=false'
      - '--startup-cpu-boost'
      - '--set-secrets=GOOGLE_API_KEY=gemini-api-key:latest,GOOGLE_MAPS_API_KEY=google-maps-api-key:latest'
    entrypoint: gcloud
```

### 5.2 Dockerfile

```dockerfile
FROM python:3.11-slim-bookworm

# InsightFace 依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## 6. Vibe Coding 可行性矩阵

### 6.1 总览

每项 Infra 任务标记是否可由 AI 通过 MCP 或 CLI 直接完成：

| 任务 | 执行方式 | AI 自动化 | 前置依赖 |
|------|---------|----------|---------|
| **Firestore 创建数据库** | `gcloud firestore databases create` | 100% | GCP 项目 |
| **Firestore 创建集合/文档** | Firebase MCP | 100% | 安装 MCP |
| **Firestore 创建向量索引** | `gcloud firestore indexes` | 100% | 数据库存在 |
| **Firestore 安全规则** | Firebase MCP 或 `firebase deploy` | 100% | — |
| **Cloud Run 部署** | `gcloud run deploy` 或 `adk deploy cloud_run` | 100% | Docker 镜像 |
| **Secret Manager 操作** | `gcloud secrets` | 100% | API Key 值 |
| **启用 GCP API** | `gcloud services enable` | 100% | GCP 项目 |
| **Service Account 创建** | `gcloud iam` | 100% | GCP 项目 |
| **Agent Engine 创建（可选 — 仅 Session 持久化）** | Python SDK `client.agent_engines.create()` | 100% | Vertex AI API |
| **Terraform IaC** | 写 `.tf` 文件 + `terraform apply` | 100% | — |
| **Python 后端代码** | Claude Code 直接写 | 100% | — |
| **React 前端代码** | Claude Code 直接写 | 100% | — |
| **Dockerfile / cloudbuild** | Claude Code 直接写 | 100% | — |
| GCP 项目创建 + Billing | Console 手动 | **0%** | 信用卡 |
| Gemini API Key 生成 | AI Studio 手动 | **0%** | GCP 项目 |
| Maps API Key 生成 | Console 手动 | **0%** | GCP 项目 |
| GDG 会员注册 | gdg.community.dev | **0%** | — |

### 6.2 推荐的 Infra 执行顺序

```
Phase A: 人工操作 (30 min)
  ├── A1. GCP Console 创建项目 + 启用 Billing
  ├── A2. AI Studio 生成 Gemini API Key
  ├── A3. Console 启用 Maps API + 生成 Key
  └── A4. 注册 GDG 会员

Phase B: AI 执行 — CLI (15 min)
  ├── B1. gcloud services enable (全部 API)
  ├── B2. gcloud firestore databases create
  ├── B3. gcloud iam service-accounts create + 绑定角色
  ├── B4. gcloud secrets create (存储 API Keys)
  └── B5. gcloud firestore indexes composite create (向量索引)

Phase C: AI 执行 — MCP + Vibe Coding (1-2 hr)
  ├── C1. 安装 Firebase MCP
  ├── C2. 通过 MCP 创建初始用户文档 (测试数据)
  ├── C3. 写 Dockerfile + cloudbuild.yaml
  ├── C4. 写 .env.example
  ├── C5. 初始化 ADK 项目结构 (agents/, tools/, lod/)
  ├── C6. (可选) 创建 Agent Engine (Session 持久化)
  └── C7. 首次部署 Cloud Run (验证 E2E)
```

### 6.3 Firebase MCP 安装步骤

安装后 AI 可直接操作 Firestore：

```bash
# 方式 1: Claude Code 全局安装
claude mcp add firebase -- npx -y firebase-tools@latest experimental:mcp

# 方式 2: 项目级 .mcp.json
# 在项目根目录创建 .mcp.json（见 §2.1 配置示例）
```

安装后可用的操作：
- `firestore_get_document` — 读取文档
- `firestore_list_documents` — 列出集合
- `firestore_set_document` — 写入/更新文档
- `firestore_delete_document` — 删除文档
- `firestore_query_collection` — 查询
- `firestore_get_rules` / `firestore_set_rules` — 安全规则管理

---

## 7. 成本估算

### 7.1 Hackathon 期间 (23 天)

| 服务 | 免费额度 | 预计用量 | 成本 |
|------|---------|---------|------|
| Gemini Live API | Free tier: 3 并发 | ~50 小时测试 | ~$22-25 |
| Gemini 3.1 Pro (Vision) | 付费 | ~100 次调用/天 | ~$10-15 |
| Gemini 3 Flash (OCR/Nav) | **预览期免费** | ~500 次/天 | $0 |
| gemini-embedding-001 | 免费额度内 | ~1000 次/天 | $0 |
| Firestore | 50K 读/20K 写/天 | 远低于上限 | $0 |
| Cloud Run | 200 万请求/月 | ~1 万请求 | ~$5 |
| Maps API | 10K 调用/月 | ~2000 调用 | $0 |
| Secret Manager | 6 版本免费 | 2-3 secrets | $0 |
| 自建 Firestore MemoryBankService | 含在 Firestore 额度内 | memories 集合读写 | $0 |
| **合计** | | | **~$37-45** |

---

## 8. 风险与注意事项

| 风险 | 影响 | 缓解 |
|------|------|------|
| Firebase MCP 权限不足 | 无法通过 AI 操作 Firestore | 降级为 `gcloud` CLI 直接操作 |
| ~~Vertex AI Memory Bank 配额限制~~ | ~~记忆存储受限~~ | ~~已采用自建 Firestore 方案，无配额限制~~ |
| Cloud Run WebSocket 超时 | 会话中断 | `timeout=3600` + Session Resumption |
| Service Account Key 泄露 | 安全风险 | 使用 Workload Identity Federation（生产级），Hackathon 用 Secret Manager |
| Firestore 向量索引创建时间 | 首次创建需要几分钟 | 提前创建，不在 Demo 前操作 |

---

*本文档为 SightLine Infra 准备阶段的执行指南。所有数据库设计和配置以本文档为准，与 Consolidated Development Reference 保持一致。*
