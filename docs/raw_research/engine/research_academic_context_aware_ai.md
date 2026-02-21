# Context-Aware AI for Assistive Technology: Academic Research Survey

> Research Date: 2026-02-21
> Scope: 学术论文、用户研究、自适应细节层级（LOD）、认知负荷、视障辅助

---

## 1. Adaptive Level of Detail (LOD) for AI Assistants

### 1.1 VIPTour + FocusFormer (npj Artificial Intelligence, 2025)

- **标题**: "AI system facilitates people with blindness and low vision in interpreting and experiencing unfamiliar environments"
- **来源**: [Nature npj AI](https://www.nature.com/articles/s44387-025-00006-w)
- **核心概念**: FocusFormer 算法将复杂场景转化为结构化、个性化的分层图。通过三个轴过滤信息：美学、新鲜度/新奇度和基本需求（导航、安全）。"BLV-in-the-Loop Adapter" 根据用户喜好/厌恶实时更新推荐。
- **Context 集成方式**: 将海量环境信息重构为稀疏分层图以降低认知负荷。通过持续用户反馈动态适应个人偏好，集成多注意力机制从复杂场景中提取有意义的信息。
- **结果**: 认知地图准确率提升 772.73%，长期记忆增强 200%，积极情绪反应提升 67.9%，可用性得分持续高于 80/100。
- **与实时导航的关系**: 这是现有最接近自适应 LOD 概念的系统。但它是为观光/探索场景设计的，不是为实时导航设计的。不使用运动状态或生物指标来驱动细节适配。实时导航产品可以采用分层图概念和 BLV-in-the-Loop 个性化，但需要添加运动感知的细节切换。

### 1.2 ShortScribe (CHI 2024)

- **来源**: [ACM DL](https://dl.acm.org/doi/10.1145/3613904.3642839)
- **核心概念**: 短视频的三级分层视觉摘要。BLV 用户根据兴趣选择概览 vs 详细描述。使用 BLIP-2 + GPT-4。
- **Context 集成方式**: 固定层级由用户选择；无自动上下文适配。
- **与 SightLine 的关系**: 证明用户接受分层细节层级，但手动选择模型增加认知负荷——自动 LOD 切换可以填补这一空白。

### 1.3 Describe Now (DIS 2025)

- **来源**: [ACM DL](https://dl.acm.org/doi/10.1145/3715336.3735685)
- **核心概念**: 用户驱动的音频描述，提供两个细节层级（简洁和详细）。
- **Context 集成方式**: 用户必须手动请求描述，决定何时以及在哪个层级。
- **关键发现**: 增加的用户控制导致更高的认知负荷，因为用户必须不断决定何时请求描述。这直接支持了自动、上下文驱动的 LOD 切换，而非用户发起的控制。

### 1.4 RAVEN (ASSETS 2025)

- **来源**: [arXiv 2510.06573](https://arxiv.org/abs/2510.06573)
- **核心概念**: VR 环境中 BLV 用户通过自然语言查询和修改 3D 场景。
- **Context 集成方式**: 自然语言交互进行场景探索。
- **关键发现**: 在用户研究中，8 名 BLV 参与者中有 5 名明确要求"场景描述中的自适应细节层级"作为期望功能——直接的用户需求证据。

---

## 2. Context-Aware Computing for Accessibility

### 2.1 ContextAgent (CUHK + Columbia, 2025)

- **标题**: "ContextAgent: Context-Aware Proactive LLM Agents with Open-World Sensory Perceptions"
- **来源**: [arXiv 2505.14668](https://arxiv.org/html/2505.14668v1)
- **核心概念**: 使用可穿戴传感器数据的主动（而非仅被动）LLM Agent 框架。四个组件：(1) 感官知觉处理（第一人称视频、音频、通知），(2) 通过 VLM 的面向主动的上下文提取，(3) 人格上下文集成（用户偏好、身份、历史），(4) 带主动必要性评分（1-5 分）的上下文感知推理。
- **Context 集成方式**: 多通道感官融合（视觉、声学、通知）与用户人格建模结合。系统生成显式推理轨迹，分配主动分数，仅在合理时干预（分数 >= 3）。使用"先思考再行动"方法。
- **结果**: 主动预测准确率提升最高 8.5%，工具调用 F1 提升 7.0%，泛化到域外场景（90.9% 准确率）。与 70B 基线相比，7B 参数模型具有竞争力。
- **与 SightLine 的关系**: 直接适用于确定何时向盲人用户主动传递信息的架构。主动必要性评分系统可适配到导航上下文：安全关键情况（障碍物、交通）高分，可以等待的环境场景信息低分。

### 2.2 VISA System (IIT, 2025)

- **标题**: "Visual Impairment Spatial Awareness System for Indoor Navigation and Daily Activities"
- **来源**: [MDPI/PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11766877/)
- **核心概念**: 三层架构：基础层（AR 标记、物体检测、深度）、中间层（避障、寻路）、高级层（空间感知综合）。将视野简化为九个可管理区域以进行直观的物体沟通。
- **Context 集成方式**: 来自 AR 定位、神经网络和深度传感器的多层数据集成。通过 TTS 和 STT 的自然人机交互。
- **与 SightLine 的关系**: 九区域空间网格是降低空间描述认知负荷的实用方法。三层架构映射了应用于系统能力层（而非信息密度）的 LOD 方法。

### 2.3 AIDEN (University of Alicante, 2025)

- **标题**: "An Artificial Intelligence-based Assistant for the Visually Impaired"
- **来源**: [arXiv 2511.06080](https://arxiv.org/html/2511.06080v1)
- **核心概念**: 使用 YOLOv8 + LLaVA 进行场景描述、OCR 和物体查找的智能手机应用。分布式计算模型（移动端捕获，服务器处理）。多模态反馈（音频、触觉、适配视觉）。
- **Context 集成方式**: 有限的上下文感知——主要响应即时视觉输入。Object Finder 优先最近检测到的物体。后续问题可在同一捕获图像内进行细化信息检索。
- **与 SightLine 的关系**: 展示了实用的部署架构和用户接受度（TAM 分数在"优秀"和"最佳"之间），但突出了上下文持久性的差距——无用户档案集成，无环境历史，无自适应细节层级。

---

## 3. User Profiles + Real-Time Environmental Context Integration

### 3.1 "Say It My Way" (CHI 2026, University of Maryland)

- **标题**: "Say It My Way: Exploring Control in Conversational Visual Question Answering with Blind Users"
- **来源**: [arXiv 2602.16930](https://arxiv.org/html/2602.16930)
- **核心概念**: 三阶段研究（实验室、10 天日记、访谈），11 名盲人参与者使用 Be My AI。研究盲人用户如何通过提示技术自定义 AI 交互。
- **Context 集成发现**:
  - 系统回复平均比用户输入长 10 倍（严重的冗余失衡）
  - 55% 的熟悉环境 vs 34% 的陌生环境中出现自定义行为
  - 专业场景显示 74% 自定义 vs 休闲场景 52%
  - 最常用技术：分解提示（9/11 参与者）——将复杂任务分解为顺序子问题
  - 74.8% 的日记交互使用直接问题而无显式提示，表明自然对话是首选
- **关键建议**: (1) 支持目标上下文与图像上传一起提交，(2) 实现持久冗余度控制和偏好记忆，(3) 添加以用户为中心的空间参考框架，(4) 支持任务特定的自定义类别。
- **与 SightLine 的关系**: 最有力的证据表明盲人用户需要但目前缺乏持久的偏好/档案系统。自定义行为随环境熟悉度和上下文类型变化的发现直接支持自动上下文驱动的适配，而非手动提示。

### 3.2 "Beyond the Cane" (ACM TACCESS, 2022)

- **标题**: "Beyond the Cane: Describing Urban Scenes to Blind People for Mobility Tasks"
- **来源**: [PMC/ACM](https://pmc.ncbi.nlm.nih.gov/articles/PMC9491388/)
- **核心概念**: 两个实验，13 名手杖用户（5 名先天盲，8 名后天盲），研究城市行动中的信息优先级。提出跨三个抽象层级的分层信息模型（低：直接环境；中：街道段/交叉路口；高：街区/地区）。
- **Context 集成发现**:
  - 路线和当前位置信息排名最高；碰撞危险物（树、消防栓、电线杆）得分最低，因为手杖用户已经能检测这些
  - 先天盲参与者出行频率高 11 倍，提问少 3 倍——经验降低信息依赖性
  - 精确位置描述优于模糊描述（3.24 vs 2.69 平均分）
  - 后天盲用户更频繁地请求信息，优先物体位置数据
- **设计建议**: 构建分层优先级系统；根据出行频率、经验水平、失明发生时间（先天 vs 后天）和 O&M 熟练度调整内容；优先尺寸/身份/位置信息而非外观信息。
- **与 SightLine 的关系**: 直接建立了用户档案驱动的内容过滤的证据基础。先天盲 vs 后天盲的区别是没有当前系统实现的关键用户档案维度。分层信息模型（低/中/高）自然映射到 LOD 层级。

### 3.3 Wearable AI System with Step-Aware LLM (2024)

- **标题**: "AI-based Wearable Vision Assistance System for the Visually Impaired"
- **来源**: [arXiv 2412.20059](https://arxiv.org/abs/2412.20059)
- **核心概念**: 帽子安装摄像头 + Raspberry Pi 4 系统，使用 LVLM 进行实时音频描述。包括带听觉碰撞警告的距离传感器。一键用户训练用于识别新人和物体。
- **与 SightLine 的关系**: 展示了实际的边缘设备部署，但缺乏复杂的用户档案集成或自适应细节控制。"一键训练"是最小形式的用户档案。

---

## 4. Personalized Scene Description / Adaptive Verbosity

### 4.1 BLV Preferences for LVLM Descriptions (Submitted CHI 2025)

- **标题**: "How Blind and Low-Vision Individuals Prefer Large Vision-Language Model-Generated Scene Descriptions"
- **来源**: [arXiv 2502.14883](https://arxiv.org/abs/2502.14883)
- **核心概念**: 评估了跨多个 LVLM 的六种描述类型。开发了基于 BLV 用户研究数据训练的新自动评估指标。
- **关键发现**:
  - 描述"有助于减少恐惧并提高可操作性"，但用户评分在充分性和简洁性方面差异很大
  - GPT-4o 尽管是最先进的模型，并非始终首选
  - 没有单一描述方法能普遍满足所有 BLV 用户
  - 简洁性和充分细节之间存在强烈张力
- **与 SightLine 的关系**: 直接证明一刀切的描述是失败的。用户偏好的广泛差异是个性化、自适应描述系统的核心理由。模型能力本身并不预测用户满意度的发现表明，适配层（如何过滤和呈现信息）比原始模型更重要。

### 4.2 Use Cases of AI-Powered Scene Description (CHI 2024)

- **标题**: "Investigating Use Cases of AI-Powered Scene Description Applications for Blind and Low Vision People"
- **来源**: [arXiv 2403.15604](https://arxiv.org/html/2403.15604v1)
- **核心概念**: 16 名 BLV 参与者的两周日记研究。识别五个主要用例：场景描述、识别主体、识别特征、学习应用、无特定目标。意外用途：避免恶心/危险物体、检查是否有他人在场、解决分歧。
- **关键发现**:
  - 当前 AI 描述的满意度低（2.76/5）和信任度低（2.43/4）
  - "满意度和信任分数与描述准确性并不一致"——用户应用上下文知识来弥补系统限制
  - 用户重视 AI 在隐私敏感查询和独立解决问题方面的价值
  - 照片质量（光线、清晰度）显著影响描述实用性
- **与 SightLine 的关系**: 准确性和满意度之间的差距揭示了描述什么的上下文感知比多准确地描述更重要。用户用自身上下文知识弥补差描述的发现表明，有效的系统应支持和增强用户认知，而不是替代它。

### 4.3 EgoBlind (NUS + Multiple Universities, 2025)

- **标题**: "EgoBlind: Towards Egocentric Visual Assistance for the Blind People"
- **来源**: [arXiv 2503.08221](https://arxiv.org/abs/2503.08221)
- **核心概念**: 首个从盲人个体收集的第一人称视频 QA 数据集。1,210+ 视频，4,927+ 问题，跨六个类别（信息阅读、安全警告、导航、社交沟通、工具使用、其他资源）。基准测试 15+ MLLM。
- **关键发现**:
  - 最佳 MLLM 准确率：~56% vs 人类表现 87.4%——巨大差距
  - 模型在以下方面失败：用户意图理解、空间方向追踪、时间推理、安全评估和幻觉预防
  - 模型优先静态显著物体而非以用户为中心的需求
  - 谄媚问题：模型对不存在的物体产生幻觉，而不是说"我不知道"
- **与 SightLine 的关系**: 建立了当前 MLLM 用于盲人辅助的性能上限。六个问题类别为 LOD 优先级提供了自然分类法：安全警告应始终是最高优先级（主动），而信息阅读可以是较低优先级（按需）。模型在用户意图推理方面失败的发现直接支持了显式用户档案 + 上下文集成的需求。

### 4.4 Proactive vs. Reactive Assistance Research

- **"Be Quiet?" (INTERACT 2003)**: 基础论文表明主动建议被认为比预期更自然；客观任务表现在手动、被动和主动条件下相似。
- **LlamaPIE (arXiv 2025)**: 主动入耳式辅助将用户准确率从 37% 提升到 87%，用户觉得它比被动系统更不打扰。
- **与 SightLine 的关系**: 有力证据表明，在上下文合适时，主动信息传递优于纯被动系统。支持混合模型：安全关键警报主动，详细探索被动/按需。

---

## 5. Synthesis: Key Gaps and Opportunities

| 维度 | 已有研究 | 缺失部分 |
|------|---------|---------|
| 细节层级 | 固定 2-3 级，用户选择（ShortScribe, Describe Now） | 连续、自动、上下文驱动的 LOD 切换 |
| 运动感知 | 行走速度仅作为设计指导被提及一次 | 无系统使用活动状态（行走/站立/坐下）驱动细节适配 |
| 用户档案集成 | 一键物体训练（AIDEN）；喜好/厌恶（VIPTour） | 无系统区分先天盲 vs 后天盲需求、经验水平或 O&M 熟练度 |
| 主动安全 | 模型检测障碍物但对危险相关性评估不佳 | 无系统结合主动必要性评分（ContextAgent）和盲人特定安全分类法（EgoBlind） |
| 认知负荷管理 | 在所有研究中被认为是关键问题 | 无系统使用生物指标/运动代理来实时估计和管理认知负荷预算 |
| 冗余度个性化 | 用户手动提示要求更多/更少细节（Say It My Way） | 无持久偏好记忆或自动冗余度校准 |
| 信息层级 | "Beyond the Cane" 提出路线 > 位置 > 物体 | 无系统将此层级实现为自动化优先级过滤器 |

**最强的研究支持设计原则**: 将沉默作为设计元素，使用运动状态作为认知负荷代理，主动传递安全信息，当用户静止时按需提供丰富场景描述。这种混合方法得到多个独立研究发现的支持，但尚未在任何现有系统中实现。

---

## Sources

- [VIPTour/FocusFormer - npj AI](https://www.nature.com/articles/s44387-025-00006-w)
- [Say It My Way - arXiv/CHI 2026](https://arxiv.org/html/2602.16930)
- [EgoBlind - arXiv](https://arxiv.org/abs/2503.08221)
- [Beyond the Cane - PMC/ACM TACCESS](https://pmc.ncbi.nlm.nih.gov/articles/PMC9491388/)
- [Use Cases of Scene Description - CHI 2024](https://arxiv.org/html/2403.15604v1)
- [BLV Preferences for LVLM - arXiv](https://arxiv.org/abs/2502.14883)
- [ContextAgent - arXiv](https://arxiv.org/html/2505.14668v1)
- [VISA System - MDPI/PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11766877/)
- [AIDEN - arXiv](https://arxiv.org/html/2511.06080v1)
- [AI-based Wearable Vision - arXiv](https://arxiv.org/abs/2412.20059)
- [ShortScribe - CHI 2024](https://dl.acm.org/doi/10.1145/3613904.3642839)
- [Describe Now - DIS 2025](https://dl.acm.org/doi/10.1145/3715336.3735685)
- [RAVEN - ASSETS 2025](https://arxiv.org/abs/2510.06573)
- [LlamaPIE - arXiv](https://arxiv.org/html/2505.04066v2)
