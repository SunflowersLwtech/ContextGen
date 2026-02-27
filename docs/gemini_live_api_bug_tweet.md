# Gemini Live API Audio Bug — Tweet Draft

## English Version

We're building SightLine, an AI assistant for visually impaired users powered by Gemini Live API's native audio. The model keeps stopping mid-sentence — sending premature turnComplete with no interruption flag.

We've tried everything client-side: hardware AEC, echo gating, SileroVAD, NO_INTERRUPTION mode, disabled auto activity detection. None of it helps because this is a server-side bug.

40+ devs have reported this across googleapis/js-genai#707, python-genai#872, and more. It's been P2 for 8+ months with no fix. Devs are switching to OpenAI Realtime.

Google's official workaround? "Use headphones." Our users are blind — they need reliable audio, not workarounds.

No alternative model exists. Every Gemini Live native audio model has this bug.

Full report: [link to Issue]

@GoogleAI @GoogleDevsJP @GeminiApp

#GeminiAPI #LiveAPI #Accessibility #a11y #AI #GoogleAI #BuildWithGemini

---

## 中文版本

我们正在做 SightLine —— 一个基于 Gemini Live API 原生音频的视障辅助 AI。模型说话说到一半就停了，服务端发出 premature turnComplete，没有任何中断标志。

客户端能做的全做了：硬件回声消除、静音门控、SileroVAD、NO_INTERRUPTION 模式、禁用自动活动检测。都没用，因为这是服务端 Bug。

40+ 开发者在 googleapis/js-genai#707 等多个仓库报告了同一问题。P2 优先级，8 个月没修。开发者们已经开始转投 OpenAI Realtime。

Google 官方的"解决方案"？"戴耳机。" 我们的用户是视障人群 —— 他们需要可靠的音频输出，不是权宜之计。

目前没有任何替代模型。所有 Gemini Live 原生音频模型都有这个 Bug。

完整报告: [Issue 链接]

@GoogleAI @GoogleDevsJP @GeminiApp

#GeminiAPI #LiveAPI #无障碍 #Accessibility #AI #GoogleAI

---

## Usage Notes

- Post English version on X (Twitter), link to the GitHub Issue after filing
- Chinese version for Weibo / Chinese dev communities
- Replace `[link to Issue]` / `[Issue 链接]` with the actual GitHub Issue URL after filing
- Character count: English ~780 chars (will need to be a thread or trimmed for X's 280 limit — see Thread Version below)

---

## X Thread Version (280 chars per tweet)

**Tweet 1/4:**
Building SightLine — an AI assistant for visually impaired users on Gemini Live API. The model keeps stopping mid-sentence. Server sends premature turnComplete, no interruption flag. 8+ months, 40+ devs affected, still P2.

**Tweet 2/4:**
We tried EVERYTHING client-side:
- Hardware AEC (iOS Voice Processing I/O)
- Echo gating (silence during playback)
- SileroVAD
- NO_INTERRUPTION mode
- Disabled auto activity detection

None of it works. This is a server-side bug.

**Tweet 3/4:**
Google's official workaround: "Use headphones."

Our users are blind. They need reliable audio output — not workarounds.

No alternative Gemini Live audio model exists without this bug. Devs are switching to OpenAI Realtime.

**Tweet 4/4:**
Full bug report with reproduction steps, evidence, and all related issues:
[Issue link]

Related: googleapis/js-genai#707 (core issue, P2, OPEN 8+ months)

@GoogleAI @GeminiApp
#GeminiAPI #LiveAPI #Accessibility #a11y
