# SightLine 环境配置操作日志

> **日期**: 2026-02-22
> **操作员**: Claude Code (AI)
> **GCP 账号**: weiliudev0607@gmail.com
> **GCP 项目**: sightline-hackathon

---

## 阶段 0: 安全检查

- [x] `.gitignore` 确认排除: `.env`, `.env.*`, `gen-lang-client-*.json`, `service-account*.json`
- [x] `.env.example` 可提交（`!.env.example` 例外规则存在）

---

## 阶段 1: 创建 .env 文件

- [x] 创建 `SightLine/.env`，写入所有凭证
- [x] 用户后续更新了 `VERTEX_API_KEY`（不再需要 Service Account JSON）
- [x] 文件已被 `.gitignore` 排除

---

## 阶段 2: Conda 虚拟环境

- [x] `conda create -n sightline python=3.12 -y` → Python 3.12.12
- [x] 路径: `/opt/anaconda3/envs/sightline/`

---

## 阶段 3: Python 依赖安装

- [x] `google-adk==1.25.1` → 成功（拉入 80+ 依赖）
- [x] `google-cloud-firestore==2.23.0` → 成功
- [x] `googlemaps==4.10.0` → 成功
- [x] `insightface==0.7.3` → Cython 编译通过 (Apple Silicon arm64)
- [x] `onnxruntime==1.24.2` → 成功
- [x] `opencv-python-headless==4.10.0.84` → 降级修复 numpy 冲突
- [x] `numpy==1.26.4` → 锁定 < 2.0
- [x] **验证: 12/12 包导入成功**

### 问题 1: numpy 版本冲突
- opencv-python-headless 4.13+ 要求 numpy >= 2.0
- insightface 0.7.3 不兼容 numpy 2.x
- 解决: 降级 OpenCV 到 4.10.0.84

---

## 阶段 4: InsightFace buffalo_l 模型

- [x] 下载: SourceForge 镜像 (`buffalo_l.zip`, 275 MB)
- [x] 解压: zip 内无子目录，手动创建 `~/.insightface/models/buffalo_l/` 并移入
- [x] 验证: `FaceAnalysis(allowed_modules=["detection","recognition"])` 加载成功
- [x] 推理测试: 空白图检测 0 人脸（符合预期）

### 文件清单
```
~/.insightface/models/buffalo_l/
├── det_10g.onnx      (16 MB)  — 人脸检测
├── w600k_r50.onnx    (166 MB) — 人脸识别嵌入 (512-D)
├── 1k3d68.onnx       (137 MB) — 3D 关键点（可选）
├── 2d106det.onnx     (4.8 MB) — 2D 关键点（可选）
└── genderage.onnx    (1.3 MB) — 性别/年龄（可选）
```

### 问题 2: zip 目录结构
- zip 内文件直接在根目录，无 buffalo_l/ 子目录
- 解决: 手动 `mkdir buffalo_l && mv *.onnx buffalo_l/`

---

## 阶段 5: gcloud CLI + GCP 基础设施

### 5.1 gcloud 安装与认证
- [x] `brew install --cask google-cloud-sdk` → v557.0.0
- [x] `gcloud auth login` → weiliudev0607@gmail.com
- [x] `gcloud config set project sightline-hackathon` → 成功

### 5.2 启用 GCP API (11 个)
- [x] `gcloud services enable` → 全部成功
```
aiplatform.googleapis.com
firestore.googleapis.com
run.googleapis.com
secretmanager.googleapis.com
maps-backend.googleapis.com
places-backend.googleapis.com
geocoding-backend.googleapis.com
routes.googleapis.com
cloudbuild.googleapis.com
artifactregistry.googleapis.com
generativelanguage.googleapis.com
```

### 5.3 创建 Firestore 数据库
- [x] `gcloud firestore databases create --location=us-central1 --type=firestore-native`
- [x] 结果: 成功
  - 模式: Firestore Native
  - 区域: us-central1
  - 免费层: true
  - UID: 70d63dbd-cff7-447f-b845-c6a85a5ff18f

### 5.4 创建 Service Account + IAM 角色
- [x] `gcloud iam service-accounts create sightline-backend` → 成功
- [x] Email: `sightline-backend@sightline-hackathon.iam.gserviceaccount.com`
- [x] 绑定角色:
  - [x] `roles/datastore.user` (Firestore)
  - [x] `roles/aiplatform.user` (Vertex AI)
  - [x] `roles/secretmanager.secretAccessor` (Secret Manager)
  - [x] `roles/run.invoker` (Cloud Run)

### 问题 3: IAM 绑定变量展开失败
- 使用 `$SA` shell 变量在某些情况下展开为空
- 解决: 直接内联完整 email 地址

### 5.5 Secret Manager
- [x] `gemini-api-key` → version 1 创建成功
- [x] `google-maps-api-key` → version 1 创建成功

### 5.6 Firestore 向量索引
- [x] `face_library` 集合: embedding 512-D flat 索引 → **READY**
- [x] `memories` 集合: embedding 2048-D flat 索引 → **READY**

### 5.7 ADC 本地凭证
- [x] `gcloud auth application-default login` → 成功
- [x] 凭证路径: `/Users/sunfl/.config/gcloud/application_default_credentials.json`
- [x] Quota project: `sightline-hackathon`

---

## 阶段性成果汇总

### 全部完成

| 项目 | 状态 |
|------|------|
| GCP 项目 `sightline-hackathon` | 已创建 + Billing |
| .env 凭证文件 | 已配置（Gemini / Maps / Vertex） |
| Conda `sightline` (Python 3.12) | 已创建 |
| Python 依赖 12/12 | 全部验证通过 |
| InsightFace buffalo_l | 已下载 + 验证通过 |
| gcloud CLI v557.0.0 | 已安装 + 已登录 + ADC 配置完成 |
| 11 个 GCP API | 全部启用 |
| Firestore 数据库 | 已创建 (Native, us-central1) |
| Service Account | 已创建 + 4 个 IAM 角色 |
| Secret Manager | 2 个 secret 已存储 |
| 向量索引 (512-D + 2048-D) | 全部 READY |
| ADC 本地凭证 | 已配置 |
| **端到端验证** | **Python → Firestore 连接 OK** |

### 后续按需安装（开发阶段不阻塞）

| 项目 | 何时需要 | 命令 |
|------|---------|------|
| Firebase MCP | AI 辅助操作 Firestore 时 | `claude mcp add firebase -- npx -y firebase-tools@latest experimental:mcp` |
| Docker | 部署到 Cloud Run 时 | `brew install --cask docker` |
| Terraform | IaC 加分项 | `brew tap hashicorp/tap && brew install hashicorp/tap/terraform` |

---

## 端到端验证结果 (最终)

```
[1] Python: 3.12.12
[2] 核心包: google-adk=1.25.1, genai=1.64.0, firestore=OK, insightface=0.7.3, onnxruntime=1.24.2, numpy=1.26.4
[3] Firestore 连接: OK (project=sightline-hackathon)
[4] InsightFace buffalo_l: 2 models loaded (detection + recognition)

=== ALL CHECKS PASSED ===
```

---

## 最终包版本清单

```
Python           3.12.12
google-adk       1.25.1
google-genai     1.64.0
google-cloud-aiplatform  1.138.0
google-cloud-firestore   2.23.0
google-cloud-secret-manager  2.26.0
insightface      0.7.3
onnxruntime      1.24.2
opencv-headless  4.10.0
googlemaps       4.10.0
numpy            1.26.4
fastapi          0.129.2
uvicorn          0.41.0
pydantic         2.12.5
websockets       15.0.1
```
