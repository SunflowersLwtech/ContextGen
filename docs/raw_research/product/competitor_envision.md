# Envision AI -- 竞品研究报告

> 研究日期: 2026-02-21
> 研究来源: Web Search, AppleVis, AFB AccessWorld, App Store

---

## 1. 公司概览

Envision（letsenvision.com）是一家荷兰辅助技术公司，为盲人和低视力用户构建 AI 工具。产品线包括 Envision App（iOS/Android）、Envision Glasses（智能眼镜）和较新的 Ally AI 助手平台。声称在 180+ 个国家服务数千名用户。

---

## 2. 完整功能清单

### Envision App 功能:

#### 文本识别（OCR）:
- **Instant Text**: 实时视频模式 -- 摄像头持续实时朗读文字。离线可用（仅拉丁字母语言）。
- **Scan Text**: 拍照并通过布局检测提取文字（识别标题、列、段落顺序）。完整精度需要互联网；离线模式可用但无布局检测。
- **Batch Scan**: 多页文档扫描，带音频引导的边缘检测。离线可用。
- **Handwriting Recognition**: 读取手写笔记、明信片、信件、清单。
- **60+ 种语言支持**（包括阿拉伯语和乌尔都语）。

#### 场景和环境:
- **Describe Scene**: 拍照并生成 AI 环境描述。仅在线。
- **Ask Envision**: 后续 AI 助手（GPT-4 驱动），回答关于扫描文字或描述场景的自然语言问题。
- **Detect Colors**: 识别衣物、墙壁、物体的颜色。
- **Detect Light**: 光照水平检测。
- **Scan Barcode**: 通过条码扫描查询产品信息。

#### 人物和物体:
- **Find People**: 检测附近的人并通过音频提示；说出已识别面孔的姓名。
- **Find Objects**: 从应用内列表中选择常见物体进行定位。
- **Teach Envision / Face Recognition**: 拍 5 张面部照片 + 姓名来训练 App。本地存储在设备上。
- **Explore**: 通用环境探索模式。

#### 其他:
- **Recognize Cash**: 货币识别（需要在线下载货币包）。
- **Scan QR Code**: QR 码阅读器。
- **Library**: 保存和导出扫描文档。
- **Reader**: 带前进/后退/暂停控制的文本回放。

### Ally AI 助手（独立 App）:
- 基于 LLM + 视觉语言模型（VLM）构建的对话式 AI 助手。
- 集成 OCR、天气 API、网络搜索、日历。
- 免费层：无限对话，每次上限 10 分钟。
- Ally Pro: 无限分钟，额外功能。EUR 10/月或 EUR 100/年。
- 在 iOS、Android、网页浏览器、Mac 和 Envision Glasses 上可用。

---

## 3. Envision Glasses

### 硬件平台: 基于 **Google Glass Enterprise Edition 2** 构建。
- SoC: Qualcomm 四核, 1.7GHz, 10nm
- 摄像头: 8 MP 广角视野
- 电池: 常规使用 5-6 小时
- 重量: 不到 50 克
- 防水防尘
- 音频: 定向单声道扬声器, USB 音频, 蓝牙音频

**关键说明:** Google 于 2023 年 3 月停产了 Glass Enterprise Edition 2。Google 不再计划软件更新。Envision 继续销售和支持，但底层硬件平台已到达生命周期终点。

### 新硬件 -- Ally Solos Glasses（2025）:
Envision 与 **Solos** 合作创建下一代眼镜:
- 双高清摄像头
- 最长 15 小时电池续航
- 定向立体扬声器（最小声音泄漏）
- 波束成形麦克风
- 触控板控制
- USB-C 快速充电
- 轻便、防溅
- 预订价约 $599（2025 年 10 月开始发货）
- 通过蓝牙与智能手机配对运行 Ally AI 助手

### Meta 合作:
Envision 在 Meta Connect 2024 上使用 Llama 3.1 在 **Meta 的 Project Aria 眼镜**上展示了原型。集成了视觉和语言处理用于无障碍。仍处于原型/研究阶段。

---

## 4. "不会幻觉"声明验证

**发现: 未找到 Envision 在其营销材料或网站上明确声称"不会幻觉"或"不会编造内容"。** 其营销强调"速度、可靠性和获奖设计"，但未专门讨论幻觉。

**然而，有一个重要的架构区别:**
- **Instant Text / Scan Text（OCR 模式）**: 使用传统 OCR 技术（模式匹配字符识别），**不是**生成式 AI。传统 OCR 从定义上不会"幻觉" -- 它要么正确识别字符，要么无法识别，要么误识别。它不会编造不存在的内容。
- **Describe Scene / Ask Envision**: 使用生成式 AI（Ask Envision 用 GPT-4）。这些**可以**幻觉，因为它们是标准 LLM/VLM 输出。

---

## 5. 实时 vs 异步

**混合模式:**
- **Instant Text**: 真正的实时连续 OCR，从实时视频流。文字一被检测到就朗读。
- **Scan Text / Batch Scan**: 异步 -- 拍照后处理。
- **Describe Scene**: 异步 -- 拍照后生成描述。不是连续视频描述。
- **Ally on Glasses**: 半实时 -- 用户问"我前面有什么？"，Ally 拍一张图片并回应。更像按需对话，而非连续流式传输。
- **Find People/Objects**: 带音频提示的连续检测（实时）。

---

## 6. 上下文感知 / 细节层级（LOD）

**未找到明确的 LOD 或自适应细节设置。** Envision 似乎不提供用户可配置的描述详细度或细节层级。

然而:
- **Ask Envision** 提供交互式后续: 获得场景描述后，用户可以就描述内容提出具体后续问题，有效允许用户驱动的 LOD。
- 场景描述一直在改进 -- Envision 声称它们"更丰富、更具上下文感知，反映类人感知"，现在能识别物体之间的关系。
- 没有证据表明自动的基于情境的适应（例如检测用户在走路 vs 坐着并相应调整细节）。

---

## 7. 记忆 / 个性化

- **Face Recognition Library**: 用户拍 5 张照片 + 添加姓名来教面孔。数据**仅存储在设备本地** -- 不与其他用户共享或上传到云端。需要互联网来访问面部库进行识别（即使在眼镜上也是如此）。
- **Teach Envision**: 扩展到允许用户教自定义物体（未来功能）。
- **Ally**: 被描述为"与你一起学习和成长"，但除了面部识别外的具体记忆/个性化机制未详细说明。
- **未找到描述风格或详细度的持久用户偏好画像。**

---

## 8. 硬件支持

- **iOS**: iPhone/iPad, iOS 15.6+
- **Android**: Android 7+
- **Mac**: macOS 12.5+
- **Web 浏览器**: Chrome 和 Safari 优化
- **Envision Glasses**: Google Glass Enterprise Edition 2
- **Ally Solos Glasses**: 新 Solos 硬件平台（2025）
- **Meta Project Aria**: 仅原型/研究
- **未找到 Apple Watch、CarPlay 或其他可穿戴集成**

---

## 9. 价格

### Envision App:
- 免费下载，每月 10 次操作（14 天免费试用后）
- 月付: $4.99
- 6 个月: $24.99
- 年付: $33.99
-（价格因地区而异；最近提到了 50% 的降价）

### Ally App:
- 免费: 无限对话，每次 10 分钟上限
- Ally Pro: EUR 10/月或 EUR 100/年（无限分钟，高级功能）

### Envision Glasses:
- Read Edition: $1,899（仅文本阅读功能）
- Home Edition: $2,499（所有功能包括场景描述、面部识别、Ally）
- Professional Edition: $3,499（终身免费软件更新）
- 软件更新: 购买当年 + 次年免费。之后 $199/年可选。
- 各版本之间有升级路径。

### Ally Solos Glasses:
- 预订价: 约 $599（活动后价格更高）

---

## 10. 用户投诉和局限性

### 来自 AppleVis、App Store 评论、AFB AccessWorld 和社区论坛:
- App 需要登录才能使用；部分用户报告登录失败
- Library 功能令人困惑；保存的文件有时消失
- 仅支持后置摄像头；无前置摄像头选项
- 无法识别文本文档中嵌入的图片（导致错误）
- 手写识别在比较测试中被报告为较弱（AFB 评测发现无法识别测试文档上的手写）
- 所有语音命令仅支持英语
- 无逐行前进/后退导航（用户请求）
- TTS 引擎提示让部分用户烦恼
- 订阅取消被报告为困难
- Find 功能被部分用户报告为"没用"
- Envision Glasses: 相对基于手机的替代品价格昂贵（$1,899-$3,499）
- 眼镜基于已停产的 Google Glass EE2 硬件（未来可靠性担忧）
- 离线面部识别不工作（只检测人，不识别姓名）
- 离线模式仅支持拉丁字母语言的 OCR
- Describe Scene 需要互联网；无离线场景描述

### 与竞品比较:
- Envision 被评为 OCR 速度略快于 Seeing AI
- Envision 在产品标签（酒瓶）上表现优于 Seeing AI
- Envision "略微更准确"（部分用户报告）
- 然而，Seeing AI 完全免费（Microsoft 补贴），而 Envision 有订阅

---

## 11. 开源状态

### GitHub 组织: github.com/Envision-AI

已发布仓库:
- **OCR-SDK**: iOS OCR SDK，用于 Dense Text 和 Scene Text 识别。这是一个关键的开源贡献。
- **yolov7-to-tflite**: 将 YOLOv7 ONNX 模型转换为 TFLite 格式的工具。
- **LMMPlayground**: （仓库存在但未找到详细信息）
- **elevenlabs-python**: （Fork/贡献）

**核心 Envision App 和 Ally 不是开源的。** 仅发布了特定 SDK 和工具。主要 AI 模型、App 代码和眼镜固件是专有的。

### Meta/Llama 连接:
Envision 使用 Meta 的 Llama 3.1（开源 LLM）用于 Ally 助手，实现成本效益的设备端推理。这是一个值得注意的开源依赖。

---

## 12. 离线能力总结

### 离线可用:
- Instant Text（仅拉丁语言）
- Scan Text（无布局检测，仅拉丁语言）
- Batch Scan
- Find Object
- Find People（仅提示音；无姓名识别）
- Explore
- Recognize Cash（货币必须预先下载）
- Detect Colors / Detect Light
- Scan QR Code
- Voice Commands

### 需要互联网:
- Describe Scene
- Ask Envision（GPT-4）
- 按姓名面部识别
- Scan Text 的布局检测
- 非拉丁语言 OCR
- Ally 对话
- 所有网络搜索和日历功能

**重要**: 离线模式必须在 Envision Glasses 上手动启用；断开连接时不会自动切换。

---

## 与 SightLine 对比的关键要点

1. **Envision 以眼镜形态差异化** -- 最早将 AI 辅助技术带到智能眼镜的公司之一
2. **OCR 是传统的（非生成式）**，意味着确实不会幻觉文字 -- 但 Envision 未明确营销此区别
3. **场景描述基于照片，不是连续视频** -- 相比潜在的实时系统是关键限制
4. **无自适应 LOD** -- 描述是一刀切的，虽然 Ask Envision 允许交互式后续
5. **Google Glass EE2 硬件已停产** -- Ally Solos（Solos 硬件）似乎是未来路径，加上 Meta Project Aria 原型
6. **价格显著**: 眼镜 $1,899-$3,499，App $34-$60/年，相比免费替代品
7. **面部识别本地存储** -- 良好的隐私模型但受互联网姓名识别限制
8. **离线 OCR 支持充实**但 AI 功能受限（场景描述、Ask Envision）
