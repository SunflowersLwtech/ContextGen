# WebRTC, PWA & Latency Optimization Research for SightLine

> **Research Date**: 2026-02-21
> **Source**: Parallel research agent - WebRTC PWA and latency optimization

---

## 1. Transport Protocol 确认调研 (2026-02-21 更新)

### 结论：Gemini Live API **只支持 WebSocket (WSS)**

| 协议 | 原生支持？ | 来源 |
|---|---|---|
| **WebSocket (WSS)** | **唯一支持** | 官方文档: "The Live API is a stateful API that uses WebSockets." |
| WebRTC | **不支持** | Google 开发者论坛官方回复: "We currently do not have the details for native WebRTC at the moment." |
| gRPC | **不支持** | 官方合作伙伴文档: "The SDKs only support HTTPS for the main API and WebSockets (WSS) for the Live API." |
| GemNet | **不存在** | 公开文档中无此协议 |

### WebSocket 端点

| 平台 | WebSocket 地址 |
|---|---|
| Google AI (ai.google.dev) | `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent` |
| Vertex AI (cloud.google.com) | `wss://{LOCATION}-aiplatform.googleapis.com/ws/google.cloud.aiplatform.v1.LlmBidiService/BidiGenerateContent` |

所有连接方式 (Python SDK `client.aio.live.connect()`、原生 WebSocket、ADK `run_live()`、Firebase AI Logic `model.connect()`) 底层都是 WebSocket。

### WebSocket vs WebRTC 性能对比

| 因素 | WebSocket (TCP) | WebRTC (UDP/DTLS/SRTP) |
|---|---|---|
| 传输层 | TCP (有序、可靠) | UDP (无序、容忍丢包) |
| 丢包处理 | 重传 + **队头阻塞** | 跳过丢失包，继续播放 |
| 弱网表现 | **严重退化** (延迟飙升至 10-15s) | 优雅降级 |
| 抖动缓冲 | 需自行实现 | 内建自适应 |
| 回声消除 | 需自行实现 | 内建 AEC |
| NAT 穿透 | 需代理/中继 | 内建 ICE/STUN/TURN |
| 音频编码 | 原始 PCM (无压缩) | Opus (高效压缩) |

**核心风险**：在移动 4G/弱 WiFi 下，TCP 队头阻塞导致延迟从 ms 级飙升至秒级。对户外行走的视障用户是实际问题。

### WebRTC 桥接方案 (Production 优化路径)

Google 官方推荐多个合作伙伴提供 WebRTC 桥接：

```
用户手机 ←─ WebRTC (UDP, 抗弱网) ─→ 桥接服务器 ←─ WebSocket (TCP, 骨干网) ─→ Gemini Live API
                                      (Pipecat + Daily)
```

| 桥接方案 | 类型 | 说明 |
|---|---|---|
| **Pipecat + Daily** | Google 官方推荐 | 开源框架 + 边缘网络，有现成 demo |
| **LiveKit** | 开源 | WebRTC 基础设施，社区活跃 |
| **Twilio** | 企业级 | 稳定但收费 |
| **Voximplant** | 企业级 | 俄罗斯团队 |
| **Fishjam** | 开源 | 新兴选择 |

Pipecat 官方声称: *"For a large percentage of users, voice-to-voice response times will be measurably faster than using direct WebSocket connection."*

原理：手机到桥接服务器走 WebRTC (UDP) 处理不稳定的"最后一公里"；桥接服务器到 Gemini 走骨干网 WebSocket，TCP 缺点被高质量网络掩盖。

**参考仓库**: [pipecat-ai/gemini-webrtc-web-simple](https://github.com/pipecat-ai/gemini-webrtc-web-simple)

### SightLine 分阶段策略

```
Hackathon:  Phone PWA ──WebSocket (直连)──→ Gemini Live API
            ✅ 零复杂度 | ✅ 受控 WiFi 下 320-800ms | ✅ 评委看 Gemini 深度利用

Production: Phone PWA ──WebRTC──→ Pipecat/Daily Edge ──WebSocket──→ Gemini Live API
            ✅ 抗弱网 | ✅ 更低感知延迟 | ✅ 内建回声消除/抖动缓冲
```

---

## 2. Media Capture in React PWA

### getUserMedia (Hackathon 唯一需要)

SightLine 只需 `getUserMedia()` 捕获摄像头/麦克风，然后通过 WebSocket 发送帧数据。不需要任何 WebRTC P2P 库。

| Library | Verdict for SightLine |
|---|---|
| Native `getUserMedia` | **Best choice** -- only need media capture |
| PeerJS | Not recommended (P2P focus) |
| simple-peer | Not recommended (unmaintained) |
| mediasoup-client | Overkill |

### Camera + Mic Capture

```typescript
const stream = await navigator.mediaDevices.getUserMedia({
    video: {
        facingMode: 'environment',  // rear camera
        width: { ideal: 768 },
        height: { ideal: 768 },
        frameRate: { ideal: 5, max: 10 }
    },
    audio: {
        sampleRate: 16000,     // Gemini expects 16kHz
        channelCount: 1,       // mono
        echoCancellation: true,
        noiseSuppression: true,
    }
});
```

---

## 3. Gemini Live API Connection from Browser

### Direct Browser-to-Gemini (RECOMMENDED for Hackathon)

```
Phone Browser --[WebSocket]--> Gemini Live API
       ^
       | (ephemeral token)
Backend Server (lightweight)
```

- Lowest latency -- no proxy hop
- Backend only mints ephemeral tokens
- Token lifetime: 1 min to start, 30 min for active connection

### Sending Audio + Video

```typescript
// Video: JPEG base64 at 1 FPS
session.sendRealtimeInput({
    mediaChunks: [{ mimeType: 'image/jpeg', data: base64Jpeg }]
});

// Audio: PCM 16kHz continuous
session.sendRealtimeInput({
    mediaChunks: [{ mimeType: 'audio/pcm;rate=16000', data: pcmBase64 }]
});
```

### Format Requirements

| Modality | Format | Details |
|---|---|---|
| Audio Input | PCM 16-bit LE | 16 kHz, mono |
| Audio Output | PCM 16-bit LE | 24 kHz |
| Video Input | JPEG base64 | 768x768, 1 FPS |
| Token cost (audio) | 25 tokens/sec | |
| Token cost (video) | 258 tokens/frame | |

---

## 4. Latency Optimization

### End-to-End Breakdown

```
Camera Capture      ~16ms
JPEG Encoding       ~5-15ms
Base64 Encoding     ~1-2ms
WebSocket Transmit  ~20-80ms
Gemini Processing   ~500ms-6000ms  (dominant factor)
TTS Generation      streamed
Audio Playback      ~10-50ms
Total perceived:    ~600ms - 6500ms
```

### Strategies

1. **Streaming Audio Playback**: Play chunks as they arrive
2. **Pre-emptive Feedback**: "Let me look..." while processing
3. **Frame Selection**: Skip duplicate scenes via pixel diff
4. **Context Compression**: Enable for unlimited sessions
5. **Cloud Run Warm**: min_instance_count=1, startup CPU boost

---

## 5. PWA Capabilities

### Background Camera: NOT SUPPORTED
- Camera/mic suspend when PWA minimized
- Use Wake Lock API to keep screen on

### iOS Gotcha
- `getUserMedia` **broken in iOS standalone PWA mode**
- Workaround: open in Safari (not standalone) or use Capacitor

### Platform Comparison

| Feature | Android Chrome | iOS Safari |
|---|---|---|
| getUserMedia in PWA | Full support | **Broken in standalone** |
| Wake Lock | Supported | Supported (iOS 16.4+) |
| Background camera | No | No |
| Bluetooth audio | Transparent | Transparent |

---

## 6. React PWA Framework: Vite (RECOMMENDED)

| Factor | Vite | Next.js | CRA |
|---|---|---|---|
| Dev cold start | <2s | 3-5s | 10-30s |
| HMR | ms | seconds | seconds |
| PWA plugin | `vite-plugin-pwa` | Manual | Deprecated |
| SSR needed? | No (SPA) | Overkill | N/A |

```typescript
// vite.config.ts
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
    plugins: [react(), VitePWA({
        registerType: 'autoUpdate',
        manifest: {
            name: 'SightLine',
            display: 'standalone',
        },
        workbox: {
            globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        }
    })]
});
```

Service workers CANNOT intercept WebSocket -- only cache static assets.

---

## 7. Latency Benchmarks

### Cloud Run

| Metric | Value |
|---|---|
| Cold start (with boost) | ~1s |
| Cold start (without) | ~3s |
| Warm request | <10ms |
| WebSocket timeout | 5min default, 60min max |

### Gemini API

| Task | Latency |
|---|---|
| Live API first chunk (audio only) | 500ms-2s |
| Live API first chunk (audio+video) | 1-4s |
| Latency spikes | 5-15s |

### Session Limits

| Config | Audio Only | Audio + Video |
|---|---|---|
| Without compression | 15 min | **2 min** |
| With compression | Unlimited | Unlimited |

---

## Recommended Architecture

### Hackathon (直连 WebSocket)

```
Phone (Vite + React PWA)
  |-- getUserMedia (native API)
  |-- AudioWorklet (16kHz PCM)
  |-- Canvas (768x768 JPEG)
  |-- WebSocket direct to Gemini  ← 唯一支持的传输协议
  |-- StreamingAudioPlayer (24kHz)
  |-- Wake Lock API
  |
  v
Cloud Run (token minter + sub-agent host)
  |-- POST /api/token -> ephemeral Gemini token
  |-- Sub-agents: Gemini 3 Flash (FREE) / 3.1 Pro (vision)
  |-- min_instance_count=1
  |
  v
Gemini Live API (WSS)
  |-- gemini-2.5-flash-native-audio-preview-12-2025 (Live API: 2.5 only)
  |-- VAD, compression, resumption
```

### Production (WebRTC 桥接 — 抗弱网优化)

```
Phone (Vite + React PWA)
  |-- getUserMedia (native API)
  |-- Pipecat Client SDK (WebRTC transport)  ← UDP, 抗丢包
  |-- 内建: 回声消除(AEC), 抖动缓冲, Opus 编码
  |
  v  WebRTC (UDP/DTLS/SRTP)
  |
Pipecat + Daily Edge Server (全球边缘节点)
  |-- WebRTC ↔ WebSocket 协议转换
  |-- 骨干网连接 Gemini (TCP 缺点被掩盖)
  |
  v  WebSocket (WSS, 骨干网)
  |
Cloud Run (sub-agent host)
  |-- Sub-agents: Gemini 3 Flash / 3.1 Pro
  |
  v
Gemini Live API (WSS)
  |-- gemini-2.5-flash-native-audio-preview-12-2025
  |-- VAD, compression, resumption
```

**Production 优势**: 手机到边缘服务器走 WebRTC (UDP)，天然抗弱网；边缘到 Gemini 走骨干网 WebSocket，TCP 队头阻塞可忽略。Pipecat 声称对大多数用户 voice-to-voice 延迟显著低于直连 WebSocket。

---

## Sources

### Gemini Live API
- [Gemini Live API Overview](https://ai.google.dev/gemini-api/docs/live)
- [Live API WebSocket Reference](https://ai.google.dev/api/live)
- [Ephemeral Tokens](https://ai.google.dev/gemini-api/docs/ephemeral-tokens)
- [Live API Web Console](https://github.com/google-gemini/live-api-web-console)
- [Partner Integrations](https://ai.google.dev/gemini-api/docs/partner-integration)
- [Gemini Latency Discussion](https://discuss.ai.google.dev/t/live-api-5-6-second-response-latency/123254)

### Transport Protocol 确认
- [Google AI Forum — WebRTC Support Question](https://discuss.ai.google.dev/t/is-there-any-near-future-plans-to-have-native-webrtc-support-in-the-gemini-2-0-flash-live-multimodal-api-servers/57746)
- [Google AI Forum — gRPC Question](https://discuss.ai.google.dev/t/how-to-use-grpc-to-call-gemini-apis-configuration-authentication-help-needed/69463)
- [Google AI Forum — WebSocket Latency Issues](https://discuss.ai.google.dev/t/significant-delay-with-gemini-live-2-5-flash-native-audio/122650)
- [Vertex AI Live API (confirms WSS)](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api)

### WebRTC 桥接方案
- [Pipecat + Gemini WebRTC Demo](https://github.com/pipecat-ai/gemini-webrtc-web-simple)
- [Pipecat Gemini Live Guide](https://docs.pipecat.ai/guides/features/gemini-live)
- [Daily + Gemini Multimodal Live](https://www.daily.co/products/gemini/multimodal-live-api/)
- [LiveKit](https://livekit.io/)

### PWA & Frontend
- [Vite Plugin PWA](https://vite-pwa-org.netlify.app/guide/)
- [Cloud Run Optimization](https://cloud.google.com/blog/topics/developers-practitioners/3-ways-optimize-cloud-run-response-times)
- [PWA iOS Limitations](https://www.magicbell.com/blog/pwa-ios-limitations-safari-support-complete-guide)
