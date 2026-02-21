# WebRTC, PWA & Latency Optimization Research for SightLine

> **Research Date**: 2026-02-21
> **Source**: Parallel research agent - WebRTC PWA and latency optimization

---

## 1. WebRTC in React PWA

### Key Finding: No WebRTC Library Needed

Gemini Live API uses **WebSocket**, not WebRTC. SightLine only needs `getUserMedia()` for camera/mic capture, then sends frames over WebSocket.

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

## 2. Gemini Live API Connection from Browser

### Direct Browser-to-Gemini (RECOMMENDED)

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

## 3. Latency Optimization

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

## 4. PWA Capabilities

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

## 5. React PWA Framework: Vite (RECOMMENDED)

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

## 6. Latency Benchmarks

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

```
Phone (Vite + React PWA)
  |-- getUserMedia (native API)
  |-- AudioWorklet (16kHz PCM)
  |-- Canvas (768x768 JPEG)
  |-- WebSocket direct to Gemini
  |-- StreamingAudioPlayer (24kHz)
  |-- Wake Lock API
  |
  v
Cloud Run (token minter only)
  |-- POST /api/token -> ephemeral Gemini token
  |-- min_instance_count=1
  |
  v
Gemini Live API
  |-- gemini-2.5-flash-native-audio
  |-- VAD, compression, resumption
```

---

## Sources

- [Gemini Live API](https://ai.google.dev/gemini-api/docs/live)
- [Ephemeral Tokens](https://ai.google.dev/gemini-api/docs/ephemeral-tokens)
- [Live API Web Console](https://github.com/google-gemini/live-api-web-console)
- [Vite Plugin PWA](https://vite-pwa-org.netlify.app/guide/)
- [Cloud Run Optimization](https://cloud.google.com/blog/topics/developers-practitioners/3-ways-optimize-cloud-run-response-times)
- [PWA iOS Limitations](https://www.magicbell.com/blog/pwa-ios-limitations-safari-support-complete-guide)
- [Gemini Latency Discussion](https://discuss.ai.google.dev/t/live-api-5-6-second-response-latency/123254)
