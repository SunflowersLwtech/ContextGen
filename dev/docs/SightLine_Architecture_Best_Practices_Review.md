# SightLine 架构最佳实践与演进战略报告 (2026-02)

## 💡 核心演进结论：从“集中式云原生”走向“边缘枢纽 (Edge Hub)”

经过对现有代码 (`TelemetryAggregator.swift`, `lod_engine.py`, `orchestrator.py`) 的极度深挖，我们发现 SightLine 项目在 Hackathon 阶段的架构虽然在哲学上追求了“硬件无关的云端大脑”，但在实际的高可用落地中，必须发生一次**架构视角的范式转移**。

我们将把架构从目前带有沉重通信代价的 **中心辐射型 (Star Topology to Cloud)**，转向当今智能穿戴领域最成熟的 **边缘枢纽型 (Hub-and-Spoke Edge Architecture)**。

---

## 🧐 1. 我们到底在做什么架构？ (Edge Hub Architecture)

如果将 `LOD 引擎`、`传感器聚合`、`Orchestrator 编排器` 全部下放到 iOS 客户端（只把重型计算如人脸识别、向量记忆库留给 Cloud Run），这种设计在业内被称为：**胖客户端 + 无状态微服务 (Fat Client / Smart Edge + Serverless Microservices)**。

更确切地说，从物联网和可穿戴设备的角度看，这就是 **边缘枢纽架构 (Edge Hub Architecture)**。

### 🍎 行业对标：为什么 Apple、Meta、Google 都在用这种架构？
1. **Apple AirPods & Apple Watch**：哪怕芯片再强，它们的第一长连接永远是 iPhone（通过蓝牙/局域网 Wi-Fi），iPhone 才是负责执行 Siri 重型网络请求、聚合健康数据 (HealthKit) 的真正“边缘枢纽 (Hub)”。
2. **Meta Ray-Ban 智能眼镜**：它只是一副装了摄像头的蓝牙耳机，它的所有“聪明”大脑（Meta AI 视觉识别请求、语音交互）全靠口袋里的手机作为一个“Edge Hub”来代理和转发。

在这套全新架构下，**用户的 iPhone 实际上变成了 SightLine 的“边缘个人服务器 (Edge Personal Server)”**。

---

## 🔗 2. 如果手机变成大脑，还能做到“硬件解耦”吗？

**答案是：不仅能做到硬件解耦，而且做到了更现实、更廉价的解耦！**

### ❌ 之前的“伪”解耦（集中式云大脑）：
如果所有的传感器数据（盲杖位置、ESP32摄像头、眼镜）都要直接发送到 Cloud Run，那么意味着**未来的每一个盲人辅助硬件，都必须自带一张 5G/LTE SIM 卡**，拥有处理 WebRTC/WebSocket 的高功耗网络芯片。
- 盲杖只有一根棍子，它的电池怎么支撑 5G 芯片和高频长连接？发热怎么办？网络盲区怎么办？

### ✅ 现在的“真”解耦（iPhone 作为万物枢纽）：
在下放逻辑后，硬件解耦的边界从“云端协议”收缩成了“**本地近场通讯协议 (Local BLE / Wi-Fi Protocol)**”。
未来的生态完全被打开了：
1. **廉价盲杖硬件**：只要内嵌一个几块钱的蓝牙串口芯片发送 IMU 数据，连上口袋里的 iPhone。
2. **ESP32 夹式摄像头**：只负责将 JPEG 图像通过本地 Wi-Fi 发给 iPhone。
3. **iPhone (Edge Hub)**：负责将分散在各处的硬件数据（Watch 的心率、盲杖的 IMU、摄像头的图像、自身的 GPS）在端侧进行极低延迟的聚合、LOD 计算。然后，由 iPhone 统一开启 **唯一一条** 直连 Google Gemini Live API 的 5G 安全长连接。

**这意味着，未来接驳进 SightLine 生态的硬件将无比便宜、省电，因为网络和算力代价全被转嫁给了性能溢出的 iPhone。**

---

## 🛠️ 3. 新老架构组件切割与职责对比

### 📱 Edge Hub 层 (iOS 客户端)
这是离用户最近、延迟要求最苛刻的阵地。
- **直连网关**：直接集成 `Firebase AI Logic iOS SDK`，负责与 Gemini 建立双向音视频流长连接，享受 0 代价的 App Check 安全防护。
- **本地感知引擎 (LOD Engine)**：接管原 Python 版的规则引擎。直接在本地每秒执行上百次的心率判定、运动状态解析，毫不拖泥带水，并实时生成包含当前规则的 System Prompt 给大模型。
- **轻量工具调用平台 (Client-side Function Calling)**：Gemini 抛出的 `navigate_to` 函数，本地 App 拦截后直接调用 iOS MapKit/CoreLocation 解决。

### ☁️ Cloud Services 层 (Cloud Run 云端微服务)
剥离了一切持久化的 WebSocket 和状态维护，成为专注于**重算力**与**长期知识图谱**的后端弹药库。
- **REST API - 人脸计算微服务**：暴露一个 `/api/face-id` 的普通 HTTP 接口，iOS 有需要时发照片来，它用 4 核 CPU 跑完 InsightFace (ONNX) 并立刻释放容器资源。不再白白浪费长连接待机时间。
- **REST API - 长时记忆微服务**：提供 `/api/memory` 接口，暴露强大的 Firestore 2048 维向量级联检索。

---

## ⚖️ 4. 灵魂拷问：如果不做这个“大手术”，会有什么影响？

如果我们保持现状（即保留 Cloud Run Proxy 和中心化的 `lod_engine.py`），项目依然可以跑，但**在真实产品化（Go-to-Market）和日常使用时，我们将面临四个无法逾越的“技术债务黑洞”**：

### 🚨 影响一：致命的 PANIC 延迟（安全隐患）
在现有架构下，当用户的心率突然飙升到 150 (PANIC 状态)：
1. Apple Watch 通过蓝牙发给 iPhone。
2. iPhone 上的 `TelemetryAggregator.swift` 拦截到，打上 `panic=true` 标签。
3. iPhone 把这个 JSON 序列化，通过移动网络发给 Cloud Run 的 WebSocket。
4. Cloud Run 排队解码，交给 Python `lod_engine.py` 计算出 LOD 1。
5. Cloud Run 再立刻把它序列化，打断 Gemini 目前的语音，重新下发提示词。
6. 最后 Gemini 发回安抚语音到手机。
**后果**：这条链路长达 6 步，且极度依赖网络稳定。如果碰巧用户在地铁里（也是最容易恐慌的场景）信号降级，大模型收到 PANIC 信号并做出反应可能需要 2-3 秒甚至更久。对于盲人来说，这 3 秒钟的“卡顿响应”是灾难性的。
**如果是端侧架构**：手机本地一秒内判定 PANIC，立刻调用本地 iOS 语音合成大喊“停下！”，甚至直接切断与云端的慢速连接，优先本地守护。

### 💸 影响二：极其昂贵的云端开销（由于长连接的心跳浪费）
当前的 Cloud Run 承载着 WebSocket 代理职责。
- 在 Serverless 架构中（Cloud Run / AWS Lambda），只要 WebSocket 连着，你就在**按秒付费计算实例时间**，即使盲人只是在静静地走路，一句话也没说。
- 哪怕是发送一个“我走到下个路口了”这么简单的遥测更新，由于通过中转节点，都会唤醒整个 Python 容器。
**后果**：当 SightLine 有了 1 万个在线用户，你们将为这 1 万个空闲但长连接的 WebSocket 支付巨额的账单。而把它降级为 REST API，只有真正需要人脸识别时才唤醒计费，成本呈指数级下降。

### 📉 影响三：逻辑重叠引发的“状态撕裂”
目前你们的 iOS 端（负责打包遥测）和 Cloud 端（负责解析和 LOD 决策）**同时都在做阈值判断**。
如果你看 `TelemetryAggregator.swift`，里面自己算了一遍心率突变。到了 `lod_engine.py`，再算一遍 LOD 规则。
**后果**：未来每一次修改“什么算危险状况”，你们都必须同时维护两份代码（Swift 和 Python），极容易出现 iOS 认为该发 Panic，而服务端 Python 认为还不算是 Panic 的“状态撕裂”，导致系统的鲁棒性大大降低。

### 🧩 影响四：被迫放弃原生 SDK 的强大生态
当你们在造一个代理中转层时，也意味着你们无法享受 Firebase 带来的一系列开箱即用套件的优势，例如基于 iOS Keychain 的安全证书管理、离线 Firestore 缓存、Crashlytics（因为崩溃全发生在 Cloud Run 黑盒里无法定位到具体哪一段用户操作）。

---

## 💡 最终结论：是否【必须】进行更改？

如果 SightLine 仅仅是停留在 Hackathon 参赛阶段（比赛结束就归档），**完全没有必要改**，因为现在的系统已经能向评委闭环展示理念了，改动不仅费时而且极大增加 Demo 瘫痪的风险。

但是，如果这是一个要在未来半年内 **发布到 App Store、真正交到视障用户手里、并作为一个创业项目去拿融资的生产级产品 (Production)**：
**【这个更改是不可避免且极其必要的】。必须进行切割。**它也是解决网络延迟、大规模并发成本和系统复杂度的唯一通路。
