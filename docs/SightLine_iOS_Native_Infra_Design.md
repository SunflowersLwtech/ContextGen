# SightLine iOS Native Infra 设计：通信架构与数据管线

> **Version**: 1.0
> **Date**: 2026-02-22
> **Status**: Active — 取代此前所有基于 PWA 的前端架构描述
> **前置文档**: `SightLine_Consolidated_Development_Reference.md`（后端 Agent 架构不变）
> **核心变更**: 前端从 React PWA (Vite) 切换为 **Swift Native iOS App + Apple Watch HealthKit 集成**

---

## 0. 架构变更总结

### 为什么从 PWA 切换到 Swift Native

| 致命缺陷 | PWA (iOS Safari) | Swift Native |
|---------|------------------|-------------|
| `navigator.vibrate()` | ❌ iOS 完全不支持 — 盲人无操作确认 | ✅ UIImpactFeedbackGenerator |
| Standalone PWA `getUserMedia` | ❌ iOS 上损坏 — 必须回退到 Safari 浏览器 | ✅ AVCaptureSession 原生稳定 |
| 后台音频持续运行 | ❌ iOS 随时杀掉 — Always-On 不可能 | ✅ Background Mode: Audio |
| 传感器数据（运动/步频/心率） | ❌ 全部需要 Developer Console 模拟 | ✅ **全部来自真实硬件** |
| Apple Watch 心率 | ❌ 完全不可能 | ✅ HealthKit 实时读取 |
| Demo 体验 | 浏览器标签页，评委看到"网页" | 全屏沉浸 App，评委看到"产品" |

### 什么没变

- ☁️ **后端架构完全不变**：Cloud Run + FastAPI + Google ADK + Gemini Live API
- 🤖 **Agent 编排不变**：Orchestrator + Vision/OCR/Navigation/Memory/FaceID Sub-Agents
- 🧠 **LOD Engine 不变**：三级 LOD + 规则引擎 + 发声阈值
- 💾 **Memory 系统**：自建 Firestore MemoryBankService（`memory/memory_bank.py`，340 行，支持 auto-extract/forget/budget）
- 🔌 **WebSocket 协议不变**：`wss://cloud-run-url/ws/{user_id}/{session_id}`

**唯一变更是"最后一公里"——前端从浏览器变成了原生 App。**

---

## 1. 整体架构

### 1.1 Hackathon 架构（Server-to-Server）

```
┌─────────────────────────────────────────────────────┐
│                    iOS Device                        │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │           SightLine iOS App (Swift)           │   │
│  │                                               │   │
│  │  ┌─────────┐  ┌────────────┐  ┌───────────┐  │   │
│  │  │ Camera  │  │   Audio    │  │  Sensor   │  │   │
│  │  │ Manager │  │  Pipeline  │  │  Manager  │  │   │
│  │  │         │  │ (capture + │  │ (Motion+  │  │   │
│  │  │ AVCapt. │  │  playback) │  │  GPS+HK)  │  │   │
│  │  └────┬────┘  └─────┬──────┘  └─────┬─────┘  │   │
│  │       │             │               │         │   │
│  │  ┌────▼─────────────▼───────────────▼─────┐   │   │
│  │  │         WebSocket Manager              │   │   │
│  │  │   (single connection, multiplexed)     │   │   │
│  │  └────────────────┬───────────────────────┘   │   │
│  │                   │                           │   │
│  │  ┌────────────────▼───────────────────────┐   │   │
│  │  │         Gesture + Haptic Layer         │   │   │
│  │  │  (UIGestureRecognizer + FeedbackGen)   │   │   │
│  │  └────────────────────────────────────────┘   │   │
│  │                                               │   │
│  │  UI: 全屏黑色 View + 底部状态文字              │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────┐                           │
│  │    Apple Watch       │  HealthKit 自动同步        │
│  │    (心率传感器)       │ ─────────────────────→    │
│  └──────────────────────┘       iPhone HealthKit     │
└──────────────────┬──────────────────────────────────┘
                   │ WSS (TLS 1.3)
                   │
    ┌──────────────▼──────────────────────────────┐
    │         Cloud Run (FastAPI + ADK)            │
    │                                              │
    │  ┌──────────────┐  ┌─────────────────────┐  │
    │  │  WebSocket   │  │   Context Parser    │  │
    │  │  Endpoint    │  │   (Telemetry JSON   │  │
    │  │              │──│    → LOD Engine)     │  │
    │  └──────┬───────┘  └─────────────────────┘  │
    │         │                                    │
    │  ┌──────▼───────────────────────────────┐   │
    │  │      ADK Runner (LiveRequestQueue)   │   │
    │  │                                      │   │
    │  │  Orchestrator Agent                  │   │
    │  │  ├── Vision Sub-Agent (Gemini 3.1)   │   │
    │  │  ├── OCR Sub-Agent (Gemini 3 Flash)  │   │
    │  │  ├── Navigation Sub-Agent            │   │
    │  │  ├── Memory Sub-Agent                │   │
    │  │  └── Face ID Sub-Agent (InsightFace) │   │
    │  └──────┬───────────────────────────────┘   │
    │         │                                    │
    │  ┌──────▼───────┐  ┌──────────────┐         │
    │  │ Gemini Live  │  │  Firestore   │         │
    │  │ API (WSS)    │  │  (Memory/    │         │
    │  │              │  │   Vectors)   │         │
    │  └──────────────┘  └──────────────┘         │
    └─────────────────────────────────────────────┘
```

### 1.2 与 PWA 方案的架构差异

| 组件 | PWA 方案 | Swift Native 方案 |
|------|---------|------------------|
| 前端 → 后端 | 浏览器 WebSocket API | `URLSessionWebSocketTask` |
| 音频采集 | Web Audio API AudioWorklet → PCM | `AVAudioEngine` installTap → PCM |
| 音频播放 | Web Audio API AudioContext → PCM | `AVAudioPlayerNode` → PCM |
| 视频采集 | `getUserMedia` + Canvas → JPEG | `AVCaptureSession` + `AVCaptureVideoDataOutput` → JPEG |
| 传感器 | DeviceMotion (有限) + navigator.geolocation | CMMotionActivityManager + CLLocationManager + HealthKit |
| 手势 | DOM Touch Events | UIGestureRecognizer |
| 触觉反馈 | ❌ 不可用 | UIImpactFeedbackGenerator / UINotificationFeedbackGenerator |
| 屏幕常亮 | Wake Lock API (部分支持) | `UIApplication.shared.isIdleTimerDisabled = true` |
| 后台运行 | ❌ 不可靠 | Background Mode: Audio (voip category) |

**后端 WebSocket 服务无需任何修改** — 它接收的仍然是 binary 音频帧、base64 JPEG、text telemetry JSON，不关心客户端是浏览器还是原生 App。

---

## 2. WebSocket 通信协议

### 2.1 连接

```
Endpoint: wss://{CLOUD_RUN_URL}/ws/{user_id}/{session_id}
Protocol: WebSocket over TLS 1.3
```

iOS 端使用 Apple **Network framework** 的 `NWConnection` + `NWProtocolWebSocket`（比 `URLSessionWebSocketTask` 更稳定，自动处理网络路径切换），不依赖任何第三方库：

```swift
import Network

let parameters = NWParameters.tls
let wsOptions = NWProtocolWebSocket.Options()
wsOptions.autoReplyPing = true
parameters.defaultProtocolStack.applicationProtocols.insert(wsOptions, at: 0)

let url = "wss://sightline-xxxxx.run.app/ws/\(userId)/\(sessionId)"
let connection = NWConnection(to: .url(URL(string: url)!), using: parameters)

connection.stateUpdateHandler = { state in
    switch state {
    case .ready:
        print("WebSocket connected")
    case .failed(let error):
        print("WebSocket failed: \(error)")
        // 触发重连
    default: break
    }
}

connection.start(queue: .global())
```

**为什么用 `NWConnection` 而非 `URLSessionWebSocketTask`**：
- `URLSessionWebSocketTask` 社区报告有崩溃和重连问题
- `NWConnection` 是 Apple Network framework 底层实现，更稳定
- 自动处理 WiFi ↔ 蜂窝网络切换（对户外行走的盲人用户至关重要）
- 原生支持 TLS 1.3，无第三方依赖

### 2.2 消息格式（复用现有协议，不改动后端）

**一条 WebSocket 连接承载三种数据类型**：

| 方向 | 类型 | WebSocket 消息类型 | 格式 | 频率 |
|------|------|-------------------|------|------|
| 📤 **iOS → Server** | 音频 | `.data(binary)` | PCM 16-bit LE, 16kHz, Mono | 连续流，每 100ms 一个 chunk |
| 📤 **iOS → Server** | 视频帧 | `.string(text)` | `{"type":"image","data":"<base64 JPEG>"}` | 1 FPS (LOD 1-2) / 0.3 FPS (LOD 3 静止) |
| 📤 **iOS → Server** | 遥测 | `.string(text)` | `{"type":"telemetry","data":{...}}` | 每 2-3 秒，或状态变化时立即 |
| 📥 **Server → iOS** | 音频 | `.data(binary)` | PCM 16-bit LE, 24kHz | 连续流（Gemini 响应） |
| 📥 **Server → iOS** | 控制 | `.string(text)` | `{"type":"lod_update","lod":2}` 等 | 事件驱动 |
| 📥 **Server → iOS** | 转写 | `.string(text)` | `{"type":"transcript","text":"...","role":"agent"}` | 每句话 |

### 2.3 消息调度优先级

```
iOS 端发送优先级（从高到低）：

1. PANIC 信号          → 立即发送，抢占一切
2. 手势操控信号         → 立即发送（lod_up/lod_down/mute/interrupt）
3. 音频流              → 连续发送，不间断
4. Telemetry 更新      → 每 2-3 秒批量发送
5. 视频帧              → 按 LOD 节流后发送
```

### 2.4 断线重连策略

```swift
// 指数退避重连
class WebSocketManager {
    private var reconnectDelay: TimeInterval = 1.0
    private let maxDelay: TimeInterval = 30.0
    
    func handleDisconnect() {
        // 触觉反馈通知用户断线
        HapticEngine.shared.play(.connectionLost)

        // P1: 断线 → 本地强制 LOD 1 降级
        // 无后端时只能依赖本地规则引擎，安全优先
        lodManager.forceLocalLOD(1, reason: "disconnected")

        // 用 TTS 本地合成一句简短提示（不依赖网络）
        LocalTTS.speak("网络断开，安全模式。")

        DispatchQueue.main.asyncAfter(deadline: .now() + reconnectDelay) {
            self.connect()
            self.reconnectDelay = min(self.reconnectDelay * 2, self.maxDelay)
        }
    }

    func handleConnect() {
        reconnectDelay = 1.0 // 重置
        HapticEngine.shared.play(.connectionRestored)

        // P1: 恢复连接 → 解除本地 LOD 锁定，恢复正常 LOD 决策
        lodManager.releaseLocalOverride()

        // Session Resumption: 发送上一个 session_id 尝试恢复（2 小时内有效）
        send(.string("{\"type\":\"session_resume\",\"session_id\":\"\(lastSessionId)\"}"))
    }
}

// P1: 本地 LOD 管理器（断线时独立运行）
class LocalLODManager {
    private var localOverride: Int? = nil
    @Published var currentLOD: Int = 2

    func forceLocalLOD(_ lod: Int, reason: String) {
        localOverride = lod
        currentLOD = lod
        print("[LOD] Local override: LOD \(lod) (\(reason))")
    }

    func releaseLocalOverride() {
        localOverride = nil
        print("[LOD] Local override released, resuming server LOD")
    }

    var isLocalOverrideActive: Bool { localOverride != nil }
}
```

---

## 3. 数据管线

### 3.1 音频输入管线（麦克风 → Gemini）

```
iPhone 麦克风
    │
    ▼
AVAudioEngine (inputNode)
    │ installTap(bufferSize: 1600, format: PCM 16kHz Mono)
    │
    ▼
Audio Format Converter
    │ AVAudioConverter → PCM 16-bit LE, 16kHz, Mono
    │
    ▼
Optional: 本地 RMS 计算
    │ → ambient_noise_db (注入 Telemetry)
    │
    ▼
WebSocket (.data binary)
    │ 每 100ms 一个 chunk (1600 samples = 3200 bytes)
    │
    ▼
Cloud Run FastAPI
    │ live_request_queue.send_realtime(audio_chunk)
    │
    ▼
Gemini Live API (AAD 自动语音检测)
```

**关键配置**：

```swift
// AVAudioSession 配置 — 关键！
let audioSession = AVAudioSession.sharedInstance()
try audioSession.setCategory(
    .playAndRecord,                          // 同时录音和播放
    mode: .voiceChat,                        // 语音通话优化
    options: [
        .defaultToSpeaker,                   // 无耳机时用扬声器
        .allowBluetooth,                     // 允许 AirPods
        .allowBluetoothA2DP,                 // 允许蓝牙耳机
        .mixWithOthers                       // 不打断其他音频
    ]
)
try audioSession.setPreferredSampleRate(16000)  // Gemini 要求 16kHz
try audioSession.setPreferredIOBufferDuration(0.01) // 10ms buffer → 低延迟
try audioSession.setActive(true)
```

**Background Mode 要求**（Info.plist）：

```xml
<key>UIBackgroundModes</key>
<array>
    <string>audio</string>
</array>
```

这使音频管线在 App 进入后台（锁屏/切换应用）后**持续运行**，实现 Always-On Companion。

### 3.2 音频输出管线（Gemini → 扬声器/AirPods）

```
Gemini Live API
    │ 流式返回 PCM 24kHz audio chunks
    │
    ▼
Cloud Run FastAPI
    │ WebSocket 转发
    │
    ▼
iOS WebSocket 接收 (.data binary)
    │
    ▼
Audio Buffer Queue
    │ 先缓冲 2-3 个 chunk（~60-90ms），避免卡顿
    │
    ▼
AVAudioPlayerNode (attached to AVAudioEngine)
    │ scheduleBuffer → 播放
    │ format: PCM 16-bit LE, 24kHz (Gemini 输出格式)
    │
    ▼
AVAudioSession 路由
    ├── AirPods (优先)
    ├── 骨传导耳机
    └── iPhone 扬声器 (fallback)
```

**Barge-in（用户打断 Agent）处理**：

```swift
// 当收到用户开始说话的信号时
func handleUserSpeechStart() {
    // 1. 立即停止音频播放
    audioPlayerNode.stop()
    
    // 2. 清空缓冲区
    audioBufferQueue.removeAll()
    
    // 3. 发送 activityStart 信号给服务器
    webSocket.send(.string("{\"type\":\"activity_start\"}"))
}
```

### 3.3 视频帧管线（摄像头 → Gemini）

```
iPhone 后置摄像头
    │
    ▼
AVCaptureSession
    │ AVCaptureVideoDataOutput
    │ captureOutput(_:didOutput:from:) delegate
    │
    ▼
帧选择器（Frame Selector）
    │ 1. LOD 节流：LOD 1-2 → 1 FPS / LOD 3 静止 → 0.3 FPS
    │ 2. 像素差异检测：与上一帧对比，重复场景跳过
    │ 3. 画面稳定性：运动模糊严重时跳过
    │
    ▼
JPEG 编码
    │ CIImage → resize to 768x768 → JPEG (quality: 0.7)
    │ ~50-100KB per frame
    │
    ▼
Base64 编码
    │ Data → base64String
    │
    ▼
WebSocket (.string text)
    │ {"type":"image","data":"<base64>"}
    │
    ▼
Cloud Run → live_request_queue.send_realtime(video_frame)
    │
    ▼
Gemini Live API (视觉理解)
```

**帧选择器算法**：

```swift
class FrameSelector {
    private var lastFrameTime: Date = .distantPast
    private var lastFrameBuffer: CVPixelBuffer?
    private var currentLOD: Int = 2
    
    // 根据 LOD 决定最小帧间隔
    var minInterval: TimeInterval {
        switch currentLOD {
        case 1: return 1.0       // 1 FPS
        case 2: return 1.0       // 1 FPS  
        case 3: return 2.0       // 0.5 FPS (静止时更低)
        default: return 1.0
        }
    }
    
    func shouldSendFrame(_ buffer: CVPixelBuffer) -> Bool {
        let now = Date()
        
        // 时间节流
        guard now.timeIntervalSince(lastFrameTime) >= minInterval else {
            return false
        }
        
        // 像素差异检测（跳过重复场景）
        if let last = lastFrameBuffer, pixelDifference(last, buffer) < 0.05 {
            return false // 场景变化 < 5%，跳过
        }
        
        lastFrameTime = now
        lastFrameBuffer = buffer
        return true
    }
}
```

### 3.4 传感器数据管线（iPhone + Apple Watch → Telemetry）

```
┌─────────────────────────────────────────────────────────────┐
│                    Sensor Manager                            │
│                                                              │
│  ┌──────────────────┐   ┌──────────────────┐                │
│  │ CMMotionActivity │   │   CMPedometer    │                │
│  │ Manager          │   │                  │                │
│  │ → motion_state   │   │ → step_cadence   │                │
│  │ (walking/running │   │ (steps per min)  │                │
│  │  /stationary/    │   │                  │                │
│  │  in_vehicle)     │   │                  │                │
│  └────────┬─────────┘   └────────┬─────────┘                │
│           │                      │                           │
│  ┌────────▼──────────────────────▼─────────┐                │
│  │          Fused Motion State              │                │
│  │  (综合运动类型 + 步频 → LOD 基线建议)      │                │
│  └────────┬────────────────────────────────┘                │
│           │                                                  │
│  ┌────────▼─────────┐   ┌──────────────────┐                │
│  │ CLLocationManager│   │ AVAudioEngine    │                │
│  │ → gps (lat/lng)  │   │ RMS Meter        │                │
│  │ → heading (方位)  │   │ → ambient_noise  │                │
│  │ → 空间转换检测     │   │   _db            │                │
│  └────────┬─────────┘   └────────┬─────────┘                │
│           │                      │                           │
│  ┌────────▼──────────────────────▼─────────┐                │
│  │              HealthKit                   │                │
│  │  HKAnchoredObjectQuery                  │                │
│  │  → heart_rate (from Apple Watch)         │                │
│  │  → PANIC 检测 (> 120 BPM)               │                │
│  └────────┬────────────────────────────────┘                │
│           │                                                  │
│  ┌────────▼────────────────────────────────┐                │
│  │        Telemetry Aggregator             │                │
│  │        (LOD-Aware 节流)                │                │
│  │                                         │                │
│  │  LOD 1: 3-4秒 / LOD 2: 2-3秒 /        │                │
│  │  LOD 3: 5-10秒，或状态变化时立即：       │                │
│  │  {                                      │                │
│  │    "type": "telemetry",                 │                │
│  │    "data": {                            │                │
│  │      "motion_state": "walking",         │  ← CMMotion    │
│  │      "step_cadence": 72,                │  ← CMPedometer │
│  │      "ambient_noise_db": 65,            │  ← AVAudio RMS │
│  │      "gps": {"lat":37.77,"lng":-122.4}, │  ← CLLocation  │
│  │      "heading": 225,                    │  ← CLLocation  │
│  │      "time_context": "afternoon",       │  ← Date        │
│  │      "heart_rate": 78,                  │  ← HealthKit   │
│  │      "user_gesture": null,              │  ← UIGesture   │
│  │      "panic": false                     │  ← 规则计算     │
│  │    }                                    │                │
│  │  }                                      │                │
│  └────────┬────────────────────────────────┘                │
│           │                                                  │
│           ▼                                                  │
│     WebSocket (.string text) → Cloud Run → Context Parser    │
└─────────────────────────────────────────────────────────────┘
```

### 3.5 Telemetry 状态变化时立即推送的条件

```swift
// 不等定时器，立即推送 Telemetry 的触发条件:
enum ImmediateTrigger {
    case motionStateChanged    // walking → stationary, stationary → running 等
    case spaceTransition       // GPS 连续位移后稳定 (室外→室内)
    case heartRateSpike        // heart_rate 变化 > 30% 或 > 120 BPM
    case noiseThresholdCrossed // ambient_noise 跨越 40dB/80dB 阈值
    case userGesture           // 任何用户手势操作
    case panicDetected         // PANIC 条件触发
}
```

### 3.6 Telemetry LOD-Aware 节流实现（P0）

```swift
class TelemetryAggregator {
    private var currentLOD: Int = 2
    private var lastSendTime: Date = .distantPast

    /// LOD-Aware 发送间隔（秒）
    var sendInterval: TimeInterval {
        switch currentLOD {
        case 1:  return 3.0   // 行走：3-4s，安全优先但避免淹没
        case 2:  return 2.0   // 探索：2-3s，频繁检测空间变化
        case 3:  return 5.0   // 静止：5-10s，状态稳定
        default: return 2.0
        }
    }

    func updateLOD(_ lod: Int) {
        currentLOD = lod
    }

    /// 定时发送检查（ImmediateTrigger 不受此限制）
    func shouldSendScheduled() -> Bool {
        return Date().timeIntervalSince(lastSendTime) >= sendInterval
    }

    func markSent() {
        lastSendTime = Date()
    }

    /// ImmediateTrigger 始终直接发送，不受节流限制
    func sendImmediate(trigger: ImmediateTrigger, data: TelemetryData) {
        webSocketManager.send(data.toJSON())
        markSent()
    }
}
```

---

## 4. Apple Watch 心率集成

### 4.1 数据流（双通道架构）

**主通道：watchOS App → WCSession → iPhone（实时，<1s 延迟）**

```
Apple Watch (watchOS App)
    │ HKWorkoutSession → 持续心率采集（1-5 秒/次）
    │
    ▼ WCSession.sendMessage (实时推送)
iPhone SightLine App
    │ WCSessionDelegate.didReceiveMessage
    │ 提取 BPM 值
    │
    ▼ (注入 Telemetry JSON)
WebSocket → Cloud Run → LOD Engine
```

**备份通道：HealthKit 系统同步（延迟 10-20 分钟）**

```
Apple Watch (系统自动测量)
    │ 静息 5-15 分钟/次
    │
    ▼ (Apple 系统自动同步到 iPhone，延迟 10-20 分钟)
iPhone HealthKit Store
    │
    ▼ (HKAnchoredObjectQuery 监听)
SightLine Sensor Manager
    │ 用于 Memory 系统长期趋势分析，不用于实时 PANIC 检测
```

**为什么需要双通道**：HealthKit 从 Apple Watch 到 iPhone 的同步延迟为 10-20 分钟甚至更长（Apple 官方确认无 API 可加速），完全不满足 PANIC 检测（>120 BPM 强制 LOD 1）的实时性要求。必须通过 watchOS App + WCSession 实现 <1s 传输。

### 4.2 实现代码

```swift
class HealthKitManager {
    private let healthStore = HKHealthStore()
    private var heartRateQuery: HKAnchoredObjectQuery?
    
    // 回调：新心率数据到达
    var onHeartRateUpdate: ((Double) -> Void)?
    
    func requestAuthorization() async throws {
        let heartRateType = HKQuantityType(.heartRate)
        
        // 只请求读权限（不写入）
        try await healthStore.requestAuthorization(
            toShare: [],
            read: [heartRateType]
        )
    }
    
    func startMonitoring() {
        let heartRateType = HKQuantityType(.heartRate)
        
        let query = HKAnchoredObjectQuery(
            type: heartRateType,
            predicate: nil,
            anchor: nil,
            limit: HKObjectQueryNoLimit
        ) { [weak self] query, samples, deletedObjects, anchor, error in
            self?.processHeartRateSamples(samples)
        }
        
        // 设置更新处理器 — 新数据到达时自动触发
        query.updateHandler = { [weak self] query, samples, deletedObjects, anchor, error in
            self?.processHeartRateSamples(samples)
        }
        
        healthStore.execute(query)
        heartRateQuery = query
    }
    
    private func processHeartRateSamples(_ samples: [HKSample]?) {
        guard let quantitySamples = samples as? [HKQuantitySample],
              let latest = quantitySamples.last else { return }
        
        let bpm = latest.quantity.doubleValue(
            for: HKUnit.count().unitDivided(by: .minute())
        )
        
        DispatchQueue.main.async {
            self.onHeartRateUpdate?(bpm)
        }
    }
    
    func stopMonitoring() {
        if let query = heartRateQuery {
            healthStore.stop(query)
        }
    }
}
```

### 4.3 Demo 技巧：提高心率采样频率

Apple Watch 在静息时采样频率较低（5-15 分钟/次）。要在 Demo 中获得实时体验：

**方法 1**：在 Apple Watch 上启动 **Workout**（体能训练 → 其他），心率将变为 **每 1-5 秒采样一次**。

**方法 2**：打开 Apple Watch 上的**心率 App**，保持常亮，同样会提高采样频率。

**Demo 脚本建议**：在录制 Demo 之前先启动 Workout，结束后停止。

### 4.4 watchOS Companion App（极简心率传输）

**需要一个简单的 watchOS App** 实现实时心率传输。仅 HealthKit 系统同步的延迟（10-20 分钟）完全无法满足 PANIC 检测需求。

**watchOS App 范围（约 500-680 行 Swift）**：

1. 启动/停止 HKWorkoutSession（触发高频心率采集）
2. 实时显示当前心率（让评委/用户看到）
3. 通过 WCSession.sendMessage 发送心率到 iPhone（<1s 延迟）

**watchOS 端核心代码**：

```swift
// WorkoutManager.swift — watchOS 端心率采集 + 传输
import HealthKit
import WatchConnectivity

class WorkoutManager: NSObject, ObservableObject, HKWorkoutSessionDelegate, HKLiveWorkoutBuilderDelegate {
    let healthStore = HKHealthStore()
    var session: HKWorkoutSession?
    var builder: HKLiveWorkoutBuilder?

    @Published var heartRate: Double = 0

    func startWorkout() {
        let config = HKWorkoutConfiguration()
        config.activityType = .other
        config.locationType = .outdoor

        do {
            session = try HKWorkoutSession(healthStore: healthStore, configuration: config)
            builder = session?.associatedWorkoutBuilder()

            session?.delegate = self
            builder?.delegate = self
            builder?.dataSource = HKLiveWorkoutDataSource(healthStore: healthStore, workoutConfiguration: config)

            session?.startActivity(with: Date())
            builder?.beginCollection(withStart: Date()) { _, _ in }
        } catch {
            print("Workout start failed: \(error)")
        }
    }

    func stopWorkout() {
        session?.end()
        builder?.endCollection(withEnd: Date()) { _, _ in }
    }

    // HKLiveWorkoutBuilderDelegate — 新数据到达
    func workoutBuilder(_ workoutBuilder: HKLiveWorkoutBuilder, didCollectDataOf collectedTypes: Set<HKSampleType>) {
        for type in collectedTypes {
            guard let quantityType = type as? HKQuantityType,
                  quantityType == HKQuantityType(.heartRate) else { continue }

            let statistics = workoutBuilder.statistics(for: quantityType)
            let bpm = statistics?.mostRecentQuantity()?.doubleValue(
                for: HKUnit.count().unitDivided(by: .minute())
            ) ?? 0

            DispatchQueue.main.async {
                self.heartRate = bpm
            }

            // 实时发送到 iPhone
            PhoneConnector.shared.sendHeartRate(bpm)
        }
    }

    func workoutSession(_ workoutSession: HKWorkoutSession, didChangeTo toState: HKWorkoutSessionState, from fromState: HKWorkoutSessionState, date: Date) {}
    func workoutSession(_ workoutSession: HKWorkoutSession, didFailWithError error: Error) {}
    func workoutBuilderDidCollectEvent(_ workoutBuilder: HKLiveWorkoutBuilder) {}
}
```

```swift
// PhoneConnector.swift — watchOS → iPhone 实时传输
import WatchConnectivity

class PhoneConnector: NSObject, WCSessionDelegate {
    static let shared = PhoneConnector()

    func activate() {
        if WCSession.isSupported() {
            WCSession.default.delegate = self
            WCSession.default.activate()
        }
    }

    func sendHeartRate(_ bpm: Double) {
        guard WCSession.default.isReachable else {
            // iPhone 不可达时，用 transferUserInfo 排队传输
            WCSession.default.transferUserInfo(["heartRate": bpm, "ts": Date().timeIntervalSince1970])
            return
        }
        WCSession.default.sendMessage(
            ["heartRate": bpm, "ts": Date().timeIntervalSince1970],
            replyHandler: nil,
            errorHandler: nil
        )
    }

    // WCSessionDelegate required
    func session(_ session: WCSession, activationDidCompleteWith activationState: WCSessionActivationState, error: Error?) {}
}
```

```swift
// iPhone 端接收 — 在 SensorManager 中
import WatchConnectivity

class WatchReceiver: NSObject, WCSessionDelegate {
    var onHeartRateUpdate: ((Double) -> Void)?

    func activate() {
        if WCSession.isSupported() {
            WCSession.default.delegate = self
            WCSession.default.activate()
        }
    }

    func session(_ session: WCSession, didReceiveMessage message: [String: Any]) {
        if let bpm = message["heartRate"] as? Double {
            DispatchQueue.main.async { self.onHeartRateUpdate?(bpm) }
        }
    }

    // WCSessionDelegate required
    func session(_ session: WCSession, activationDidCompleteWith activationState: WCSessionActivationState, error: Error?) {}
    func sessionDidBecomeInactive(_ session: WCSession) {}
    func sessionDidDeactivate(_ session: WCSession) { WCSession.default.activate() }
}
```

**watchOS 项目结构**：

```
SightLineWatch/
├── SightLineWatchApp.swift       # @main 入口
├── WorkoutManager.swift          # HKWorkoutSession + 心率采集
├── PhoneConnector.swift          # WCSession → iPhone 实时传输
├── ContentView.swift             # 主界面：心率数字 + 开始/停止按钮
├── Info.plist                    # HealthKit 权限
└── SightLineWatch.entitlements   # HealthKit entitlement
```

**开源参考**：Apple 官方 [SpeedySloth](https://developer.apple.com/documentation/healthkit/workouts_and_activity_rings/build_a_workout_app_for_apple_watch) 示例，裁剪到只保留心率部分。

**Demo 时**：在 Apple Watch 上启动 Workout，心率变为 1-5 秒/次采集，通过 WCSession 实时送达 iPhone → Telemetry → LOD Engine。

---

## 5. 手势与触觉反馈系统

### 5.1 手势识别层

整个屏幕是一个全屏不可见的触控区域。手势使用 UIKit 原生识别器，不需要任何第三方库：

```swift
class GestureHandler {
    func setupGestures(on view: UIView) {
        // 单击 → 静音/取消静音
        let singleTap = UITapGestureRecognizer(target: self, action: #selector(handleSingleTap))
        singleTap.numberOfTapsRequired = 1
        
        // 双击 → 强制打断 Agent
        let doubleTap = UITapGestureRecognizer(target: self, action: #selector(handleDoubleTap))
        doubleTap.numberOfTapsRequired = 2
        
        // 三击 → 重复上一句话
        let tripleTap = UITapGestureRecognizer(target: self, action: #selector(handleTripleTap))
        tripleTap.numberOfTapsRequired = 3
        
        // 上滑 → LOD 升级
        let swipeUp = UISwipeGestureRecognizer(target: self, action: #selector(handleSwipeUp))
        swipeUp.direction = .up
        
        // 下滑 → LOD 降级
        let swipeDown = UISwipeGestureRecognizer(target: self, action: #selector(handleSwipeDown))
        swipeDown.direction = .down
        
        // 长按 (3s) → 紧急暂停
        let longPress = UILongPressGestureRecognizer(target: self, action: #selector(handleLongPress))
        longPress.minimumPressDuration = 3.0
        
        // 解决冲突：单击等双击判定后再触发
        singleTap.require(toFail: doubleTap)
        doubleTap.require(toFail: tripleTap)
        
        [singleTap, doubleTap, tripleTap, swipeUp, swipeDown, longPress]
            .forEach { view.addGestureRecognizer($0) }
    }
}
```

### 5.2 摇晃检测（SOS）

```swift
// 在 ViewController 中
override func motionBegan(_ motion: UIEvent.EventSubtype, with event: UIEvent?) {
    if motion == .motionShake {
        // SOS 紧急模式
        HapticEngine.shared.play(.sosAlert)  // 连续震动
        telemetryManager.sendImmediate(panic: true)
    }
}
```

### 5.3 触觉反馈引擎

```swift
class HapticEngine {
    static let shared = HapticEngine()
    
    private let lightImpact = UIImpactFeedbackGenerator(style: .light)
    private let mediumImpact = UIImpactFeedbackGenerator(style: .medium)
    private let heavyImpact = UIImpactFeedbackGenerator(style: .heavy)
    private let notification = UINotificationFeedbackGenerator()
    
    enum Pattern {
        case singleTap          // 静音切换 — 轻震一次
        case doubleTap          // 打断 Agent — 中震两次
        case tripleTap          // 重复 — 轻震三次
        case lodUp              // LOD 升级 — 递增震感
        case lodDown            // LOD 降级 — 递减震感
        case emergencyPause     // 紧急暂停 — 重震一次
        case sosAlert           // SOS — 连续震动
        case connectionLost     // 断线 — 警告震感
        case connectionRestored // 恢复 — 成功震感
    }
    
    func play(_ pattern: Pattern) {
        switch pattern {
        case .singleTap:
            lightImpact.impactOccurred()
            
        case .doubleTap:
            mediumImpact.impactOccurred()
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                self.mediumImpact.impactOccurred()
            }
            
        case .tripleTap:
            for i in 0..<3 {
                DispatchQueue.main.asyncAfter(deadline: .now() + Double(i) * 0.1) {
                    self.lightImpact.impactOccurred()
                }
            }
            
        case .lodUp:
            notification.notificationOccurred(.success) // 上升感
            
        case .lodDown:
            notification.notificationOccurred(.warning) // 下降感
            
        case .emergencyPause:
            heavyImpact.impactOccurred()
            
        case .sosAlert:
            // 连续震动 5 次
            for i in 0..<5 {
                DispatchQueue.main.asyncAfter(deadline: .now() + Double(i) * 0.2) {
                    self.heavyImpact.impactOccurred()
                }
            }
            
        case .connectionLost:
            notification.notificationOccurred(.error)
            
        case .connectionRestored:
            notification.notificationOccurred(.success)
        }
    }
    
    func prepare() {
        // 预热反馈引擎，减少首次触发延迟
        lightImpact.prepare()
        mediumImpact.prepare()
        heavyImpact.prepare()
        notification.prepare()
    }
}
```

---

## 6. Swift 项目结构

```
SightLine/
├── SightLine.xcodeproj
├── SightLine/                              # iOS App Target
│   ├── App/
│   │   ├── SightLineApp.swift             # @main 入口
│   │   └── AppDelegate.swift              # 音频会话、后台模式配置
│   │
│   ├── Core/
│   │   ├── WebSocketManager.swift         # NWConnection WebSocket 连接、收发、重连
│   │   ├── MessageProtocol.swift          # 消息类型定义、JSON 编解码
│   │   └── Config.swift                   # 服务器 URL、配置常量
│   │
│   ├── Audio/
│   │   ├── AudioCaptureManager.swift      # AVAudioEngine 麦克风采集 → PCM
│   │   ├── AudioPlaybackManager.swift     # PCM 音频播放 (AVAudioPlayerNode)
│   │   └── AudioSessionManager.swift      # AVAudioSession 配置、蓝牙路由
│   │
│   ├── Camera/
│   │   ├── CameraManager.swift            # AVCaptureSession → JPEG 帧
│   │   └── FrameSelector.swift            # 帧选择器（LOD 节流 + 像素差异）
│   │
│   ├── Sensors/
│   │   ├── SensorManager.swift            # 统一传感器接口
│   │   ├── MotionManager.swift            # CMMotionActivityManager + CMPedometer
│   │   ├── LocationManager.swift          # CLLocationManager (GPS + heading)
│   │   ├── WatchReceiver.swift            # WCSession 接收 watchOS 实时心率
│   │   ├── HealthKitManager.swift         # HealthKit 备份通道（长期趋势）
│   │   ├── NoiseMeter.swift               # AVAudioEngine RMS 噪声计算
│   │   └── TelemetryAggregator.swift      # 汇总所有传感器 → Telemetry JSON
│   │
│   ├── Interaction/
│   │   ├── GestureHandler.swift           # 全屏手势识别
│   │   └── HapticEngine.swift             # 触觉反馈模式
│   │
│   ├── UI/
│   │   ├── MainView.swift                 # SwiftUI 全屏黑色界面
│   │   ├── StatusOverlay.swift            # 底部半透明状态文字
│   │   └── DebugOverlay.swift             # 开发阶段：实时数据面板（可关闭，内容见 §6.3）
│   │
│   ├── Resources/
│   │   ├── Info.plist                     # 权限声明、后台模式
│   │   └── SightLine.entitlements         # HealthKit entitlement
│   │
│   └── Supporting/
│       └── Assets.xcassets                # App 图标
│
├── SightLineWatch/                         # watchOS App Target (~500-680 行)
│   ├── SightLineWatchApp.swift            # @main 入口
│   ├── WorkoutManager.swift               # HKWorkoutSession + 心率采集
│   ├── PhoneConnector.swift               # WCSession → iPhone 实时传输
│   ├── ContentView.swift                  # 主界面：心率数字 + 开始/停止按钮
│   ├── Info.plist                         # HealthKit 权限
│   └── SightLineWatch.entitlements        # HealthKit entitlement
│
└── README.md
```

### 6.1 Info.plist 关键配置

```xml
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
    <!-- 权限声明 -->
    <key>NSCameraUsageDescription</key>
    <string>SightLine uses the camera to understand your surroundings and provide real-time audio descriptions.</string>
    
    <key>NSMicrophoneUsageDescription</key>
    <string>SightLine uses the microphone for voice interaction with your AI companion.</string>
    
    <key>NSMotionUsageDescription</key>
    <string>SightLine uses motion data to adapt its response style based on whether you are walking, running, or stationary.</string>
    
    <key>NSLocationWhenInUseUsageDescription</key>
    <string>SightLine uses your location to provide navigation assistance and detect space transitions.</string>
    
    <key>NSHealthShareUsageDescription</key>
    <string>SightLine reads your heart rate from Apple Watch to detect stress and provide appropriate support.</string>
    
    <!-- 后台模式 -->
    <key>UIBackgroundModes</key>
    <array>
        <string>audio</string>
    </array>
    
    <!-- 屏幕方向锁定为竖屏 -->
    <key>UISupportedInterfaceOrientations</key>
    <array>
        <string>UIInterfaceOrientationPortrait</string>
    </array>
</dict>
</plist>
```

### 6.2 Entitlements 文件

```xml
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
    <key>com.apple.developer.healthkit</key>
    <true/>
    <key>com.apple.developer.healthkit.access</key>
    <array/>
</dict>
</plist>
```

### 6.3 DebugOverlay 内容规格（P1）

> **用途**：开发+Demo 阶段的实时数据面板，三指双击切换显示/隐藏。生产环境默认关闭。

```
┌─────────────────────────────────────┐
│  🔧 Debug Overlay                   │
│─────────────────────────────────────│
│  LOD: 2 (标准)                      │
│  触发: Rule2:walking_slow→LOD2      │
│       + Rule4:space_transition→LOD2 │
│─────────────────────────────────────│
│  📡 Telemetry (interval: 2.0s)      │
│  motion: walking  cadence: 0.8/s    │
│  noise: 62dB  HR: 78 BPM           │
│  GPS: 37.77, -122.42               │
│─────────────────────────────────────│
│  ❤️ HR Sparkline (last 60s)         │
│  ▁▂▂▃▃▂▂▃▅▇▅▃▂▂▁                  │
│  min:72  avg:78  max:95             │
│─────────────────────────────────────│
│  🧠 Memory (top-3 active)           │
│  1. [location] 腾讯大厦B座="公司"    │
│  2. [person] face_abc=老板David      │
│  3. [routine] 8:30出发→地铁→公司     │
│─────────────────────────────────────│
│  🔌 WS: connected (latency: 45ms)   │
│  📷 Frame: 1.0 FPS (768x768)        │
└─────────────────────────────────────┘
```

**数据来源映射**：

| DebugOverlay 区块 | 数据来源 |
|------------------|---------|
| LOD 状态 + 触发原因 | `LODDecisionLog.to_debug_dict()` (后端 WebSocket `debug_lod` 消息) |
| Telemetry 实时值 | `TelemetryAggregator` 本地数据 |
| HR Sparkline | `WatchReceiver` 心率数据，本地保留 60 秒环形缓冲 |
| Memory top-3 | 后端 WebSocket `debug_memory` 消息（每次 LOD 决策时附带） |
| WS 状态 + 延迟 | `WebSocketManager` 连接状态 + ping-pong RTT |
| Frame FPS | `FrameSelector` 实际发送帧率统计 |

**切换方式**：

```swift
// 三指双击切换 DebugOverlay
let debugToggle = UITapGestureRecognizer(target: self, action: #selector(toggleDebug))
debugToggle.numberOfTapsRequired = 2
debugToggle.numberOfTouchesRequired = 3
view.addGestureRecognizer(debugToggle)
```

---

## 7. 延迟分析（Swift Native vs PWA）

| 环节 | PWA 延迟 | Swift Native 延迟 | 差异来源 |
|------|---------|-------------------|---------|
| 摄像头捕获 | ~16ms | **~8ms** | AVCaptureSession 更直接 |
| JPEG 编码 | ~5-15ms (Canvas) | **~3-8ms** (CIImage) | 硬件加速 |
| Base64 编码 | ~1-2ms | ~1-2ms | 差别不大 |
| 音频采集延迟 | ~20-50ms (AudioWorklet) | **~10ms** (AVAudioEngine) | 原生管线更短 |
| WebSocket 传输 | ~20-80ms | ~20-80ms | 网络无差别 |
| **Gemini 处理** | **500-6000ms** | **500-6000ms** | **主瓶颈，无差别** |
| 音频播放启动 | ~30-50ms (AudioContext) | **~10-20ms** (AVAudioPlayerNode) | 原生更快 |
| **总感知延迟** | **~600-6200ms** | **~550-6100ms** | 前端优化约~50-100ms |

**结论**：延迟的主瓶颈在 Gemini 处理（500ms-6s），前端的差异约 50-100ms，用户几乎感知不到。**Swift Native 的核心优势不在延迟，而在稳定性、后台运行、触觉反馈、真实传感器**。

---

## 8. 开发计划与依赖关系

### 8.1 模块之间的依赖

```
Config ──────────────────────────────────────────────────┐
    │                                                     │
    ▼                                                     │
WebSocketManager ◄─── 被所有管线依赖（核心通道）            │
    │                                                     │
    ├──► AudioCaptureManager ◄── AudioSessionManager      │
    │         (音频输入)                                    │
    │                                                     │
    ├──► AudioPlaybackManager ◄── AudioSessionManager     │
    │         (音频输出)                                    │
    │                                                     │
    ├──► CameraManager ◄── FrameSelector                  │
    │         (视频帧)                                     │
    │                                                     │
    ├──► TelemetryAggregator                              │
    │     ◄── MotionManager                               │
    │     ◄── LocationManager                             │
    │     ◄── HealthKitManager                            │
    │     ◄── NoiseMeter                                  │
    │     ◄── GestureHandler                              │
    │                                                     │
    └──► HapticEngine (独立，不依赖网络)                    │
                                                          │
MainView ◄── 所有 Manager 的状态（SwiftUI @Published）     │
```

### 8.2 推荐开发顺序

```
Phase 1: 核心通道 (Day 1-3)
  ├── Day 1: Config + NWConnection WebSocketManager + 基础消息协议
  ├── Day 2: AudioSessionManager + AudioCaptureManager
  └── Day 3: AudioPlaybackManager + 与 Cloud Run 联调

Phase 2: 视觉 + 传感器 (Day 4-6)
  ├── Day 4: CameraManager + FrameSelector + JPEG 编码
  ├── Day 5: SensorManager (Motion + GPS + NoiseMeter)
  └── Day 6: GestureHandler + HapticEngine + TelemetryAggregator

Phase 3: watchOS + 集成 (Day 7-9)
  ├── Day 7: watchOS App (WorkoutManager + PhoneConnector + ContentView)
  ├── Day 8: iPhone WatchReceiver + HealthKitManager(备份) + 联调
  └── Day 9: MainView UI + DebugOverlay + 端到端测试
```

**总计约 9 天完成 iOS + watchOS Thin Client。** 有 AI 辅助（Claude Code）可适当压缩。

---

## 9. 与 Consolidated Reference 的关系

本文档**替换**了 `SightLine_Consolidated_Development_Reference.md` 中以下章节的前端部分：

| 章节 | 原描述 | 本文档更新 |
|------|--------|----------|
| §1.1 Hackathon 硬件 | PWA = 唯一硬件 | **Swift Native iOS App = 唯一前端** |
| §4.3 底层网络 Infra | Phone PWA → WebSocket → Cloud Run | **iPhone App → WebSocket → Cloud Run**（协议不变） |
| §6 技术栈 | 前端: React PWA (Vite) | **前端: Swift (UIKit/SwiftUI) + AVFoundation + HealthKit** |

以下内容**不受影响**，继续以 Consolidated Reference 为准：

- §2 记忆系统
- §3 引擎核心（LOD Engine / Context Engine）
- §4.1-4.2 交互体验 + ADK Agent 编排
- §5 功能与集成
- §7 竞赛策略

---

## 10. 决策日志

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-02-22 | 前端从 PWA 切换为 Swift Native iOS | iOS PWA 三大致命缺陷（振动不可用、getUserMedia 不可靠、后台不可靠） |
| 2026-02-22 | 集成 Apple Watch HealthKit 心率 | 用户拥有 Apple Watch，可获得真实 PANIC 检测数据，消除 Developer Console 模拟需求 |
| 2026-02-22 | 开发极简 watchOS Companion App | HealthKit 系统同步延迟 10-20 分钟，无法满足实时 PANIC 检测。通过 WCSession.sendMessage 实现 <1s 心率传输，约 500-680 行代码 |
| 2026-02-22 | 使用免费 Apple ID 开发 | 免费 Apple ID 在本地真机调试时支持 HealthKit + Background Audio + CoreMotion + CoreLocation（Loop 开源项目数千用户验证）。限制：签名 7 天过期需重新构建，不能上架 App Store。Hackathon 场景完全足够 |
| 2026-02-22 | WebSocket 用 NWConnection 而非 URLSessionWebSocketTask | NWConnection (Network framework) 更稳定，自动处理 WiFi↔蜂窝网络切换，对户外行走场景至关重要 |
| 2026-02-22 | WebSocket 协议不变 | 后端无需任何修改，降低整体风险 |
