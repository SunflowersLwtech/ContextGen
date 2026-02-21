# Commercial Products: Context Integration Approaches Comparison

> Research Date: 2026-02-21
> Scope: 辅助视障产品 + 通用 AI 平台的上下文集成策略

---

## Part 1: Assistive AI Products for Blind/Visually Impaired

### 1. Be My Eyes + Be My AI (GPT-4/GPT-4o)

**用户历史/档案集成**: 无。每次与 AI 的交互从零开始。志愿者端也不保留用户历史。

**实时 Context**: 基于相机——用户将手机相机对准场景，AI（GPT-4o 多模态）生成描述。支持会话内后续问题。GPT-4 可以扫描冰箱并从内容物中建议食谱。

**多源融合**: 单源上下文：一次一张相机图片 + 该会话的对话线程。无 GPS、日历、用户偏好或历史数据集成。

**定价**: 完全免费。由企业合作伙伴和赞助商资助。

**关键局限**: 无持久记忆或个性化；需要智能手机和互联网；非实时连续模式；无导航或空间定向；无可穿戴形态。

---

### 2. Google Lookout

**用户历史/档案集成**: 无。每次会话独立。

**实时 Context**: 七种模式：Text、Documents、Explore（连续场景识别）、Food Labels、Scan、Currency、Find（beta）。Image Q&A 功能（2024 新增）。

**多源融合**: 主要单源（相机）。不集成 GPS、用户日历或个人数据。

**定价**: 免费（Google 产品）。仅 Android。

**关键局限**: 仅 Android；无持久上下文或个性化；无可穿戴集成；Find 模式仍为 beta。

---

### 3. Microsoft Seeing AI

**用户历史/档案集成**: 人脸识别功能需要用户先教应用识别人——一种初级的用户构建知识库。无更广泛的偏好记忆。

**实时 Context**: 多通道：Short Text、Documents、Scenes、People（人脸 + 情绪识别）、Currency、Color、Light Detector、Handwriting。"More info"按钮使用生成式 AI 提供更丰富描述。空间探索：用户触摸屏幕可听到物体在照片中的位置。

**多源融合**: 最小融合。各通道独立运行。人脸识别是最接近"组合上下文源"的。

**定价**: 免费。iOS 和 Android。2024 年从 18 种语言扩展到 36 种。

**关键局限**: 非连续实时模式（快照式）；人脸识别需要手动初始注册；无导航或空间定向。

---

### 4. Aira

**用户历史/档案集成**: 辅助产品中**最先进的用户档案**。人工客服可访问之前会话的笔记。用户可指定偏好（沟通风格、细节层级、具体需求）。

**实时 Context**: 真人客服实时查看用户相机画面并提供口头指导。客服可在指导时访问网络搜索、地图等资源。与 Envision Glasses 合作实现免提流式传输。

**多源融合**: 人工客服是"融合引擎"，结合视觉画面、用户历史/笔记、网络查找和对话上下文。这是辅助领域最真正的多上下文系统，但融合是人工中介的，非自动化。

**定价**: 订阅制（Silver/Gold/Platinum 层级）。许多公共场所免费使用（机场、大学、政府大楼）。

**关键局限**: 昂贵；依赖人工客服（可扩展性受限）；需要互联网；AI 对客服的增强有限。

---

### 5. OrCam MyEye 3 Pro

**用户历史/档案集成**: 人脸识别库：用户教设备识别特定人（设备端存储）。无更广泛的行为学习。完全离线运行。

**实时 Context**: 轻触或语音命令触发。阅读任何表面文字，通过条形码识别产品，识别人脸。方向模式（beta）："我前面有什么？"提供物体的空间描述。Smart Reading：语音命令导航文档。

**多源融合**: 限于单模式操作：相机输入 + 存储的人脸库。无 GPS，无互联网丰富化，无日历集成。

**定价**: 约 $3,689-$4,490。高端硬件产品。

**关键局限**: 非常昂贵；无互联网连接；无导航功能；方向模式仍为 beta。

---

### 6. Envision Glasses

**用户历史/档案集成**: Teach a Face 功能。"ally"助手（2024-2025）在会话内维护对话上下文。无跨会话记忆。

**实时 Context**: 基于 Google Glass Enterprise Edition 2 硬件（可穿戴、免提）。功能：Instant Text、Scan Text、Batch Scan、Describe Scene、Detect Light、Recognize Cash、Detect Colors、Find People、Find Objects、Explore。"Ask Envision"功能：扫描文档并提问。Aira 集成。

**多源融合**: ally 助手可结合场景描述与后续 Q&A。Aira 集成添加人工中介层。无 GPS/日历/个人数据集成。

**定价**: Read Edition: $1,899; Home Edition: $2,499; Professional Edition: $3,499。

**关键局限**: 昂贵的硬件加持续的软件成本；依赖老化的 Google Glass 硬件平台；AI 功能需互联网；电池续航受限。

---

### 7. Sullivan+ (TUAT / SK Telecom)

**用户历史/档案集成**: 无。无人脸识别库。

**实时 Context**: AI Mode：自动场景检测和描述性句子生成，无需按快门（连续模式）。Object Finder、Color Recognition、Text Recognition、Consumer Electronics Mode（QR 码配对三星 SmartThings 家电）。

**多源融合**: SK Telecom 的 A.X 多模态 AI 驱动图像描述。SmartThings 集成是独特的跨域功能。无 GPS、日历或个人数据集成。

**定价**: 免费。200+ 国家 300,000+ 下载。

**关键局限**: 韩国市场中心开发；无可穿戴形态；无持久用户记忆。

---

## Part 2: General-Purpose Context-Aware AI Platforms

### 8. Google Gemini (Memory + Context Window)

**用户历史/档案集成**: 显式记忆（2025.2）+ 自动记忆（2025.8）。Google 应用集成：连接 Gmail、Calendar、Google Docs、Google Photos 实现深度个人上下文。企业版从工作模式、邮件、日历和文档中构建个人记忆。

**实时 Context**: 100 万 token 上下文窗口（Gemini 1.5 Pro / Gemini 3 Pro）。可同时处理文本、音频、图像、视频、PDF 和代码。Gemini Live：移动端带相机输入的实时对话 AI。

**多源融合**: 通用 AI 平台中最复杂的上下文融合架构。结合：长期记忆 + 当前会话上下文 + Google 应用数据 + 实时多模态输入。

**定价**: 免费层。Gemini Advanced: $19.99/月。

**关键局限**: 记忆功能默认开启（opt-out），引发隐私担忧；跨应用上下文需要授予广泛的 Google 账户访问权限；记忆非结构化。

---

### 9. OpenAI ChatGPT (Memory + Personalization)

**用户历史/档案集成**: Saved Memories：存储用户分享的特定事实。Reference Chat History（2025）：引用过去对话学习兴趣和偏好。Custom Instructions：跨对话持久的用户定义指令。

**实时 Context**: GPT-4o 多模态：实时处理文本、图像、音频和视频。语音模式带相机输入（移动端）。

**多源融合**: 结合：保存的记忆 + 自定义指令 + 当前对话上下文 + 多模态输入。无外部数据源集成（邮件、日历）。

**定价**: 免费层。ChatGPT Plus: $20/月。ChatGPT Pro: $200/月。

**关键局限**: 记忆相对非结构化（扁平事实列表，非知识图谱）；无个人生产力工具集成；记忆可能不准确。

---

### 10. Apple Intelligence (On-Device Personal Context)

**用户历史/档案集成**: Semantic Index：设备端向量数据库，包含所有用户内容的 embedding——短信、邮件、约会、照片、笔记、文件。超越语义搜索到"显著性"（理解什么对用户来说是重要的）。跨应用搜索。所有个人数据处理在设备上进行。

**实时 Context**: 屏幕感知：Siri 可以看到和理解当前屏幕显示内容。App Intents 框架：Siri 有每个应用的能力数据库。

**多源融合**: 最深度集成的个人上下文系统：结合设备端语义索引 + 当前屏幕内容 + 应用能力 + 对话上下文。Private Cloud Compute 扩展到 Apple silicon 服务器处理复杂请求同时维护隐私保障。

**定价**: 免费（随兼容 Apple 设备提供：iPhone 15 Pro+，M 系列 Mac/iPad）。

**关键局限**: 仅 Apple 生态；硬件门控；Siri V2 架构面临重大延迟。

---

### 11. Humane AI Pin (DISCONTINUED)

**已停产（2025.2.28）**。$699 设备 + $24/月订阅。灾难性的负面评论。被 HP 收购，所有设备变砖。

试图结合：位置 + 相机 + 记忆 + 网络搜索 + 时间的上下文建议。理论上是任何可穿戴设备中最雄心勃勃的上下文融合。实践中很少可靠工作。

**教训**: 硬件可靠性（过热、电池、相机质量）是基础。AI 响应太慢且太不准确。

---

### 12. Rabbit R1

$199（一次性）。初始炒作（10万+ 台售出）。后续评论压倒性负面。描述为"应该是手机应用的应用"。

LAM（大型动作模型）大部分无法按宣传工作。2024.7 隐私泄露：所有用户聊天和设备配对数据被记录且无删除选项。

---

### 13. Meta Ray-Ban Smart Glasses

**用户历史/档案集成**: 个性化用户记忆。与 Meta 社交图谱（Messenger、WhatsApp、Instagram）集成。通过 Spotify/Apple Music 集成学习音乐偏好。

**实时 Context**: Live AI：响应关于佩戴者所看到和听到的提示。上下文感知协助：检测环境并建议附近地标、餐厅、交通。实时翻译和字幕。增强视觉识别。

**多源融合**: 结合：相机 + 麦克风 + GPS + 用户记忆 + Meta 社交图谱 + 第三方集成。AnyMAL 模型：跨文本、音频、视频和 IMU 运动传感器数据的统一推理。智能手机作为中介，实现云处理同时维持可穿戴形态。

**定价**: Ray-Ban Meta（Gen 2，无显示屏）：$299 起。Meta Ray-Ban Display（2025，带显示屏）：$799。

**关键局限**: 依赖配对智能手机和 Meta 应用；关于始终可用的相机和麦克风的隐私担忧；AI 处理需要互联网；记忆和个性化与 Meta 账户绑定。

---

## Part 3: Cross-Category Comparison

### Context Integration Architecture Matrix

| 产品 | 用户档案/历史 | 实时环境 | 多源融合 | 处理方式 | 价格 |
|------|-------------|---------|---------|---------|------|
| **Be My Eyes** | 无 | 相机快照 + 对话 | 单源 | Cloud (OpenAI) | 免费 |
| **Google Lookout** | 无 | 相机（7 模式） + Q&A | 单源 | 设备端 + Cloud | 免费 |
| **Seeing AI** | 仅人脸库 | 相机（8 通道） | 最小 | 设备端 + Cloud | 免费 |
| **Aira** | 客服笔记 | 实时相机（人工） | 人工融合 | Human + Cloud | 订阅 |
| **OrCam MyEye 3** | 仅人脸库 | 相机 + 语音 | 单源 | 完全离线 | ~$3,700-4,500 |
| **Envision Glasses** | 人脸库 + ally 对话 | 相机（可穿戴） + GPT Q&A | 新兴（ally） | Cloud (OpenAI) | $1,900-3,500 |
| **Sullivan+** | 无 | 相机（连续）+ SmartThings | 最小（视觉 + IoT） | Cloud (SK Telecom) | 免费 |
| **Google Gemini** | 自动记忆 + Google 应用 | 100 万 token 窗口 + 多模态 | 深度 | Cloud + 设备端 | 免费 / $20/月 |
| **ChatGPT** | 保存的记忆 + 聊天历史 | 多模态 | 中等 | Cloud | 免费 / $20-200/月 |
| **Apple Intelligence** | Semantic Index（设备端） | 屏幕感知 + App Intents | 深度 | 设备端 + Private Cloud | 免费（硬件门控） |
| **Meta Ray-Ban** | 用户记忆 + 社交图谱 | 相机 + 麦克风 + GPS + 翻译 | 最深的可穿戴融合 | Cloud（经手机） | $299-799 |

### Key Findings

1. **辅助产品的"上下文鸿沟"**: 每个盲人辅助产品都以零或最小用户历史运行。无产品学习用户日常路线、家庭布局或偏好。通用 AI 平台已大举投资持久记忆，但辅助产品都没有跟进。

2. **人工 vs AI 融合**: Aira 是辅助领域唯一实现真正多上下文融合的产品，但通过人工客服而非算法。昂贵、难以扩展、不一致。无产品自动化了 Aira 客服所做的事情。

3. **可穿戴形态作为上下文启用器**: OrCam、Envision Glasses、Meta Ray-Ban 的可穿戴形态自然捕获更多环境上下文。但只有 Meta Ray-Ban 将可穿戴与持久用户记忆和多源上下文融合结合。

4. **无产品同时实现三层**: 没有现有产品成功结合 (a) 持久用户档案/历史 + (b) 实时环境感知 + (c) 自适应信息密度——专为视障用户。这是明确的产品机会。

---

## Sources

- [Be My Eyes - OpenAI](https://openai.com/index/be-my-eyes/)
- [Google Lookout Blog](https://blog.google/company-news/outreach-and-initiatives/accessibility/lookout-app-help-blind-and-visually-impaired-people-learn-about-their-surroundings/)
- [Seeing AI - Perkins School](https://www.perkins.org/resource/seeing-ai-ios-app-recognizing-people-objects-and-scenes/)
- [Aira](https://aira.io/)
- [OrCam MyEye 3 Pro](https://www.orcam.com/en-us/orcam-myeye-3-pro)
- [Envision Glasses](https://www.letsenvision.com/updates/glasses)
- [Sullivan+ on Google Play](https://play.google.com/store/apps/details?id=tuat.kr.sullivan&hl=en)
- [Gemini Context Window 2025](https://www.datastudios.org/post/google-gemini-context-window-token-limits-and-memory-in-2025)
- [OpenAI Memory](https://openai.com/index/memory-and-new-controls-for-chatgpt/)
- [Apple Intelligence](https://www.apple.com/apple-intelligence/)
- [Humane AI Pin Discontinued](https://www.macrumors.com/2025/02/18/humane-ai-pin-discontinued/)
- [Meta Ray-Ban Display](https://www.meta.com/ai-glasses/meta-ray-ban-display/)
- [Ray-Ban Meta AI Features](https://about.fb.com/news/2024/09/ray-ban-meta-glasses-new-ai-features-and-partner-integrations/)
