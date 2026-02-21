# SightLine 环境依赖完整指南

> **生成日期**: 2026-02-22
> **定位**: 开发前的环境准备参考，涵盖所有需要安装的工具、SDK、Python 包、预训练模型

---

## 1. 本地开发工具（macOS）

### 1.1 当前已有

| 工具 | 版本 | 用途 |
|------|------|------|
| Xcode | 26.2 | iOS/watchOS 前端开发（Swift） |
| Swift | 6.2.3 (arm64) | iOS Native App 编写 |
| Python | 3.13.9（系统默认） | 需降级到 3.12，见下方说明 |
| Conda | 25.11.1 (`/opt/anaconda3`) | 虚拟环境管理 |
| uv | 0.9.26 | 快速 Python 包管理（备选） |
| Node.js | 25.2.1 | Firebase MCP 运行 (`npx`) |
| npm / npx | 11.6.2 | 同上 |
| Homebrew | 5.0.14 | 安装其他工具 |

### 1.2 需要安装的工具

| 工具 | 用途 | 安装命令 |
|------|------|---------|
| **gcloud CLI** | GCP 项目管理、Cloud Run 部署、IAM、Secret Manager | `brew install --cask google-cloud-sdk` |
| **Firebase CLI** | Firestore 安全规则部署、Firebase MCP | `npm install -g firebase-tools` |
| **Docker Desktop** | 构建 Cloud Run 容器镜像 | `brew install --cask docker` |
| **Terraform** | Infrastructure as Code（加分项） | `brew tap hashicorp/tap && brew install hashicorp/tap/terraform` |

#### gcloud CLI 安装后初始化

```bash
# 安装后重启终端，然后：
gcloud init
gcloud auth login
gcloud config set project sightline-hackathon
gcloud auth application-default login   # 本地开发用的 ADC 凭证
```

#### Firebase CLI 说明

Firebase MCP 可以通过 `npx -y firebase-tools@latest experimental:mcp` 按需运行，不一定需要全局安装。但全局安装后可以用 `firebase deploy --only firestore:rules` 部署安全规则。

#### Docker 说明

安装 Docker Desktop 后需要从 Applications 启动一次以初始化 daemon。Cloud Run 部署也可以用 Cloud Build 远程构建（不依赖本地 Docker），但本地调试时需要。

---

## 2. Python 环境

### 2.1 为什么要用 Python 3.12（不用系统默认 3.13）

| 包 | Python 3.13 兼容性 | Python 3.12 兼容性 |
|-----|-------------------|-------------------|
| `google-adk` | 支持（3.10-3.14） | 支持 |
| `insightface` 0.7.3 | Cython 编译可能失败 | 稳定 |
| `onnxruntime` 1.24.x | 支持（3.10-3.13） | 支持 |
| `numpy < 2.0` | 部分兼容问题 | 完全兼容 |

**结论：使用 Python 3.12 创建虚拟环境。**

### 2.2 创建虚拟环境（Conda）

```bash
conda create -n sightline python=3.12 -y
conda activate sightline
```

### 2.3 备选：使用 uv

```bash
cd /Users/sunfl/Documents/study/ContextGen/SightLine
uv venv --python 3.12 .venv
source .venv/bin/activate
```

---

## 3. Python 包依赖（完整清单）

### 3.1 核心依赖关系图

```
google-adk==1.25.1  ← 唯一的"mega-dependency"，自动拉入大量 Google Cloud 包
├── google-genai >= 1.56.0           (Gemini Live API / REST API)
├── google-cloud-aiplatform >= 1.132.0 [agent-engines]
│   └── (Memory Bank, Session Service, Embedding)
├── google-cloud-secret-manager >= 2.22.0
├── google-cloud-storage >= 2.18.0
├── fastapi >= 0.124.1               (HTTP/WebSocket 框架)
├── uvicorn >= 0.34.0                (ASGI 服务器)
├── pydantic >= 2.0
├── websockets >= 15.0.1
├── httpx >= 0.27.0
├── requests >= 2.32.4
├── starlette >= 0.49.1
├── python-dotenv >= 1.0.0
├── graphviz                         (Agent 可视化)
└── ... (aiosqlite, authlib, click, mcp, opentelemetry-*, 等)

google-cloud-firestore==2.23.0  ← 需要额外安装（ADK 不包含）
insightface==0.7.3              ← 人脸识别
onnxruntime==1.24.2             ← ONNX 推理（CPU）
googlemaps==4.10.0              ← Maps/Places/Geocoding 统一客户端
opencv-python-headless           ← 图像处理（服务端无 GUI）
numpy >= 1.24, < 2.0            ← 必须锁定 < 2.0（insightface 不兼容 numpy 2.x）
cython >= 3.0.0                 ← insightface 编译依赖
```

### 3.2 requirements.txt

```
# ============================================================
# SightLine Backend Dependencies
# Python 3.12 | Last updated: 2026-02-22
# ============================================================

# === 核心 Agent 框架（自动拉入 fastapi, uvicorn, google-genai,
#     google-cloud-aiplatform, secret-manager, pydantic, websockets 等） ===
google-adk==1.25.1

# === Firestore（ADK 不包含，必须单独安装） ===
google-cloud-firestore==2.23.0

# === 人脸识别 ===
insightface==0.7.3
onnxruntime==1.24.2
opencv-python-headless>=4.9.0

# === Google Maps（Places / Routes / Geocoding 统一客户端） ===
googlemaps==4.10.0

# === 版本锁定（防止 insightface 与 numpy 2.x 不兼容） ===
numpy>=1.24.0,<2.0

# === 编译依赖（insightface Cython 扩展需要） ===
cython>=3.0.0
```

### 3.3 google-adk 已经包含的包（不要重复安装）

以下包由 `google-adk==1.25.1` 自动拉入，**无需写入 requirements.txt**：

| 包 | ADK 约束版本 | SightLine 用途 |
|----|-------------|---------------|
| `fastapi` | >= 0.124.1, < 1.0 | Cloud Run HTTP/WebSocket 后端 |
| `uvicorn` | >= 0.34.0, < 1.0 | ASGI 服务器 |
| `google-genai` | >= 1.56.0, < 2.0 | Gemini Live API (`client.aio.live.connect()`) |
| `google-cloud-aiplatform[agent-engines]` | >= 1.132.0, < 2.0 | Memory Bank + Session Service |
| `google-cloud-secret-manager` | >= 2.22.0, < 3.0 | Cloud Run 读取 API Key |
| `google-cloud-storage` | >= 2.18.0, < 4.0 | 文件存储（备用） |
| `pydantic` | >= 2.0, < 3.0 | 数据模型 |
| `websockets` | >= 15.0.1, < 16.0 | WebSocket 通信 |
| `httpx` | >= 0.27.0 | HTTP 客户端 |
| `requests` | >= 2.32.4, < 3.0 | HTTP 客户端（同步） |
| `starlette` | >= 0.49.1, < 1.0 | ASGI 框架 |
| `python-dotenv` | >= 1.0.0 | .env 文件加载 |
| `graphviz` | — | Agent 图可视化 |

### 3.4 已知兼容性问题

| 问题 | 严重度 | 解决方案 |
|------|--------|---------|
| insightface + NumPy 2.x 不兼容 | **高** | 锁定 `numpy>=1.24.0,<2.0` |
| insightface Cython 在 Apple Silicon 编译可能失败 | **中** | 确保 `xcode-select --install` + `brew install cmake libomp` |
| `google-genai` vs `google-generativeai` 混淆 | **中** | 只用 `google-genai`（新 SDK），不要安装 `google-generativeai`（旧 SDK，不支持 Live API） |
| `onnxruntime` vs `onnxruntime-gpu` 冲突 | **高** | 只装一个。Cloud Run 用 CPU 版 `onnxruntime` |

### 3.5 macOS 系统级依赖（Apple Silicon 编译 insightface 需要）

```bash
# Xcode Command Line Tools（通常已有）
xcode-select --install

# Homebrew 包
brew install cmake libomp
```

---

## 4. 预训练模型下载

### 4.1 InsightFace buffalo_l 模型包

| 属性 | 值 |
|------|---|
| 模型包名 | `buffalo_l` |
| 总大小 | ~326 MB (zip) / ~341 MB (解压) |
| 本地存储路径 | `~/.insightface/models/buffalo_l/` |
| 自动下载 | 首次调用 `FaceAnalysis()` 时自动下载 |
| 官方下载源 | `storage.insightface.ai`（**经常挂**） |

**模型文件清单：**

| 文件 | 大小 | 用途 | SightLine 是否必需 |
|------|------|------|-------------------|
| `det_10g.onnx` | 17 MB | 人脸检测（SCRFD-10GF） | **必需** |
| `w600k_r50.onnx` | 174 MB | 人脸识别嵌入（ArcFace ResNet50, 512-D） | **必需** |
| `1k3d68.onnx` | 137 MB | 3D 面部对齐（68 点） | 可选 |
| `2d106det.onnx` | 5 MB | 2D 面部关键点（106 点） | 可选 |
| `genderage.onnx` | 1.3 MB | 性别/年龄估计 | 可选 |

**可靠下载源（官方源不稳定时使用）：**

1. SourceForge 镜像：`https://sourceforge.net/projects/insightface.mirror/files/v0.7/buffalo_l.zip/download`
2. HuggingFace (official)：`https://huggingface.co/public-data/insightface/tree/main/models/buffalo_l`
3. HuggingFace (immich)：`https://huggingface.co/immich-app/buffalo_l`

**Docker 构建注意**：必须在 Dockerfile 中预下载模型，不能依赖运行时自动下载（326 MB 会导致容器启动极慢）。

```dockerfile
# Dockerfile 中预置模型
RUN mkdir -p /root/.insightface/models/buffalo_l
COPY models/buffalo_l/ /root/.insightface/models/buffalo_l/
```

**使用代码：**

```python
from insightface.app import FaceAnalysis
import os

model_root = os.environ.get('INSIGHTFACE_ROOT', '~/.insightface')
app = FaceAnalysis(name="buffalo_l", root=model_root,
                   providers=["CPUExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))

faces = app.get(image_bgr_array)  # numpy BGR array
for face in faces:
    embedding = face.embedding  # shape: (512,), L2 归一化后存 Firestore
```

### 4.2 Gemini 模型（无需本地下载）

所有 Gemini 模型通过 API 远程调用，无需本地下载：

| 模型 ID | 用途 | 调用方式 |
|---------|------|---------|
| `gemini-2.5-flash-native-audio-preview-12-2025` | Orchestrator（Live API 双向音频+视频） | `google-genai` SDK WebSocket |
| `gemini-3.1-pro-preview` | Vision Sub-Agent（深度场景分析） | `google-genai` SDK REST |
| `gemini-3-flash-preview` | OCR/Navigation/Memory Sub-Agent | `google-genai` SDK REST |
| `gemini-embedding-001` | 记忆/RAG 向量嵌入（2048-D） | `google-genai` SDK REST |

### 4.3 graphviz 系统包（ADK Agent 图可视化）

```bash
brew install graphviz
```

Python 包 `graphviz` 由 ADK 自动安装，但它依赖系统的 `dot` 命令。

---

## 5. 开源项目 / SDK 参考

### 5.1 Google ADK (Agent Development Kit)

| 属性 | 值 |
|------|---|
| GitHub | `https://github.com/google/adk-python` |
| 文档 | `https://google.github.io/adk-docs/` |
| 安装 | `pip install google-adk==1.25.1` |
| 关键功能 | LlmAgent, SequentialAgent, ParallelAgent, LoopAgent, `run_live()` bidi-streaming, LiveRequestQueue, VertexAiSessionService, VertexAiMemoryBankService |

**ADK bidi-demo 模板**（SightLine 架构的基础参考）：
- 位于 ADK 仓库的 `contributing/samples/` 目录
- 或参考 `SightLine_Best_Practices_Research.md` 中的模板代码

### 5.2 InsightFace

| 属性 | 值 |
|------|---|
| GitHub | `https://github.com/deepinsight/insightface` |
| PyPI | `https://pypi.org/project/insightface/` |
| 版本 | 0.7.3（2023-04 发布，截至 2026-02 仍为最新） |
| 许可证 | **非商业研究用途**（商业使用需联系 InsightFace 获取许可） |

### 5.3 Google Gen AI SDK

| 属性 | 值 |
|------|---|
| GitHub | `https://github.com/googleapis/python-genai` |
| PyPI | `https://pypi.org/project/google-genai/` |
| 导入方式 | `from google import genai` |
| 注意 | 这是**新** SDK（不是 `google-generativeai`），支持 Live API |

### 5.4 Firebase Tools

| 属性 | 值 |
|------|---|
| GitHub | `https://github.com/firebase/firebase-tools` |
| npm | `npm install -g firebase-tools` |
| MCP 模式 | `npx -y firebase-tools@latest experimental:mcp` |

---

## 6. Docker 镜像依赖（Cloud Run 部署用）

### 6.1 基础镜像

```
python:3.12-slim-bookworm
```

### 6.2 系统包（apt）

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    g++ \
    python3-dev \
    graphviz \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
```

| 包 | 用途 |
|----|------|
| `build-essential` / `cmake` / `g++` / `python3-dev` | insightface Cython 编译 |
| `graphviz` | ADK Agent 图可视化 |
| `libgl1` | OpenCV `libGL.so.1` 依赖 |
| `libglib2.0-0` | OpenCV GLib 依赖 |

> 提示：如果使用 `opencv-python-headless`，则不需要 `libgl1`。

### 6.3 预计镜像大小

| 层 | 大小 |
|----|------|
| python:3.12-slim 基础 | ~150 MB |
| 系统包 | ~200 MB |
| Python 依赖 | ~800 MB |
| buffalo_l 模型 | ~340 MB |
| 应用代码 | ~5 MB |
| **总计** | **~1.5 GB** |

---

## 7. 完整安装执行顺序

```
Phase 0: 本地工具安装 [人工，~15 min]
  ├── 0.1  brew install --cask google-cloud-sdk
  ├── 0.2  brew install --cask docker
  ├── 0.3  npm install -g firebase-tools
  ├── 0.4  brew tap hashicorp/tap && brew install hashicorp/tap/terraform
  ├── 0.5  brew install cmake libomp graphviz
  └── 0.6  gcloud init && gcloud auth login && gcloud config set project sightline-hackathon

Phase 1: Python 虚拟环境 [AI 或人工，~5 min]
  ├── 1.1  conda create -n sightline python=3.12 -y
  ├── 1.2  conda activate sightline
  └── 1.3  pip install -r requirements.txt

Phase 2: 模型下载 [AI 或人工，~5 min]
  └── 2.1  下载 buffalo_l.zip → 解压到 ~/.insightface/models/buffalo_l/

Phase 3: GCP 凭证（见 .env.checklist.md）[人工]
  ├── 3.1  Gemini API Key
  ├── 3.2  Google Maps API Key
  └── 3.3  填入 .env

Phase 4: GCP 基础设施 [AI 自动]
  ├── 4.1  启用 GCP API
  ├── 4.2  创建 Firestore
  ├── 4.3  创建 Service Account
  ├── 4.4  Secret Manager
  ├── 4.5  向量索引
  └── 4.6  安装 Firebase MCP
```

---

## 8. 快速验证清单

安装完成后，运行以下命令确认环境正常：

```bash
# 工具验证
gcloud --version                          # Google Cloud SDK
firebase --version                        # Firebase CLI
docker --version                          # Docker
terraform --version                       # Terraform

# Python 环境验证
conda activate sightline
python --version                          # 应显示 3.12.x

# 核心包验证
python -c "import google.adk; print(google.adk.__version__)"        # 1.25.1
python -c "from google import genai; print(genai.__version__)"       # >= 1.56.0
python -c "import google.cloud.firestore; print('Firestore OK')"
python -c "import insightface; print(insightface.__version__)"       # 0.7.3
python -c "import onnxruntime; print(onnxruntime.__version__)"       # 1.24.2
python -c "import googlemaps; print('Maps OK')"
python -c "import numpy; print(numpy.__version__)"                   # 应 < 2.0

# InsightFace 模型验证
python -c "
from insightface.app import FaceAnalysis
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))
print(f'Models loaded: {len(app.models)}')
"

# GCP 认证验证
gcloud auth application-default print-access-token   # 应输出 token
```

---

*本文档为 SightLine 开发环境准备的完整参考。所有版本号基于 2026-02-22 调研结果。*
