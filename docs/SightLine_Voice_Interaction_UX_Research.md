# SightLine: Voice Interaction UX Research — 语音交互体验深度研究

> **Version**: 1.0
> **Date**: 2026-02-21
> **Purpose**: 解决 SightLine 三大交互体验难题：VAD 唤起/结束、手机端交互妥协、嘈杂环境识别
> **Methodology**: Gemini Live API 官方文档 + Google DeepMind 研究 + 开源框架调研 + 闭源产品思想借鉴
>
> ⚠️ **前端迁移说明 (2026-02-22)**：前端已从 React PWA 迁移到 **Swift Native iOS App**（详见 `SightLine_iOS_Native_Infra_Design.md`）。本文档中涉及 PWA 的实现细节（`navigator.vibrate()`、HTML/ARIA 标签、`AudioWorklet` 等）仅作为交互设计参考，实际实现已切换为 iOS 原生 API（`UIImpactFeedbackGenerator`、`UIGestureRecognizer`、`AVAudioEngine` 等）。VAD 策略、Proactive Audio 设计、嘈杂环境防御架构等**后端/AI 层设计不受影响**。

---

## 0. 设计哲学：对盲人用户来说，最好的交互就是"没有交互"

> **核心原则：系统应该足够智能，让用户几乎不需要主动控制它。当必须控制时，应该是物理直觉式的（触摸/按压），而不是视觉引导式的。**

传统语音助手的交互范式是 **"唤醒词 → 命令 → 等待响应"**，这对盲人用户是灾难性的：

| 问题 | 为什么对盲人用户是灾难 |
|------|----------------------|
| 唤醒词 | 盲人在嘈杂户外需要时刻保持听觉警觉，大声说唤醒词会暴露自身，也影响注意力 |
| 等待响应 | 无法看到"正在处理"的视觉指示器，不确定系统是否收到了请求 |
| 打断 | 传统系统被打断后从头开始，盲人用户需要依赖连续叙事理解环境 |
| 静默 | 无法区分"系统在思考"和"系统崩溃了"——对视力正常用户，看一眼屏幕就知道 |

SightLine 的解决方案：**Always-On Companion Model（永远在线的伴侣模型）**

```
传统模式:  用户 ──唤醒──→ 系统 ──命令──→ 响应 ──结束──→ 静默
SightLine:  系统 ═══════ 持续感知 ═══════ 适时说话 ═══════ 知趣闭嘴
                         ↕ 用户随时可打断/提问/控制 ↕
```

这直接映射到 Gemini Live API 的 **Proactive Audio** 能力 — AI 决定何时说话，而不是用户主动请求。

---

## 1. VAD 唤起与结束 — 核心交互机制设计

### 1.1 Gemini Live API 的内建 VAD 能力

Gemini Live API 将 VAD 整合为 **Automatic Activity Detection (AAD)**，提供以下可配置参数：

```python
realtime_input_config = types.RealtimeInputConfig(
    automatic_activity_detection=types.AutomaticActivityDetection(
        disabled=False,                                           # 启用自动 VAD
        start_of_speech_sensitivity="MEDIUM",                     # 语音开始灵敏度
        end_of_speech_sensitivity="MEDIUM",                       # 语音结束灵敏度
        prefix_padding_ms=200,                                    # 语音起始前的缓冲
        silence_duration_ms=1000,                                 # 静默多久判定用户说完
    )
)
```

#### 关键参数详解

| 参数 | 作用 | 对盲人用户的影响 |
|------|------|----------------|
| `start_of_speech_sensitivity` | LOW/MEDIUM/HIGH — 多敏感地检测用户开始说话 | HIGH = 任何轻声都会触发识别（嘈杂时误触发）；LOW = 需要声音较大才触发 |
| `end_of_speech_sensitivity` | LOW/MEDIUM/HIGH — 多快判定用户已说完 | LOW = 给用户更多时间组织语言（适合复杂提问）；HIGH = 快速判定结束（适合简短指令） |
| `prefix_padding_ms` | 检测到语音起始前，保留多少毫秒的音频 | 防止吞掉第一个字的开头音节 |
| `silence_duration_ms` | 静默多久后判定用户说完 | 太短 = 用户停顿思考时被误判为说完；太长 = 响应延迟 |

#### Barge-in（用户打断系统）机制

```python
# activity_handling 控制用户说话时是否打断系统
# START_OF_ACTIVITY_INTERRUPTS = 用户说话立即打断系统（默认，推荐）
# NO_INTERRUPTION = 系统说话不可被打断（仅用于紧急安全警报）
```

**关键发现**：Gemini 的 barge-in 是 **语义级别的**，不仅仅是 VAD 级别。Gemini Native Audio 模型直接处理原始音频波形，它能区分：
- 用户真的想打断 → 立即停止并响应
- 背景噪音 → 继续说话
- 用户的"嗯"、"对" → 这是反馈信号，不是打断

这正是 Google Cloud 博客所说的：*"Proactive Audio moves beyond simple Voice Activity Detection. The agent can intelligently decide when to respond and when to remain a silent co-listener."*

### 1.2 LOD-Adaptive VAD 调参策略

**核心洞察：VAD 参数不应该是固定的，应该随 LOD 动态调整。**

| LOD | start_of_speech_sensitivity | end_of_speech_sensitivity | silence_duration_ms | 理由 |
|-----|----------------------------|--------------------------|--------------------|----|
| **LOD 1**（行走/危险） | **HIGH** | **HIGH** | **300-500ms** | 用户在移动中，可能只说一两个字（"停"、"什么？"），需要极速响应 |
| **LOD 2**（探索） | MEDIUM | MEDIUM | **700-1000ms** | 用户在探索环境，可能有中等长度的提问 |
| **LOD 3**（静坐/阅读） | MEDIUM | **LOW** | **1200-1500ms** | 用户可能组织复杂问题，需要更多停顿时间 |

**实现方式**：Gemini Live API 支持在会话中途更新配置（通过发送新的 setup message），因此可以在 LOD 切换时同步调整 VAD 参数：

```python
# 当 LOD Engine 决定切换 LOD 时，同步更新 VAD 配置
async def update_vad_for_lod(live_session, new_lod: int):
    vad_configs = {
        1: {"start_sensitivity": "HIGH", "end_sensitivity": "HIGH", "silence_ms": 400},
        2: {"start_sensitivity": "MEDIUM", "end_sensitivity": "MEDIUM", "silence_ms": 800},
        3: {"start_sensitivity": "MEDIUM", "end_sensitivity": "LOW", "silence_ms": 1300},
    }
    config = vad_configs[new_lod]
    # 通过 session update 动态调整
    await live_session.send({
        "setup": {
            "realtimeInputConfig": {
                "automaticActivityDetection": {
                    "startOfSpeechSensitivity": config["start_sensitivity"],
                    "endOfSpeechSensitivity": config["end_sensitivity"],
                    "silenceDurationMs": config["silence_ms"],
                }
            }
        }
    })
```

### 1.3 "什么时候该说话" — Proactive Audio 的精细化控制

Gemini 的 Proactive Audio 已经解决了"系统何时主动说话"的基础问题，但需要通过 System Prompt 精细化控制：

```
# System Prompt 中的 Proactive Audio 指导
You are a proactive but respectful companion for a blind user.

WHEN TO SPEAK PROACTIVELY:
- New significant object/person enters the scene → speak
- Scene changes dramatically (entering a new space) → speak
- Safety-relevant information detected → speak IMMEDIATELY
- User appears to be searching for something (head scanning motion) → offer help

WHEN TO STAY SILENT:
- Scene is stable and unchanged → stay silent
- User is in active conversation with another person → stay absolutely silent
- User is walking and no new information → stay silent
- Ambient noise level is very high → only speak for CRITICAL safety info

WHEN THE USER INTERRUPTS YOU:
- IMMEDIATELY stop speaking
- Acknowledge the interruption naturally ("Yes?", "Go ahead")
- Save your current narrative position to resume later
- Process the user's new request with highest priority
```

### 1.4 手动 VAD 模式 — 备选方案

如果 Gemini 的自动 AAD 在某些场景表现不佳，可以切换到手动模式：

```python
# 禁用自动 VAD，由客户端发送 activityStart/activityEnd 信号
config = {
    "realtimeInputConfig": {
        "automaticActivityDetection": {"disabled": True}
    }
}

# 客户端逻辑：
# 用户按下按钮 → send activityStart → 开始收集音频
# 用户松开按钮 → send activityEnd → 系统开始处理
```

**但不推荐作为主要交互方式**——对盲人用户来说，"按住说话"增加了认知和物理负担。仅作为嘈杂环境的降级方案。

### 1.5 当前方案的已知局限

| 局限 | 详情 | 缓解策略 |
|------|------|----------|
| 无 `speech_started`/`speech_stopped` 事件 | 客户端无法知道 Gemini 何时检测到用户开始/停止说话 (GitHub #1285) | 前端用本地 Web Audio API 的音量级别做近似 UI 指示 |
| 手动 endpointing 不支持 | 不能混合使用自动 VAD + 手动 endpoint | Hackathon 中用纯自动 VAD；生产环境考虑 Pipecat |
| 语义 VAD 不透明 | Gemini 的"语义级"turn-taking 不暴露置信度 | 信任 Gemini 的内建判断，通过 prompt tuning 调优 |

---

## 2. 手机端交互妥协方案

### 2.1 设计原则：一只手，零视觉

盲人用户可能一只手持白手杖，另一只手持手机。交互必须满足：
- ✅ 单手可完成所有操作
- ✅ 不需要精确定位屏幕上的元素
- ✅ 触觉/震动反馈确认操作
- ✅ 与 iOS VoiceOver / Android TalkBack 兼容

### 2.2 手势映射方案（全屏触控区）

整个屏幕是一个巨大的触控区域，无需精确瞄准：

| 手势 | 动作 | Gemini API 实现 | 触觉反馈 |
|------|------|----------------|---------|
| **单击** (anywhere) | 静音/取消静音麦克风 | 静音 = 暂停发送音频 + `activityEnd`；取消静音 = 恢复发送音频 | 短震一次 |
| **双击** (anywhere) | 强制中断 Agent 说话 | 发送 `activityStart` 触发 barge-in，然后立即 `activityEnd` | 短震两次 |
| **三击** (anywhere) | 重复上一句 Agent 说的话 | 通过 WebSocket 发送文本："请重复你刚才说的最后一句话" | 短震三次 |
| **长按 (3s)** | 紧急暂停 — 全系统静音 | 暂停所有音频输入输出；进入 LOD 0（完全静默模式） | 长震一次 |
| **上滑** | LOD 升级（说更多） | 注入 Telemetry: `{"user_gesture": "lod_up"}` | 上升音效 |
| **下滑** | LOD 降级（说更少） | 注入 Telemetry: `{"user_gesture": "lod_down"}` | 下降音效 |
| **摇晃手机** | SOS — 紧急求助模式 | 注入 Telemetry: `{"panic": true}` → 强制 LOD 1 + 安全响应 | 连续震动 |

### 2.3 物理按钮映射

利用手机已有的物理按钮（不需要任何额外硬件）：

| 物理按钮 | 动作 | 实现方式 |
|----------|------|---------|
| **音量上键** | LOD 升级 | JavaScript `volumeupbutton` 事件 (Android) / Media Session API |
| **音量下键** | LOD 降级 | JavaScript `volumedownbutton` 事件 (Android) / Media Session API |
| **电源键短按** | 锁屏但保持对话 | Wake Lock API 防止息屏；或在锁屏状态下继续音频处理 |

> **⚠️ iOS 限制**: iOS PWA 无法拦截音量键。需要通过 `MediaSession` API 的间接方式，或引导用户使用 AirPods 的物理按钮。

### 2.4 AirPods / 蓝牙耳机交互

对于使用 AirPods 或其他蓝牙耳机的用户，可以利用耳机的物理控制：

| AirPods 手势 | 映射到 SightLine | 技术实现 |
|-------------|-----------------|---------|
| **捏一下** (AirPods Pro) | 暂停/恢复 Agent 说话 | MediaSession `play/pause` API |
| **长按** | 说话（Push-to-talk 模式） | MediaSession API |
| **"Hey Siri"** | *不使用* — 与系统冲突 | N/A |

### 2.5 VoiceOver / TalkBack 兼容策略

```html
<!-- 主按钮的无障碍属性 -->
<button
  id="main-action"
  role="button"
  aria-label="Tap to mute, double tap to interrupt, swipe up for more detail"
  aria-live="polite"
  style="width: 100vw; height: 100vh; position: fixed; top: 0; left: 0;"
>
  <!-- 全屏不可见按钮，实际上是整个屏幕的触控区 -->
</button>

<!-- LOD 状态变化的无障碍播报 -->
<div aria-live="assertive" id="lod-status">
  <!-- 动态更新: "Detail level changed to conversational mode" -->
</div>
```

**关键设计决策**: SightLine 在 Demo 中应该**关闭 VoiceOver/TalkBack**，因为它们会与 SightLine 自身的语音输出冲突。SightLine 本身就是取代屏幕阅读器的——它是"环境阅读器"。

但需要在代码中预留兼容性：
- 所有 UI 元素有正确的 ARIA 标签
- 状态变化通过 `aria-live` 区域播报
- 支持"双重输出"模式（SightLine 语音 + VoiceOver 同时工作）——用于初次使用者的过渡

### 2.6 简化的 Frontend 交互流程图

```
App 启动
  │
  ├── 自动连接 WebSocket → Gemini Live API
  ├── 自动开启麦克风 (getUserMedia)
  ├── 自动开启摄像头 (getUserMedia)
  ├── 防息屏 (Wake Lock API)
  │
  ▼
正常运行 (Always-On Companion)
  │
  ├── Gemini 的 Proactive Audio 自动决定何时说话
  ├── 用户随时可以说话 → Gemini AAD 自动检测
  ├── 背景持续分析摄像头画面 (1 FPS)
  │
  ├── [用户单击屏幕] → 切换静音 → 短震反馈
  ├── [用户双击屏幕] → 打断 Agent → 双震反馈
  ├── [用户上滑] → LOD++ → 音效反馈
  ├── [用户下滑] → LOD-- → 音效反馈
  ├── [用户长按] → 紧急暂停 → 长震反馈
  └── [用户摇晃] → SOS 模式 → 连续震动
```

---

## 3. 嘈杂环境下的语音识别 — 四层防御架构

### 3.1 问题分析

室外嘈杂环境是 SightLine 面临的最严峻挑战：

| 噪声来源 | 严重性 | 对 VAD 的影响 |
|---------|--------|-------------|
| 交通噪声（汽车、公交） | 高 | 持续噪声可能被 VAD 过滤，影响不大 |
| **他人说话** | **极高** | VAD 无法区分用户说话和旁人说话 → 误触发 → Agent 被打断 |
| 风声 | 中 | 直接吹入麦克风，完全淹没用户语音 |
| 建筑工地 | 高 | 突发冲击噪声可能触发 VAD |
| 用户自身声音被路人听到 | 隐私风险 | 非技术问题，但影响用户使用意愿 |

**最关键的问题：他人说话。** 传统降噪（如手机内置的单麦降噪）能处理稳态噪声（引擎声、空调声），但**无法分离他人的语音**。

### 3.2 四层防御架构

```
Audio from Mic ──→ [Layer 0: Gemini Native Audio] ──→ Gemini 的内建处理
                    ↑
                    │ (Hackathon 方案: 仅依赖此层)
                    │
Audio from Mic ──→ [Layer 1: Krisp VIVA] ──→ [Layer 0] ──→ Gemini
                    ↑
                    │ (Production Phase 1: 添加噪声/声音隔离)
                    │
Audio from Mic ──→ [Layer 2: Speaker Verification] ──→ [Layer 1] ──→ [Layer 0]
                    ↑
                    │ (Production Phase 2: 添加说话人识别)
                    │
Multi-Mic Array ──→ [Layer 3: Beamforming] ──→ [Layer 2] ──→ [Layer 1] ──→ [Layer 0]
                    ↑
                    │ (Future: 硬件级多麦克风阵列波束成形)
```

### 3.3 Layer 0: Gemini Native Audio 的内建能力

Gemini 2.5 Flash Native Audio 直接处理原始音频波形（不经过 STT 中间步骤），这意味着模型本身有一定的噪声鲁棒性：

- **Proactive Audio 的"智能沉默"**: 模型能感知背景噪声级别，当噪声很高时会倾向于保持沉默（避免用户在嘈杂中听不清）
- **Affective Dialog**: 感知用户情绪和语调，使 turn-taking 更自然
- **Barge-in 语义判断**: 不仅看 VAD 阈值，还理解语义上下文来判断是否是真正的打断

**Hackathon 策略**: 仅依赖此层 + 受控演示环境（室内、噪声可控）。Demo 时确保在安静环境中展示主要功能。

### 3.4 Layer 1: Krisp VIVA — Voice Isolation for Voice AI (生产级)

**Krisp VIVA 是目前最成熟的 Voice AI 专用降噪方案。** 已被 Daily, LiveKit, Vodex, Fixie 等主流平台集成。

#### 能力

| 能力 | 详情 |
|------|------|
| **背景噪声消除** | 交通、风声、建筑工地等环境噪声 |
| **背景声音消除** | ⭐ 他人说话的声音 — 这是关键差异，普通降噪做不到 |
| **语言无关** | 不依赖特定语言模型，适用于中英文 |
| **低延迟** | 实时处理，增加的延迟可忽略 |
| **服务端部署** | 运行在服务器上，不消耗手机算力 |

#### 实测效果（来自 Krisp + Daily + Pipecat + Gemini Live 的联合测试）

| 指标 | 无 Krisp | 有 Krisp | 改善 |
|------|---------|---------|------|
| 误打断次数 | 基准 | ↓ 71% | **3.5x 更少** |
| 语音识别准确率 | 基准 | ↑ 2x | 翻倍 |
| 通话中断率 | 基准 | ↓ 50% | 减半 |

#### 集成方式（通过 Pipecat）

```python
# Pipecat + Krisp VIVA 集成示例
from pipecat.transports.services.daily import DailyTransport, DailyParams
from pipecat.audio.filters.krisp_filter import KrispVivaFilter

transport = DailyTransport(
    room_url,
    token,
    "SightLine Agent",
    DailyParams(
        audio_in_filter=KrispVivaFilter(),   # ← 在 VAD 之前处理音频
        audio_in_enabled=True,
        audio_out_enabled=True,
    ),
)
```

#### 部署模型

| 模型 | 音频采样率 | 适用场景 |
|------|----------|---------|
| `krisp-viva-tel` | ≤ 16kHz | 电话/移动端（SightLine 的 16kHz PCM 输入匹配此模型） |
| `krisp-viva-pro` | ≤ 32kHz | WebRTC 高保真音频 |
| `krisp-viva-ss` | ≤ 32kHz | 语音分离（Speaker Separation） |

**SightLine 推荐: `krisp-viva-tel`** — 因为 Gemini Live API 的音频输入就是 16kHz PCM。

#### 费用

Krisp VIVA 是**商业 SDK**，需要联系 Krisp 获取定价。但 Pipecat Cloud 用户可以直接通过 `krispViva` 配置项启用（包含在 Pipecat Cloud 费用中）。

**Hackathon 策略**: Krisp VIVA 的集成需要 Pipecat 中间层，增加了架构复杂性。可以在 Demo 的 narrative 中提及它作为 "Production Roadmap"，但 Hackathon 内不实现。

### 3.5 Layer 2: Speaker Verification — 识别"是不是用户在说话"

#### 问题

即使 Krisp VIVA 能消除大多数背景声音，在某些场景下仍然需要确认"说话的人是用户本人"：
- 用户和朋友并排走路聊天 → 谁的话应该被处理？
- 路过的人对着手机说话 → 不应该触发 SightLine

#### 方案：Picovoice Eagle — On-Device Speaker Recognition

Picovoice Eagle 是目前最适合 SightLine 的声纹识别方案：

| 特性 | Eagle |
|------|-------|
| **运行位置** | 完全 On-Device（手机端） |
| **隐私** | 声纹数据不离开设备 |
| **平台** | iOS, Android, Web, Linux |
| **注册** | 仅需 3-5 句话的声纹采集 |
| **识别延迟** | < 100ms |
| **开源** | ⚠️ 非完全开源，SDK 免费用于非商业用途 |

#### 集成架构

```
Mic Audio ──→ Eagle (on-device, < 100ms)
              ├── speaker_match = true  → 发送到 Gemini
              └── speaker_match = false → 丢弃 / 标记为背景声音
```

#### 与 Gemini 的结合

```python
# 前端 (TypeScript/React)
class SpeakerGate {
    private eagle: PicovoiceEagle;
    private isUserSpeaking: boolean = false;

    processAudioChunk(pcmData: Int16Array) {
        const score = this.eagle.process(pcmData);
        if (score > THRESHOLD) {  // 典型阈值: 0.5-0.7
            this.isUserSpeaking = true;
            // 将音频发送到 WebSocket → Gemini
            this.websocket.send(pcmData);
        } else {
            this.isUserSpeaking = false;
            // 不发送 → Gemini 不会被触发
        }
    }
}
```

**Hackathon 策略**: 不实现。在 Demo 脚本和技术亮点中提及为 "Future Capability"。

### 3.6 Layer 3: Multi-Microphone Beamforming (未来方向)

来自 **Google Research / DeepMind 的 SpeechCompass 项目**（CHI 2025 Best Paper Award）：

> **"SpeechCompass: Enhancing Mobile Captioning with Diarization and Directional Guidance via Multi-Microphone Localization"**
> — Samuel Yang (Google Research) & Sagar Savla (Google DeepMind)

核心思想：
- 利用手机的**多麦克风**（iPhone 有 3-4 个麦克风）进行声源定位
- 实时计算每个说话人的方向
- 为每个说话人分配不同的颜色标签
- 用箭头指示声音来源方向

**对 SightLine 的启示**：
- 可以判断声音来自**用户正前方（嘴部）** 还是 **其他方向**
- 正前方 + 近距离 = 大概率是用户在说话
- 其他方向 = 背景/他人

**技术可行性**: 高，但需要深入的原生音频 API 开发（AudioWorklet 无法访问多麦克风独立通道）。需要 Native app（非 PWA）。

**Hackathon 策略**: 完全不实现。但在技术博客和架构图中画出这个层级，展示技术远见。

### 3.7 嘈杂环境策略汇总

| 阶段 | 策略 | 复杂度 | 效果 |
|------|------|--------|------|
| **Hackathon** | Gemini AAD (MEDIUM) + 受控环境 Demo | ⭐ | 足够 Demo |
| **Production P1** | + Pipecat + Krisp VIVA (服务端降噪) | ⭐⭐⭐ | 消除 71% 误打断 |
| **Production P2** | + Picovoice Eagle (端侧声纹) | ⭐⭐⭐⭐ | 精准识别用户 |
| **Future** | + Multi-mic beamforming | ⭐⭐⭐⭐⭐ | 方向感知 + 完全隔离 |

---

## 4. 可直接复用的开源项目与 SDK

### 4.1 综合对比

| 项目 | 用途 | 许可证 | Stars | 与 Gemini 集成 | SightLine 优先级 |
|------|------|--------|-------|---------------|----------------|
| **[Pipecat](https://github.com/pipecat-ai/pipecat)** | 语音 AI Pipeline 框架 | BSD-2 | 10.2k | ✅ 原生支持 Gemini Live | P1 (Production) |
| **[LiveKit Agents](https://github.com/livekit/agents)** | 实时音视频 + AI Agent | Apache-2.0 | 5k+ | ✅ Gemini plugin | P1 (Production alt.) |
| **[Krisp VIVA](https://krisp.ai/developers/)** | Voice Isolation for AI | 商业 SDK | N/A | ✅ via Pipecat | P1 (Production) |
| **[Picovoice Eagle](https://picovoice.ai/platform/eagle/)** | 端侧 Speaker Recognition | SDK 免费 | N/A | 需自行集成 | P2 (Future) |
| **[Picovoice Porcupine](https://picovoice.ai/platform/porcupine/)** | 端侧唤醒词 | SDK 免费 | N/A | 需自行集成 | P3 (可选) |
| **[Daily smart-turn](https://github.com/daily-co/smart-turn)** | 开源 Turn-Taking 模型 | Apache-2.0 | 新项目 | via Pipecat/Daily | P2 (Production) |
| **[InsightFace](https://github.com/deepinsight/insightface)** | 人脸识别 (已在架构中) | MIT | 25k+ | via Function Calling | P2 (已规划) |
| **[Silero VAD](https://github.com/snakers4/silero-vad)** | 轻量级 VAD 模型 | MIT | 5.5k+ | 端侧预处理 | P3 (备选) |

### 4.2 Pipecat 详解 — 为什么它是 Production 的首选

Pipecat 是由 Daily.co 创建的开源语音 AI 框架，专门为构建 STT → LLM → TTS pipeline 设计：

```python
# Pipecat 的典型 pipeline 结构
from pipecat.pipeline.pipeline import Pipeline
from pipecat.transports.services.daily import DailyTransport
from pipecat.services.google import GoogleLLMService
from pipecat.audio.filters.krisp_filter import KrispVivaFilter

pipeline = Pipeline([
    transport.input(),       # 音频输入 (WebRTC from Daily)
    krisp_filter,            # Krisp VIVA 降噪
    vad,                     # VAD 检测
    stt,                     # Speech-to-Text
    llm,                     # Gemini Live / OpenAI
    tts,                     # Text-to-Speech
    transport.output(),      # 音频输出
])
```

**对 SightLine 的价值**：
1. **WebRTC 桥接**: 解决 Gemini Live API 只支持 WebSocket 的抗弱网问题
2. **Krisp VIVA 集成**: 一行代码启用噪声消除
3. **Turn-taking 可定制**: 可以替换 Gemini 的 VAD 为更智能的 LiveKit MultilingualModel
4. **插件生态**: 40+ AI 服务的插件（STT, LLM, TTS 自由组合）

**但 Hackathon 不用 Pipecat 的理由**：
- 增加了一跳延迟（Phone → Daily Edge → Cloud Run → Gemini）
- 需要 Daily 账号和配置
- 破坏了当前"直连 Gemini"的简洁架构
- Hackathon 在受控环境中，不需要抗噪能力

### 4.3 LiveKit Agents — Pipecat 的替代方案

如果 SightLine 选择 LiveKit 而非 Pipecat/Daily 作为 WebRTC 层：

```python
# LiveKit 禁用 Gemini VAD，使用 LiveKit 的 MultilingualModel turn detector
from livekit.plugins import google
from livekit.plugins.turn_detector.multilingual import MultilingualModel

session = AgentSession(
    turn_detection=MultilingualModel(),
    llm=google.realtime.RealtimeModel(
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=True,      # 禁用 Gemini 的 VAD
            ),
        ),
    ),
    stt="assemblyai/universal-streaming",  # 外部 STT for turn detection
)
```

LiveKit 的 MultilingualModel 是一个专门训练的 turn-taking 模型，比简单的 silence-duration 更智能：它理解对话上下文来判断用户是否说完了（semantic endpointing）。

---

## 5. 与现有 SightLine 架构的融合方案

### 5.1 Hackathon 阶段（不改架构）

```
Phone PWA ──WebSocket──→ Cloud Run (ADK) ──WebSocket──→ Gemini Live API
     │                        │
     │                        ├── LOD Engine 动态调整 VAD 参数
     │                        └── Proactive Audio 决定何时说话
     │
     └── 前端手势 (单击/双击/上滑/下滑/长按/摇一摇)
         └── 映射到 WebSocket 信号 (activityStart/End, Telemetry)
```

**需要新增的代码**：
1. **前端手势处理器** (`GestureHandler.ts`): 捕获单击/双击/上滑/下滑/长按/摇一摇
2. **LOD-Adaptive VAD 配置** (`lod_engine.py` 中新增): LOD 切换时发送 VAD 参数更新
3. **触觉反馈** (`HapticFeedback.ts`): 使用 `navigator.vibrate()` API
4. **System Prompt 增强**: 加入 Proactive Audio 行为指导

### 5.2 Production 阶段（架构升级）

```
Phone Native App ──WebRTC──→ Daily/Pipecat Edge ──WebSocket──→ Cloud Run ──WSS──→ Gemini
     │                            │
     │                            ├── Krisp VIVA (服务端降噪)
     │                            ├── smart-turn (语义 turn-taking)
     │                            └── Pipecat Pipeline 编排
     │
     ├── Picovoice Eagle (端侧声纹验证)
     ├── 多麦克风波束成形 (原生 API)
     └── 物理按钮 / AirPods 手势
```

### 5.3 系统 Prompt 中关于交互体验的增强

```
# 追加到 Orchestrator 的 System Prompt:

## TURN-TAKING BEHAVIOR

You are having a continuous, natural conversation. There are NO wake words.

### Responding to user speech:
- SHORT commands (1-3 words like "stop", "what's that?", "go back"):
  Respond IMMEDIATELY with a brief answer.
- MEDIUM questions (1-2 sentences):
  Wait for a natural pause, then respond at appropriate length.
- LONG/COMPLEX input (user is telling a story, explaining something):
  Do NOT interrupt. Wait for a clear ending signal (trailing off, explicit question).

### Handling overlapping audio:
- If you detect multiple voices, ONLY respond to speech that seems directed at you.
- Conversational speech between other people should be IGNORED completely.
- If unsure whether the user is talking to you: stay silent. Better to miss a command
  than to interrupt a real human conversation.

### When you are speaking and get interrupted:
- Stop IMMEDIATELY (within 200ms).
- Acknowledge naturally: "Yes?" or "Go ahead" or just silence.
- Save your current topic and position.
- Process the new input.
- After handling the interruption, ask: "Should I continue where I left off?"

### Audio cues you should listen for:
- Throat clearing / "um" / "so" → User is about to speak, wait for them.
- Laughter → User is not giving a command, acknowledge warmly.
- Sighing → User may be frustrated, adjust tone to be more supportive.
- Footsteps suddenly stopping → User may need environmental info, consider proactive description.
```

---

## 6. 总结：三个问题的最终回答

### Q1: VAD 唤起与结束能不能做到自然？

**结论：能，但需要分层实现。**

| 层级 | 解决什么 | 框架阶段 |
|------|---------|---------|
| Gemini AAD + Proactive Audio | 基础的 turn-taking + 主动说话 | Hackathon |
| LOD-Adaptive VAD 参数 | 不同场景下的 VAD 灵敏度动态调整 | Hackathon |
| System Prompt 行为指导 | 教会 Gemini 什么时候该说/该闭嘴 | Hackathon |
| Pipecat + smart-turn | 语义级 endpointing（理解上下文判断用户是否说完） | Production |

Gemini 的 Native Audio 模型本身就是端到端的，它直接从音频波形理解语义。相比传统的 "VAD → STT → NLU" pipeline，它的 turn-taking 天然更自然。

### Q2: 手机端有哪些妥协方案？

**结论：全屏触控 + 简单手势 + 物理按钮 + 触觉反馈。**

关键原则：
- 整个屏幕就是一个按钮
- 手势设计遵循"盲人用户的肌肉记忆"（单击/双击/上下滑/长按）
- 每个操作都有独特的触觉反馈
- 不依赖精确定位

### Q3: 嘈杂环境怎么办？

**结论：四层防御，逐步构建。**

Hackathon 阶段信任 Gemini 的内建能力 + 受控环境。Production 阶段引入 Krisp VIVA（最大收益，消除 71% 误打断），然后逐步添加声纹识别和多麦克风。

**来自 Google DeepMind 的核心启示 (SpeechCompass, CHI 2025)**：
> 多麦克风声源定位是解决嘈杂环境的终极方案。手机已经有 3-4 个麦克风，但 WebRTC/PWA 无法访问独立麦克风通道（只能获取混合后的单通道音频）。这意味着**生产级 SightLine 需要原生 App**，而非 PWA。

---

## Sources

### Gemini Live API (VAD & Turn-Taking)
- [Live API Capabilities Guide](https://ai.google.dev/gemini-api/docs/live-guide) — AAD configuration
- [Vertex AI Live API Reference](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live) — Activity handling modes
- [Firebase Live API Configuration](https://firebase.google.com/docs/ai-logic/live-api/configuration) — VAD docs
- [Dev Blog: Build with the Live API](https://developers.googleblog.com/en/achieve-real-time-interaction-build-with-the-live-api/) — Configurable VAD
- [GitHub Issue #1285: speech_started/stopped events](https://github.com/googleapis/python-genai/issues/1285)
- [Sipfront: Inside the Brain of Gemini Live](https://sipfront.com/blog/2026/01/baresip-gemini-live-voicebot-deepdive/) — AAD deep dive
- [Google Cloud: Gemini Live API Native Audio Guide](https://cloud.google.com/blog/topics/developers-practitioners/how-to-use-gemini-live-api-native-audio-in-vertex-ai) — Proactive Audio, Barge-in

### Noise Cancellation & Voice Isolation
- [Krisp VIVA SDK](https://krisp.ai/developers/) — Voice Isolation for Voice AI
- [Pipecat + Krisp VIVA Integration](https://docs.pipecat.ai/guides/features/krisp-viva) — Self-hosted guide
- [Pipecat Cloud Krisp Guide](https://docs.pipecat.ai/deployment/pipecat-cloud/guides/krisp-viva) — Cloud deployment
- [Krisp Voice AI Newsletter: Where AI Voice Agents Fail](https://voice-ai-newsletter.krisp.ai/p/where-ai-voice-agents-fail-the-most) — Turn-taking + noise cancellation data

### Speaker Recognition & Diarization
- [Picovoice Eagle](https://picovoice.ai/blog/state-of-speaker-recognition/) — State of Speaker Recognition 2026
- [Google Research: SpeechCompass](https://research.google/blog/making-group-conversations-more-accessible-with-sound-localization/) — CHI 2025 Best Paper, multi-mic localization for accessibility
- [AssemblyAI: Speaker Diarization Libraries](https://www.assemblyai.com/blog/top-speaker-diarization-libraries-and-apis) — Comparison guide

### Voice AI Frameworks
- [Pipecat](https://github.com/pipecat-ai/pipecat) — BSD-2, 10.2k stars
- [LiveKit Agents + Gemini Plugin](https://docs.livekit.io/agents/models/realtime/plugins/gemini/) — Turn detection with MultilingualModel
- [Daily smart-turn](https://github.com/daily-co/smart-turn) — Open-source turn-taking model
- [Medium: Top Voice AI Agent Frameworks 2026](https://medium.com/@mahadise0011/top-voice-ai-agent-frameworks-in-2026-a-complete-guide-for-developers-4349d49dbd2b)

### Accessibility & Blind User UX
- [TopTechTidbits: Voice-First AI for BLV People](https://toptechtidbits.com/how-voice-first-ai-could-soon-change-everything-for-blv-people/) — Comprehensive analysis
- [Ablr360: Voice Control Tools for Visually Impaired](https://ablr360.com/voice-control-tools-for-people-who-are-visually-impaired/) — Best practices
- [FloridaReading: Assistive Tech Trends 2025](https://floridareading.com/blogs/news/top-assistive-tech-trends-for-the-visually-impaired-in-2025)

---

*本文档与 `SightLine_Final_Specification.md` 配合阅读。本文档深入研究交互体验的技术实现细节，Final Specification 是整体产品与技术规格。*
