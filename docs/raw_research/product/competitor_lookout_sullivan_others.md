# Google Lookout, Sullivan+ 及其他竞品 -- 研究报告

> 研究日期: 2026-02-21
> 研究来源: Web Search, Google Play, App Store, AppleVis, Accessible Android

---

## 一、Google Lookout

### 概览
Google Lookout 是一款免费的 Android 独占无障碍 App，使用计算机视觉和生成式 AI 帮助低视力或盲人用户。2019 年发布，持续积极维护和更新。

### 功能（7 个操作模式）
1. **Text** - 扫描文字并朗读
2. **Documents** - 通过 OCR 捕获整页文字或手写（离线工作，设备端处理）
3. **Explore** - 识别周围的物体、人和文字
4. **Currency** - 识别纸币
5. **Food Labels** - 通过标签或条码识别包装食品
6. **Find** - 扫描周围找到特定物体（门、浴室、杯子、车辆），带方向和距离指示
7. **Images** - 拍摄、描述并就图片提出后续问题（AI 驱动，仅英语）

### AI 模型
- Play Store 列表确认："Have Gemini describe your surroundings in Images mode (English only)"
- 据 Accessible Android 深入评测，Lookout 目前使用**旧版 Gemini 模型** -- 当被问及 Samsung Galaxy S24 时，回应最近的 Samsung S 设备是 S23，表明训练数据过时
- 评测者认为 Google 应升级到 **Gemini 2.0 Flash** 以获得实时摄像头集成能力
- 另外，**TalkBack**（Android 屏幕阅读器）现使用 **Gemini Nano** 多模态进行设备端图像描述，但这是不同产品

### 硬件 / 平台
- **仅 Android**（Android 6.0+，任何 Android 手机）
- **无 iOS 版本**
- **无眼镜/可穿戴支持** -- 推荐将手机放在衬衫口袋或挂绳上，摄像头朝外
- Google 正在单独开发 **Android XR 智能眼镜**（预计 2026），可能最终整合类似无障碍功能，但不是 Lookout 本身

### 与 Seeing AI 比较
- Lookout 是 Android 独占；Seeing AI 是 iOS 独占 -- 互补生态系统
- 都提供文本阅读、文档 OCR、场景描述、货币和条码/产品识别
- **Seeing AI 优势**: 更好的条码扫描引导（用提示音帮助定位条码）；触觉反馈功能；免费
- **Lookout 优势**: 设备端 OCR 离线工作（非常快）；Find 模式带方向/距离；30+ 种语言自动检测

### 用户投诉和局限性
1. **Documents 模式不朗读** -- 扫描并 OCR 文字但不读出来；需要独立的屏幕阅读器
2. **不支持文本格式或表格数据** -- 仅显示识别的文字，对结构化文档不够用
3. **PDF 支持差** -- 对纯图像扫描有问题，特别是阿拉伯语等语言
4. **条码检测限于食品标签** -- 区域特定数据库有限制
5. **无条码扫描引导** -- 不像 Seeing AI 的提示音系统
6. **图像描述初始简短** -- AI 后续问题曾地理限制（仅美国、英国、加拿大）超过一年
7. **无视频描述能力** -- 与部分竞品相比是重大缺口
8. **过时的 Gemini 模型** -- 训练数据落后于当前知识

### 活跃/维护状态
是的，截至 2025 年积极维护。Google 继续发布更新。

---

## 二、Sullivan+（TUAT 开发）

### 概览
Sullivan+ 是由 **TUAT Inc.**（韩国公司）开发的视觉辅助 App。2018 年发布，通过智能手机摄像头识别增强盲人和低视力用户的信息可访问性。

### 功能
1. **AI Mode** - 自动找到拍摄照片的最佳分析
2. **Text Recognition** - 通过 OCR 找到并读取文字
3. **Face Recognition** - 识别面孔并报告估计年龄和性别
4. **Image Description** - 识别物体并创建场景描述句
5. **Color Recognition** - 两种模式: 单色（屏幕中心）和全屏（整个视图的主色调）
6. **Light Brightness** - 使用前置摄像头报告环境光照水平
7. **Magnifying Glass** - 摄像头变焦放大/缩小物体或文字，支持颜色反转

### AI 模型
- Sullivan+ 不使用 OpenAI GPT 或标准西方 AI 模型
- 由 **SKT（SK Telecom）的 A.X Multimodal AI** 视觉模型驱动
- 也整合了 SKT 的 **NUGU** 语音 AI 技术
- SKT 的 A.X Multimodal AI 已在十亿张图片上训练

### 价格
- **免费下载**
- 提供**一周免费试用**（暗示付费墙后有高级功能，但英语源中未找到确切订阅价格）
- 还提供 **Sullivan Lite**（精简版）和 **Sullivan Finder**（独立物体查找 App）

### 平台
- **iOS** 和 **Android**
- App Accessibility (MA) 认证
- 完整 VoiceOver 支持
- 多语言支持

### 用户反馈
- 一般对无障碍认证和 VoiceOver 支持给予正面评价
- **技术问题**: AppleVis 用户报告功能在 iPhone XR + iOS 14.2 上不工作，点击拍摄按钮无反馈，设置菜单崩溃，App 将亮度设为 100%
- 在韩国/亚洲以外知名度较低

### 与 Seeing AI / Be My Eyes 的区别
- **独特功能**: 光照亮度检测、颜色识别（全屏模式）、带颜色反转的放大镜
- **AI 模型**: 使用韩国 SKT AI 而非 Microsoft/OpenAI 模型
- **来源**: 韩国公司，韩语支持更强
- **不够精致**: 根据用户报告的 bug 和崩溃
- **较小的用户基础**，英语社区反馈较少

---

## 三、其他竞品

### Supersense（Mediate 开发）
- **平台**: iOS 和 Android
- **核心优势**: 智能扫描模式自动确定内容类型（文字、文档、货币、物体、条码）
- **功能**: 文本阅读、货币识别、条码扫描、Object Explorer and Find、多页文档扫描、PDF 阅读、摄像头引导系统、阅读历史
- **离线**: 大多数功能无需互联网
- **价格**: $4.99/月, $49.99/年, 或 $99.99 终身。免费层包括 Quick Read、Import Image/PDF 和 Read History
- **无障碍**: 完整 VoiceOver 支持

### KNFB Reader（现为 OneStep Reader）
- **平台**: iOS, Android, Windows 10
- **开发者**: 现由 Sensotec 开发（从 National Federation of the Blind 接手）
- **核心优势**: 最高质量的印刷文档 OCR，被视为金标准
- **功能**: 带触觉反馈的文本检测、低视力高亮、多页批处理模式、导出到 Google Drive/Dropbox、30+ 种语言
- **价格**: **$99.99** 一次性购买 -- 高价是其最大障碍
- **状态**: 仍可用但面临免费 App 竞争

### TapTapSee
- **平台**: iOS 和 Android
- **功能**: 拍照或最多 10 秒视频，识别任何 2D 或 3D 物体，并口头描述
- **简洁性**: 非常简单的单一用途 App，专注物体识别
- **状态**: 仍可用但更新不频繁；被更全面的 App 超越

### Looktel（Money Reader）
- **专注**: 主要是货币识别
- **功能**: 使用摄像头实时货币识别
- **状态**: 仍可用但范围狭窄

---

## 四、竞争格局汇总表

| App | 平台 | AI 模型 | 价格 | 眼镜支持 | 核心优势 |
|-----|------|---------|------|----------|----------|
| Google Lookout | Android | Gemini (旧版) | 免费 | 无 (未来 Android XR) | 离线 OCR, Find 模式 |
| Sullivan+ | iOS + Android | SKT A.X Multimodal | 免费+试用 | 无 | 颜色/光照检测 |
| Seeing AI | iOS | GPT-4o | 免费 | 无 | iOS 最佳，触觉反馈 |
| Be My Eyes | iOS + Android | GPT-4 (Be My AI) | 免费 | Ray-Ban Meta | 人工志愿者 + AI 混合 |
| Envision AI | iOS + Android + 眼镜 | GPT-4 | 免费增值 | Envision Glasses, Ally Solos | 智能眼镜硬件 |
| Aira | iOS + Android | 人工代理 + Project Astra | 订阅 | 已退出 | 人工驱动准确性 |
| Supersense | iOS + Android | 专有 | $4.99/月 或 $99.99 终身 | 无 | 自动内容检测 |
| KNFB Reader | iOS + Android + Windows | 专有 OCR | $99.99 一次性 | 无 | 最佳文档 OCR |
| TapTapSee | iOS + Android | 云视觉 | 免费 | 无 | 简单物体识别 |
