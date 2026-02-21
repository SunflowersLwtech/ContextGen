# **SightLine: Agent 编排与多维上下文建模架构**

## **1\. 核心编排策略：Hierarchical Sub-Agent (层级化子智能体)**

在探讨 Multi-Agent, Sub-Agent 还是 Agent Team 时，我们需要回归业务本质：**视障辅助是一个“容错率极低、延迟敏感”的强干预场景。** 如果采用去中心化的平行 Agent Team（让几个 Agent 自己去辩论和商量），不仅延迟不可控，还可能在用户耳边产生混乱的反馈。因此，基于 Google ADK，我们采用 **Hierarchical Sub-Agent（带强中枢的层级化子智能体）** 架构。

### **架构拓扑图**

\[SEP API 网关 (处理音视频/遥测数据)\]  
        │  
        ▼  
【Orchestrator Agent (中枢指挥官)】 \--- (内置自适应 LOD 引擎)  
        │  
        ├─▶ \[Vision Sub-Agent\] (负责: 帧解析、OCR、人脸情感识别)  
        ├─▶ \[Navigation Sub-Agent\] (负责: 地理位置、路线、POI)  
        └─▶ \[Memory Sub-Agent\] (负责: 跨会话偏好读取与写入)

### **为什么这样编排？(ADK 最佳实践)**

1. **统一出口 (Single Voice)**：只有 Orchestrator 拥有直接和用户“说话”的权力。所有的 Sub-Agent 只以 JSON/Text 形式向 Orchestrator 汇报结果。这样确保了人格的统一。  
2. **极速路由**：Orchestrator 使用高响应速度的模型 (Gemini 2.5 Flash)，快速判断当前用户的意图和 Context，按需挂载和调用最重的 Sub-Agent (如使用 Gemini 2.5 Pro 的 Vision 节点)。

## **2\. Context Awareness (多维上下文融合算法)**

我们从 SEP 协议收到的 Context 不是独立发挥作用的，我们需要一个 **Context Fusion Algorithm (上下文融合算法)**。你的原有 iMeanPiper 代码库中的状态机可以直接升级为这套逻辑。

我们将 Context 分为三个生命周期维度，在每次生成 Prompt 之前进行动态融合 (Prompt Injection)：

### **A. 极短期上下文 (Ephemeral Context) \- 毫秒级到秒级**

* **数据源**：当前视频帧、音频打断信号、手表心率突变、陀螺仪剧烈晃动。  
* **处理逻辑**：拥有最高中断优先级 (Interrupt Priority)。如果是危险信号，Orchestrator 会直接清空当前的 TTS 播放队列，降级 LOD，并插播警告。

### **B. 会话期上下文 (Session Context) \- 分钟级到小时级**

* **数据源**：用户今天出行的目的（“我要去面试”）、当前所在的空间类型（室内/室外/车上）、近 30 分钟的步频均值。  
* **处理逻辑**：维持系统的平稳运行。例如：系统知道用户目前“正在喝咖啡”，LOD 会稳定在等级 3，允许深度的闲聊和环境描述。

### **C. 长期上下文 (Long-term Context) \- 跨会话级**

* **数据源**：Firestore 数据库。  
* **处理逻辑**：决定 AI 的个性化设定和先验知识（见第 3 节）。

## **3\. 跨 Session 记忆与用户建模 (User Data Modeling)**

要让用户觉得 AI 越来越“懂我”，我们需要实现**跨会话的常识记忆机制**。在 23 天的 Hackathon 内，我们不需要去搭复杂的向量数据库 (Vector DB)，而是使用 **Firestore 构建一个结构化的记忆图谱 (Structured Memory Graph)**。

我们将记忆分为两大类，由 Memory Sub-Agent 负责异步更新：

### **① 显式偏好 (Explicit Profile)**

这是硬性的医疗与个性化数据，优先级极高。

* **视力状态**：是全盲 (Totally Blind) 还是低视力 (Low Vision)？（低视力用户可能只需要 AI 提醒小字，全盲需要全量描述）。  
* **物理特征**：是否有导盲犬？（如果有，AI 不需要提示地面的小水坑，因为导盲犬会避开）。  
* **语言与语速**：偏好的 TTS 说话速度（很多盲人习惯听 2.0x 甚至 3.0x 的超快语速）。

### **② 隐式常识 (Implicit Epistemology) \- 参考 Gemini App 模式**

这是系统在日常陪伴中“偷偷”学到的。你可以复用你之前写的 PreferenceLearner 模块。

* **常去地点实体**：{ "office": "Tencent Building B", "favorite\_coffee": "Starbucks on 5th Ave" }。下次用户说“带我去买咖啡”，系统直接路由到那家星巴克。  
* **社交关系拓扑**：系统通过 Vision 认出了某个人，用户说“这是我老板”。Memory Sub-Agent 会写入 { "face\_id\_xyz": {"name": "David", "relation": "Boss"} }。下次摄像头看到他，AI 会主动低声说：“你老板 David 走过来了，看起来心情不错。”  
* **环境压力触发器**：系统学习到“每次用户走到拥挤的地铁站，心率都会升高”。未来系统预测到即将进入地铁站时，会**提前**主动切换到温和、安抚的 LOD 模式。

## **4\. 核心算法流程 (ADK Orchestrator 伪代码逻辑)**

以下是 SightLine 在云端每一次“思考”的核心编排流（你可以直接映射到 Python ADK 代码中）：

\# 每次收到用户语音/视频/遥测数据时的处理流

async def process\_user\_input(input\_stream, edge\_telemetry):  
    \# 1\. 记忆与状态挂载 (Context Loading)  
    user\_profile \= await MemoryAgent.fetch\_profile(user\_id)  
    current\_lod \= LODManager.get\_current\_level()  
      
    \# 2\. 遥测异常阻断 (Telemetry Interrupt)  
    if edge\_telemetry.is\_panic\_mode(): \# 例如: 心率飙升 \> 120  
        LODManager.force\_downgrade(level=1)  
        return Orchestrator.generate\_safety\_response()

    \# 3\. 智能路由 (Sub-Agent Dispatch)  
    intent \= await IntentClassifier.analyze(input\_stream)  
      
    if intent \== "read\_text" or intent \== "describe\_scene":  
        vision\_context \= await VisionAgent.analyze\_frames(camera\_buffer)  
    elif intent \== "where\_am\_i":  
        geo\_context \= await NavigationAgent.get\_location()  
          
    \# 4\. 融合生成 (Context Fusion Prompting)  
    \# 将提取的 Context、记忆、当前 LOD 限制，全部融合到 System Prompt 中  
    system\_prompt \= build\_dynamic\_prompt(  
        lod=current\_lod,   
        memory=user\_profile,   
        vision=vision\_context  
    )  
      
    \# 5\. Gemini 实时流式输出 (Native Audio)  
    async for audio\_chunk in GeminiLiveAPI.stream(system\_prompt, input\_stream):  
        yield audio\_chunk  
          
    \# 6\. 后台异步记忆巩固 (Memory Consolidation)  
    \# 如果对话中产生了新的偏好，后台悄悄更新 Firestore  
    asyncio.create\_task(MemoryAgent.extract\_and\_save\_new\_facts(conversation\_history))

## **5\. 给评委的陈述亮点 (The Wow Factors)**

向评委展示这段架构时，你要强调以下几个“极其昂贵且高级”的特性：

1. **"The Memory Sub-Agent" (长时记忆智能体)**：  
   * “我们的 AI 不仅有眼睛，还有海马体。通过我们自研的后台记忆智能体，即使用户每天开启一个新的 Session，SightLine 依然记得用户偏好极快的语速，记得对面走来的是用户的亲属。这就是真正的跨会话建模。”  
2. **"Non-blocking Vision Orchestration" (非阻塞视觉编排)**：  
   * “视觉解析是很慢的。在我们的层级架构中，Orchestrator 能够先用零点几秒回复‘让我看看...’，同时异步挂载 Vision Sub-Agent 去处理高分辨率帧。这种编排保证了盲人用户在音频通道上永远有及时的反馈（零静默焦虑）。”  
3. **"Implicit Stress Learning" (隐式压力学习)**：  
   * “结合 SEP 协议的遥测数据，我们的算法不仅仅是感知当下的心率。它能结合时空 Context 进行机器学习：系统发现用户每次经过某个十字路口时步频都会紊乱、心率升高。系统会记住这个‘高压坐标’，下次接近该路口时，无需用户开口，AI 会提前切入高精度的导航引导。”