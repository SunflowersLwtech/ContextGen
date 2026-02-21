# SightLine 市场竞品全景图

> **调研日期**: 2026-02-21
> **目标**: 搜索市场上与 SightLine 相关的已有产品，包括开源项目、脚手架/轮子、闭源产品

---

## 一、闭源商业产品 (Closed-Source Products)

这些是市场上已经在运营的、面向视障用户的 AI 辅助产品。

### 1. Be My Eyes + Be My AI
- **公司**: Be My Eyes (丹麦)
- **形态**: iOS/Android App（免费）
- **核心能力**: 原先连接视障用户与志愿者进行实时视频通话；2023 年整合 GPT-4o 推出 **Be My AI**，用户拍照即可获得 AI 图像描述
- **与 SightLine 的关系**: 最接近的竞品之一。但 Be My AI 是**被动响应**模式 (用户拍照 → AI 描述)，没有实时视频流分析，没有 LOD 自适应，没有 Context Awareness
- **差异化**: ❌ 无 Adaptive LOD ❌ 无传感器融合 ❌ 无主动发声 ❌ 无人脸库
- **官网**: https://www.bemyeyes.com

### 2. Envision Glasses / Envision Ally
- **公司**: Envision (荷兰)
- **形态**: 智能眼镜 (基于 Google Glass EE2) + iOS/Android App
- **价格**: 眼镜 ~$2,099+；App 免费/订阅
- **核心能力**: OCR (60+ 语言)、场景描述 (Describe Scene)、人脸识别 (Teach a Face)、物体查找、颜色检测、同伴视频通话。2025 年推出 **Ally** AI 助手 (基于 GPT-5 的对话式 AI)
- **与 SightLine 的关系**: 功能上最完整的竞品。已经有人脸识别和场景描述。但信息输出是**静态密度**，不会根据用户行走/静止状态自动调节
- **差异化**: ❌ 无 Adaptive LOD ❌ 无基于心率/步频的上下文融合 ❌ 信息密度不自适应
- **官网**: https://www.letsenvision.com

### 3. Aira Explorer + Aira AI (Project Astra)
- **公司**: Aira (美国, Carlsbad CA)
- **形态**: iOS/Android App，连接**真人**视觉翻译员 (Visual Interpreter)
- **价格**: 部分免费 (Access Partner 地点)，订阅制
- **核心能力**: 24/7 真人远程视觉翻译；2025 年与 Google 合作推出 **Aira AI powered by Project Astra** — 实时对话式 AI 视觉翻译，有真人监督
- **与 SightLine 的关系**: Aira AI + Project Astra 是概念上最接近 SightLine 的产品 — 实时、对话式、视觉翻译。但目前处于 Trusted Tester 阶段
- **差异化**: ❌ 无 Adaptive LOD ❌ 无传感器融合 ❌ 依赖真人兜底 (成本高)
- **关键信息**: Aira 与 Google 的合作表明 Google 非常重视这个方向，对 SightLine 参加 Gemini Challenge 是利好信号
- **官网**: https://aira.io

### 4. Microsoft Seeing AI
- **公司**: Microsoft
- **形态**: iOS App（免费）
- **核心能力**: 短文本即时读取、文档扫描、产品条码识别、人物识别 (面部表情)、场景描述、颜色识别、光源检测、货币识别
- **与 SightLine 的关系**: 功能丰富但**完全被动** — 用户需要选择模式并对准摄像头
- **差异化**: ❌ 无 Adaptive LOD ❌ 无实时视频流 ❌ 无主动发声 ❌ 仅 iOS
- **官网**: https://www.microsoft.com/en-us/seeing-ai

### 5. Google Lookout
- **公司**: Google
- **形态**: Android App（免费）
- **核心能力**: 物体识别、文字阅读、食品标签识别、场景描述、货币识别
- **与 SightLine 的关系**: Google 自家的视障辅助 App，但功能相对基础，没有对话能力
- **差异化**: ❌ 无 LOD ❌ 无对话能力 ❌ 无人脸识别 ❌ 仅 Android
- **官网**: https://play.google.com/store/apps/details?id=com.google.android.apps.accessibility.reveal

### 6. OrCam MyEye Smart
- **公司**: OrCam Technologies (以色列)
- **形态**: 可夹在眼镜上的微型设备
- **价格**: ~$4,500
- **核心能力**: **完全离线** AI 处理。文字朗读、人脸识别、产品识别、货币识别、颜色识别、手势控制、多语言支持。2025 年推出 OrCam MyEye 3.0 (面部表情检测)
- **与 SightLine 的关系**: 硬件形态上是未来方向的参考，但核心是离线+被动模式
- **差异化**: ✅ 完全离线 (隐私优势) ❌ 无 LOD ❌ 无实时对话 ❌ 无上下文感知 ❌ 非常贵
- **官网**: https://www.orcam.com

### 7. Supersense
- **公司**: Mediate (MIT 孵化, 波士顿)
- **形态**: iOS/Android App
- **价格**: 免费 + 订阅 ($4.99/月)
- **核心能力**: 智能扫描 (自动检测文字/文档/货币/条码)、智能引导 (指导用户对准相机)、离线物体探索
- **与 SightLine 的关系**: 纯工具型 App，单次扫描模式
- **差异化**: ❌ 无 LOD ❌ 无实时流 ❌ 无对话 ❌ 无上下文
- **官网**: https://www.supersense.app

### 8. Lumyeye
- **公司**: Lumyeye (法国)
- **形态**: iOS/Android App
- **核心能力**: AI 视觉助手，一键拍照后 AI 分析场景并朗读。支持文档问答 ("这封信需要我做什么？")
- **与 SightLine 的关系**: 类似 Be My AI 的功能定位，被动响应
- **官网**: https://www.lumyeye.com

### 9. Ray-Ban Meta Smart Glasses
- **公司**: Meta + Ray-Ban
- **形态**: 智能太阳镜 (~$299 起)
- **核心能力**: 摄像头 + 扬声器 + 麦克风。通过 Meta AI 语音指令描述场景、读取文字。支持 Be My Eyes 和 Aira 集成
- **与 SightLine 的关系**: 硬件形态上是理想的 SightLine 载体。但 Meta AI 不是为视障设计的，无 LOD 概念
- **差异化**: ✅ 便宜、外观正常 ❌ 非专为视障设计 ❌ 无 LOD ❌ 无上下文感知

### 10. Agiga EchoVision Glasses
- **公司**: Agiga
- **形态**: 智能眼镜 (~$399)
- **核心能力**: 支持 Be My Eyes 和 Aira 直连 (不需手机中介)、公交路线查询 (Transit API)
- **与 SightLine 的关系**: 新兴硬件选择，专为视障设计

---

## 二、开源项目 (Open-Source Projects)

这些是 GitHub 上可以找到的、与 SightLine 功能相关的开源项目。

### 1. Vision-For-Blind (GitHub: jashan20/Vision-For-Blind)
- **描述**: AI 辅助视障系统，集成场景描述 (CNN+RNN)、人脸识别、OCR
- **技术栈**: Python, TTS (GTTS), Tesseract OCR, 自训练深度学习模型
- **与 SightLine 的关系**: 功能组合最接近，但技术较旧，无实时流处理，无 LOD 概念
- **可借鉴**: 人脸识别 + 场景描述 + OCR 的集成思路
- **链接**: https://github.com/jashan20/Vision-For-Blind

### 2. Voice-Vision-Assistant-for-Blind (GitHub: codingaslu)
- **描述**: 基于 GPT-4o 的 AI 视觉助手，支持实时视觉、语音识别、自然语言理解
- **技术栈**: Python, GPT-4o, Google OAuth (日历/联系人/邮件集成), Tavus 虚拟头像
- **与 SightLine 的关系**: 现代 LLM 集成方案，但非开源许可 (proprietary license)
- **链接**: https://github.com/codingaslu/Voice-Vision-Assistant-for-Blind

### 3. SightWalk (GitHub: team8/outdoor-blind-navigation)
- **描述**: 完全开源的户外视障导航系统。使用多线程 CNN 进行物体检测、侧路追踪、碰撞预测
- **技术栈**: Python, ResNet/VGG CNN, Jetson Xavier, 自定义物体追踪算法
- **亮点**: 自定义跟踪算法可以过滤不重要的信息 (类似 SightLine "知趣地闭嘴" 的思想)
- **可借鉴**: 碰撞预测 + 信息过滤的逻辑
- **链接**: https://github.com/team8/outdoor-blind-navigation

### 4. Oculus — A Virtual Eye for the Blind (GitHub: dwij2812/Oculus)
- **描述**: 基于树莓派 + 摄像头的可穿戴 AI 帽子，能描述场景、识别物体、朗读文字
- **技术栈**: Python, YOLOv3, Keras, Raspberry Pi, Pi Camera
- **可借鉴**: 边缘设备 + 云端 AI 的混合架构思路
- **链接**: https://github.com/dwij2812/Oculus

### 5. World-Viewer (GitHub: lcukerd/World-Viewer)
- **描述**: Android App，使用 YOLO 实时识别 80 类物体 + 距离估算 + 语音输出
- **技术栈**: Android, YOLO, TTS, COCO dataset
- **亮点**: 无需互联网连接
- **链接**: https://github.com/lcukerd/World-Viewer

### 6. Seeing-the-World (GitHub: aiformankind)
- **描述**: AI for Mankind 社区开源项目，帮助视障人群导航世界
- **技术栈**: TensorFlow, Docker, 迁移学习
- **链接**: https://github.com/aiformankind/seeing-the-world

### 7. UAE 大学的离线辅助系统 (学术论文, 2025)
- **描述**: 基于树莓派 5 的完全离线多模态辅助系统。集成物体检测、OCR、人脸识别、语音控制
- **技术栈**: Python, 开源 AI 模型 (YOLOv8 等), Raspberry Pi 5
- **亮点**: 隐私优先架构，完全无需云服务
- **论文**: https://www.mdpi.com/1424-8220/25/19/6006
- **状态**: 代码可联系作者获取

### 8. AIris (学术项目, 2024)
- **描述**: AI 驱动的可穿戴眼镜辅助设备。场景描述、OCR、条码扫描、NLP 交互
- **技术栈**: Python, Google Speech API, OCR (Tesseract), 物体检测
- **论文**: https://arxiv.org/html/2405.07606v1

### 9. AIDEN (学术项目, 2025)
- **描述**: 智能手机 AI 助手。集成场景描述、OCR、物体检测、实时问答、物体主动搜索 (有声 + 触觉反馈)
- **亮点**: **主动物体搜索 (Active Object Search)** — 通过持续多模态引导帮助用户定位物体，这是其独特功能
- **论文**: https://arxiv.org/html/2511.06080v1

---

## 三、开源脚手架 / 已造好的轮子 (Frameworks & Building Blocks)

这些是 SightLine 可以直接使用的框架、库、工具。

### 🤖 Agent 框架

| 名称 | 描述 | 与 SightLine 的关系 | 链接 |
|------|------|-------------------|------|
| **Google ADK (Agent Development Kit)** | Google 官方开源 Agent 框架。支持多 Agent 编排、双向音视频流、Function Calling、Gemini 深度集成 | **核心框架** — SightLine 的 Orchestrator + Sub-Agent 架构直接基于 ADK 构建 | https://github.com/google/adk-python |
| **LangGraph** | LangChain 的图式 Agent 框架。支持有状态的多步骤工作流 | 替代方案 — 如果 ADK 不够灵活，可以用 LangGraph 做更细粒度的控制 | https://github.com/langchain-ai/langgraph |
| **CrewAI** | 多 Agent 协作框架，高层抽象 | 替代方案 — 角色化多 Agent 协作 | https://github.com/crewAIInc/crewAI |

### 👁️ 视觉 / CV 库

| 名称 | 描述 | 用途 | 链接 |
|------|------|------|------|
| **face_recognition** | Python 人脸识别库 (基于 dlib)。一行代码生成 128 维 face embedding | SightLine 人脸库的核心依赖 | https://github.com/ageitgey/face_recognition |
| **DeepFace** | 轻量级人脸分析框架。支持 ArcFace/FaceNet/VGG-Face 等多种模型 | face_recognition 的替代方案，更多模型选择 | https://github.com/serengil/deepface |
| **insightface** | 高精度人脸分析。提供 ArcFace 预训练模型 | 生产级人脸识别选择 | https://github.com/deepinsight/insightface |
| **OpenCV** | 计算机视觉基础库 | 图像处理、人脸检测预处理 | https://github.com/opencv/opencv |
| **ML Kit (Google)** | Google 移动端 ML 库，含人脸检测 | 前端人脸检测 (如果在端侧做) | https://developers.google.com/ml-kit |

### 🔊 音频 / TTS / STT

| 名称 | 描述 | 用途 | 链接 |
|------|------|------|------|
| **Gemini Live API** | Google 的实时双向音视频 AI API。支持 Proactive Audio、Affective Dialog | SightLine 的核心通信层 | https://ai.google.dev/gemini-api/docs/live |
| **WebRTC** | 实时通信标准 | 前端音视频采集与传输 | 浏览器内置 |
| **gTTS (Google TTS)** | Google 文字转语音 | 备用 TTS 方案 | https://github.com/pndurette/gTTS |

### 📡 媒体服务器

| 名称 | 描述 | 用途 | 链接 |
|------|------|------|------|
| **MediaMTX** | 开源媒体服务器。接收 RTMP/RTSP，转发为 WebRTC/HLS | 赛后多摄像头支持 (GoPro/DJI/IP 摄像头统一接入) | https://github.com/bluenviron/mediamtx |

### ☁️ 部署 / 基础设施

| 名称 | 描述 | 用途 | 链接 |
|------|------|------|------|
| **Cloud Run** | Google Cloud 无服务器容器平台 | SightLine 后端部署 | GCP |
| **Firestore** | Google Cloud NoSQL 文档数据库 | 用户偏好、人脸库、记忆存储 | GCP |
| **Terraform** | 基础设施即代码 | 自动化 GCP 部署 (+0.2 加分) | https://github.com/hashicorp/terraform |

---

## 四、关键差异化分析

### SightLine 独有的、市场上零竞品的功能

| 功能 | 市场现状 | SightLine 方案 |
|------|---------|---------------|
| **Adaptive LOD** (自适应信息密度) | ❌ **零竞品实现**。所有产品要么静默要么持续说话，没有根据用户状态动态调节的 | ✅ 三级 LOD，基于步频/心率/头部转动/空间类型自动切换 |
| **多维上下文融合** (极短期/会话/长期) | ❌ 没有产品融合生理信号 + 运动状态 + 空间注意力来驱动 AI 输出 | ✅ 三层 Context Fusion |
| **知趣地闭嘴** (默认静默) | ❌ 多数产品要么不说话要么全说。Aira 的真人翻译员有这个直觉，但 AI 产品没有 | ✅ 认知成本模型 + 动态阈值 |
| **Narrative Snapshot** (打断恢复) | ❌ 没有产品支持中断后精准恢复叙述 | ✅ 保存叙事快照，从中断点继续 |

### SightLine 有、但市场上也有的功能 (非独有)

| 功能 | 已有产品 |
|------|---------|
| 场景描述 | Envision, Seeing AI, Be My AI, Google Lookout, Aira |
| OCR 文字读取 | Envision, Seeing AI, Supersense, OrCam |
| 人脸识别 | Envision (Teach a Face), OrCam MyEye, Seeing AI |
| 导航/地理位置 | Google Maps 集成 (多数 App 都有) |
| Google Search 事实验证 | 新功能，少数产品 (Be My AI) 有类似能力 |

---

## 五、战略启示

1. **Adaptive LOD 确实是蓝海** — 搜索了大量产品和学术文献，没有找到任何一个已上线产品实现了基于传感器融合的自适应信息密度控制。学术界有 Context-Aware Adaptive UI 的研究，但没有落地到视障辅助领域。

2. **Aira + Project Astra 是最值得关注的潜在威胁** — Google 和 Aira 合作的 AI Visual Interpreter (基于 Project Astra) 概念上最接近 SightLine 的 "语义翻译官" 定位。但他们目前没有 LOD 和传感器融合。

3. **Envision 是功能最全的现有产品** — 人脸识别、OCR、场景描述都有了。SightLine 必须靠 Adaptive LOD + Context Awareness 来差异化。

4. **开源脚手架非常成熟** — Google ADK + face_recognition + MediaMTX + WebRTC + Firestore，这些轮子都已经造好了，SightLine 的开发重心应该放在 LOD Engine 和 Context Fusion 这两个核心创新点上。

5. **硬件生态正在爆发** — Ray-Ban Meta ($299)、Agiga EchoVision ($399)、Envision Ally Solos 等便宜的智能眼镜正在涌现。SightLine 的 "硬件无关" 设计方向是对的，但短期内用手机 WebRTC 是务实的选择。
