# **SightLine: 核心产品定义与冠军战略重构**

**项目名称**: SightLine (Powered by Adaptive LOD)

**参赛类别**: Gemini Live Agent Challenge \- Live Agents

**核心定位**: 视障群体的“随身语义翻译官” (Semantic & Contextual Interpreter)，而非物理避障雷达。

## **1\. 痛点重构：认清工程现实与AI边界**

在盲人辅助领域，最容易陷入的陷阱是试图让 AI 成为“盲人的物理眼睛”（替代导盲犬或白手杖）。然而，从工程现实来看，这在当前的云端大模型架构下是不成立的，任何懂技术的评委都会对此提出致命质疑：

1. **时延与生命安全 (Latency vs. Safety) 悖论**：  
   * 盲人躲避飞驰的电动车或脚下的台阶，是一个**毫秒级 (ms)** 响应的物理生存问题。  
   * 基于“摄像头捕获 ![][image1] 云端传输 ![][image1] Gemini 视觉解析 ![][image1] LLM 生成 ![][image1] TTS 语音 ![][image1] 回传”的完整链路，即便在极佳网络下，时延也至少是 **1-2秒起步**。  
   * 在物理移动中，2秒的时延意味着致命危险。它绝对不能，也不应该替代盲杖 (White Cane)。  
2. **极低的容错率 (Zero Margin for Error)**：  
   * 类似于自动驾驶的 L4/L5 困境，LLM 本质上是概率预测模型，存在幻觉 (Hallucination)。如果 AI 误将“施工坑洞”识别为“平地”，后果不堪设想。

## **2\. 战略转轴：我们到底解决什么问题？**

既然做不到“物理避障的白手杖”，SightLine 的真实落地价值是什么？

**盲人深层的日常痛点，不仅是“不撞墙”（白手杖已解决），更是严重的“信息剥夺” (Information Deprivation)。** 白手杖能告诉盲人前面有一堵墙，但无法告诉他们：

* 这堵墙上贴着一张“今日特价咖啡”的海报。  
* 前面的餐桌是空的，还是已经有人坐了。  
* 手里拿的药盒，保质期到哪一天，每次应该吃几粒。  
* 站在对面的朋友，现在是微笑着点头，还是在皱眉头。

**战略结论：** 我们要将重点从“利用视觉进行空间微导航”彻底转移到\*\*“利用多模态大模型进行复杂环境的语义解析”\*\*。这是 Gemini Live API 真正能降维打击，且对时延容忍度极高（1-2秒完全可接受）的完美场景。

## **3\. 冠军级设计：将“时延劣势”转化为“LOD 高光时刻”**

如何向评委证明我们懂技术边界，又能给出绝佳的解决方案？答案就是我们已有的 **Adaptive LOD (自适应细节层级) 系统**。

我们要讲的故事是：**“我们知道 AI 有时延，我们知道盲人走路需要全神贯注，所以我们的 AI 懂得知趣地闭嘴。它只在最安全、最需要的时刻，提供最合适的细节。”**

### **移动状态 (高物理风险) —— 触发 LOD 1**

* **用户场景**：用户在走路，白手杖在探路，听觉需要全神贯注用来听周围的汽车声和环境音。  
* **痛点**：此时 AI 如果喋喋不休，会造成严重的**认知过载 (Cognitive Overload)** 并掩盖环境音，极其危险。  
* **系统响应**：完全静默，或者仅提供极高颗粒度的 Macro-Navigation（宏观导航）。例如：“前方十米是星巴克入口”。绝不进行微观避障提示。

### **探索状态 (中等风险，时延容忍度高) —— 触发 LOD 2**

* **用户场景**：用户停下脚步，在超市货架前摸索。  
* **痛点**：不知道眼前的空间布局和物品分类。  
* **系统响应**：AI 介入，提供中等细节的空间语义。例如：“你现在正面对饮料区，左手边是可乐，右手边是果汁。”

### **互动/静止状态 (零物理风险，极高细节需求) —— 触发 LOD 3**

* **用户场景**：用户坐在椅子上，手里拿着一份外卖菜单或一封信。这正是盲人最无助的“信息黑洞”。  
* **痛点**：无法获取高密度的文本和图像信息。  
* **系统响应**：火力全开。调用高精度的 Vision 解析、OCR 和外部工具 (Grounding)。  
  * *交互亮点*：结合 **Narrative Snapshot (叙事快照)** 功能，AI 开始详细阅读成分表或菜单。若用户中途听到异响打断提问（“刚才那是什么声音？”），AI 瞬间中断阅读，用 LOD 1 简短回答（“旁边有人拉开椅子”），随后精准从刚才中断的“副作用”段落恢复朗读。

## **4\. Hackathon 评委路演策略 (The Pitch)**

在 4 分钟的 Demo 视频或路演中，采用以下话术策略将形成对其他竞品的降维打击：

"When building for the visually impaired, the industry often makes a fatal mistake: trying to replace the white cane with AI. But a 2-second cloud latency is deadly when you're crossing a street.

We didn't build a radar; we built a **Semantic Interpreter**.

More importantly, we introduced **Adaptive Level-of-Detail (LOD)**. SightLine knows when you are moving and stays absolutely silent to let you hear traffic. But when you sit down at a café, it unleashes the full power of Gemini Vision to read you the menu, describe the room, and even tell you if the waiter is smiling.

We embrace the engineering limits of cloud AI, and we use brilliant software architecture to work around them, delivering an immersive, safe, and truly context-aware experience."

*(“在为视障人士开发产品时，业界常犯一个致命错误：试图用 AI 替代白手杖。但在过马路时，2秒的云端时延是致命的。我们没有造雷达，我们造的是‘语义翻译官’。更重要的是，我们引入了自适应细节层级 (LOD)。SightLine 知道你何时在移动，并保持绝对安静让你聆听交通。但当你坐在咖啡馆，它会释放 Gemini Vision 的全部潜力为你读菜单。我们正视工程现实，并用绝佳的软件架构解决它。”)*

## **5\. 接下来技术实施的 Focus**

1. **剥离旅游业务**：从 iMeanPiper 代码库中剥离旅游、景点推荐等强业务绑定代码。  
2. **ADK 重新编排**：利用 Google ADK 将现有的 LOD Manager、Intent Classifier 等模块包装为 Orchestrator Agent。  
3. **引入视觉模态**：接入 Gemini Vision 流，重点训练/Prompt 优化其对文本（OCR）、人物表情、室内布局的语义解析能力。

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAXCAYAAADpwXTaAAAAdUlEQVR4XmNgGAWjgHpAXl5+L7oY2QBo2D90MbKBnJycDRCXoYuTDYCuO6egoGCOLs4gKytrQg4GGnYLaOg+dMP8yMFAg66BMNAIFhQDSQVAV00EGuSNLk4yABqiCDSsE12cLAA07BO6GNkAaNhhdLFRMNwAADgJIGwPRW62AAAAAElFTkSuQmCC>