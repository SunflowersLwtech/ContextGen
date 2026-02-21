> ⚠️ **DEPRECATED** — 本文档内容已被 `SightLine_Final_Specification.md` 吸收。以 Final Spec 为准。保留仅作历史参考。

# **SightLine: 产品形态设计与极简部署战略**

## **1\. 终极愿景：从“辅助 App”到“无障碍感官操作系统 (OS)”**

真正的无障碍视觉伴侣，绝不是让用户举着一部绑死在特定厂商上的手机。SightLine 的终极形态不是一个 App，而是一个\*\*“硬件无关的云端感官大脑 (Hardware-Agnostic Cloud Brain)”\*\*。

我们致力于打造无障碍领域的标准通信层——**SightLine Edge Protocol (SEP)**。通过提供一个中央处理服务器（基于 Google Cloud \+ Gemini ADK），我们允许世界上任何硬件厂商（Apple, Sony, 华强北白牌硬件）通过标准协议无缝接入我们的“自适应 LOD 引擎”。

### **平台级解耦战略 (The Decoupling Strategy)**

我们将物理世界的数据流彻底解耦为三大独立通道，厂商只需负责数据采集，SightLine 负责所有的语义理解与状态调度：

#### **① 视觉流设备无关 (SEP-Vision)**

* **入口载体**：胸前摄像头、智能眼镜（如 Meta Ray-Ban）、甚至盲杖上的微型摄像头。  
* **解耦标准**：系统不依赖任何特定的相机 SDK。硬件只需向中央服务器推送标准的 WebRTC 视频流 (H.264/VP8) 或通过 WebSocket 持续发送抽帧图片流 (JPEG)。  
* **出口载体**：目前视觉主要作为单向输入，未来可扩展至 AR 眼镜的显示输出。

#### **② 语音流设备无关 (SEP-Audio)**

* **入口与出口载体**：AirPods、开放式骨传导耳机、助听器。  
* **解耦标准**：音频输入输出彻底分离。硬件只需通过 WebRTC 或 WebSocket 发送标准格式（如 16kHz PCM / Opus）的麦克风拾音流，并接收系统下发的 TTS 音频流进行播放。系统内置 VAD (静音检测)，硬件完全不需要做任何音频处理。

#### **③ 上下文与生理流设备无关 (SEP-Telemetry)**

* **入口载体**：手机内置传感器（加速度计、麦克风、GPS、时钟）为 Core 数据源；Apple Watch 等智能手表为 Optional 增强数据源。
* **解耦标准**：所有非音视频的传感器数据，统一抽象为 JSON 格式的 Telemetry (遥测) 数据报文。Core 字段（step\_cadence, motion\_state, ambient\_noise\_db, gps, time\_context）全部来自手机，无需额外设备；Optional 字段（heart\_rate）在有手表时自动启用。我们的 Orchestrator Agent 会自动将其转化为大模型的 Context（上下文）。

## **2\. 侧端 Context 分析：我们需要什么？能获取什么？**

为了让云端大模型真正理解视障用户的”心情”与”物理状态”，我们通过 SEP-Telemetry 通道获取以下 Context。**核心设计原则：手机即主传感器，零额外设备即可驱动完整 LOD 系统。**

### **Core 层：手机自带传感器（零额外硬件）**

#### **① 物理移动感知 (Locomotion State)**

* **来源**：手机加速度计 — iOS `CMMotionActivityManager` + `CMPedometer` / Android `ActivityRecognitionClient` + `TYPE_STEP_COUNTER`。
* **核心指标**：运动状态 (`motion_state`: stationary/walking/running/in\_vehicle) + 步频 (`step_cadence`)。
* **LOD 响应**：walking/running → LOD 1 静默；stationary → LOD 2/3 描述展开；in\_vehicle → 允许高 LOD（用户不需要听路况，可以详细描述窗外）。步频为 0（驻足）时系统升级 LOD，展开详尽的环境描述。

#### **② 环境噪声感知 (Ambient Noise Awareness)**

* **来源**：手机麦克风后台 RMS 分析（与语音输入并行，不冲突）。
* **核心指标**：环境噪声分贝值 (`ambient_noise_db`)。
* **LOD 响应**：高噪声 (>80dB，如地铁站) → 增加”发声成本”，仅高价值信息突破阈值，TTS 输出更简短；安静环境 (<40dB，如图书馆) → AI 采用低语模式，避免打扰周围人；中等环境 (50-65dB) → 正常输出。

#### **③ 时空定位 (Spatiotemporal Context)**

* **来源**：手机 GPS + 手机时钟。
* **核心指标**：地理坐标 (`gps`) + 时间上下文 (`time_context`: 时段推断)。
* **LOD 响应**：空间转换（GPS 跳变，如室外→室内）自动触发 LOD 升级（用户进入新空间需要更多信息）；时间段推断辅助预判行为模式（早高峰通勤 vs 晚间休闲）。

### **Optional 层：智能手表增强（有则更好）**

#### **④ 心理/压力状态感知 (Stress Detection) — 可选**

* **来源**：智能手表（Apple Watch、运动手环）。
* **核心指标**：实时心率 (`heart_rate`)。
* **LOD 响应**：心率突升（如 75→115）表示用户可能感到恐慌或迷失。Orchestrator 瞬间打断当前冗长描述，强制切入 LOD 1（安全模式），提供最简短的安抚与关键方向指令。
* **无手表时的降级策略**：系统仍可通过步频突变（突然加速/停下）+ 语音语调变化间接推断紧张状态，LOD 系统正常运行。

## **3\. Hackathon 极简部署：透明的“硬件仿真模式”**

在 23 天的赛程内，死磕硬件接口会偏离核心。我们采用\*\*“架构解耦 \+ 协议仿真”\*\*的策略，这在工业界是绝对专业的生产级实践 (Hardware-in-the-Loop Simulation)：

1. **音视频接入**：利用智能手机的 WebRTC (PWA 网页) 扮演未来的智能眼镜和耳机，验证 SEP-Vision 和 SEP-Audio 通道。  
2. **侧端数据模拟器 (Developer Console)**：在 Web 界面构建一个公开透明的传感器控制台。通过滑块和按钮，按照 SEP-Telemetry 标准 JSON 协议向云端持续注入心率、步频等数据。

**强调点**：我们的云端 Agent 是 100% 真实运行的。我们在做的是**硬件仿真测试**，以证明只要第三方硬件按照 SEP 协议发送数据，SightLine 系统就能完美兼容并实时反应。

## **4\. 产品架构与中央网关数据流图**

graph TD  
    subgraph Third-Party Hardware Ecosystem \[第三方硬件生态 (设备无关)\]  
        A\[任意智能眼镜/摄像头\] \--\>|SEP-Vision: WebRTC / JPEG流| D{SightLine API Gateway}  
        B\[任意蓝牙耳机/助听器\] \<--\>|SEP-Audio: PCM/Opus双向流| D  
        C\[智能手表/戒指\] \--\>|SEP-Telemetry: JSON 报文| D  
          
        %% Hackathon Mock %%  
        M\[PWA Developer Console\] \-.-\>|模拟生成 JSON 注入| C  
        P\[PWA 手机摄像头/麦克风\] \-.-\>|模拟充当| A  
        P \-.-\>|模拟充当| B  
    end  
      
    D \--\>|统一路由解包| E\[Google Cloud Run 中央大脑\]  
      
    subgraph Cloud Layer \[SightLine Core: ADK 多智能体编排\]  
        E \--\>|Telemetry 数据| F(Context Parser)  
        F \--\> G(Orchestrator Agent)  
        G \<--\> H\[Adaptive LOD Engine\]  
        G \<--\> I\[Gemini Live Native Audio\]  
        G \<--\> J\[Gemini Vision Pro\]  
    end  
      
    I \--\>|生成自适应语音| E  
    E \--\>|通过网关下发| B

## **5\. 给评委的终极 Pitch (平台生态与架构前瞻性)**

这段陈述将彻底把你的项目与普通的“聊天机器人 App”区分开来：

"When building for accessibility, creating another siloed App is the wrong approach. Visually impaired users don't want to hold a phone; they want to use their smartwatches, their hearing aids, and emerging smart glasses.

That's why we didn't build an App; we built **SightLine—a hardware-agnostic Cloud Operating System for accessibility.** \>

We completely decoupled the architecture into three unified channels: **Vision, Audio, and Telemetry**. Any hardware manufacturer can connect to our central API gateway using the SightLine Edge Protocol (SEP). If a Sony earbud streams audio and an Apple Watch streams heart rate telemetry, our ADK Orchestrator fuses them in the cloud. If the heart rate spikes, our Adaptive LOD engine instantly alters the AI's speaking style to calm and guide the user.

To prove this production-ready backend today without writing proprietary iOS code, we built a transparent Developer Simulation Console in our web client. The AI, the agents, and the LOD state machine are 100% real. We are simply simulating the edge sensors to prove that SightLine is ready to be the universal brain for the next generation of wearable tech."

*(“在无障碍领域，再造一个孤立的 App 是错误的做法。视障用户不想举着手机，他们想用他们的智能手表、助听器和新兴的智能眼镜。这就是为什么我们没有造 App，我们打造了 **SightLine——一个硬件无关的无障碍云端操作系统**。我们将架构彻底解耦为视觉、音频和遥测三大通道。任何硬件厂商都可以通过 SEP 协议连接到我们的中央网关。如果索尼耳机输入音频，Apple Watch 输入心率，我们的 ADK 中枢会在云端将它们融合。如果心率飙升，自适应 LOD 引擎会立即改变 AI 的说话风格以安抚用户。为了在今天展示这个生产就绪的后端，我们在 Web 端内置了一个开发者仿真控制台。AI 和智能体是 100% 真实的。我们只是在模拟边缘传感器，以证明 SightLine 已经准备好成为下一代穿戴设备的通用大脑。”)*