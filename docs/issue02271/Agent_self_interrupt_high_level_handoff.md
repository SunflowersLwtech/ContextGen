# Issue 02271 — agent自我抢话（高层交接）

## 1) 问题概述
在 iOS Debug（本地后端）场景下，agent 语音对话存在明显“自己和自己抢话/打断自己”的体验问题。
该问题在会话开场（例如打招呼阶段）即可出现，不依赖复杂操作。

## 2) 影响范围
- 用户主观体验明显劣化（不连贯、像双声道抢话）。
- 可重复出现，且伴随客户端播放缓冲溢出日志。

## 3) 关键现象（来自最新真机日志）
- WebSocket 最终可连接并收到 `Session ready`。
- 音频链路已启动：`SharedAudioEngine started (VP=true)`、`Audio capture started`。
- 高频出现：`Audio buffer overflow (20 chunks), dropping 10 oldest`。
- 问题从开场就存在，不是长会话后才出现。

注：日志中还包含若干网络握手 reset、WatchConnectivity 文件枚举告警等噪音信息；当前未确认它们是主因。

## 4) 当前判断（高层，非结论）
更像是“实时音频收发节奏失衡 + 回声/中断状态机交互”问题，而不是单点数据库或单点鉴权问题。
`Audio buffer overflow` 与“抢话感”可能同根：下行音频堆积、回放与上行门控时机不一致。

## 5) 已尝试方向（供参考，不保证充分）
- 调整 barge-in 判定阈值/确认窗口。
- 增加打断后短抑制窗，尝试丢弃旧下行残片。
- 缩小播放队列上限（50 -> 20）。
- 本地后端已反复 clean restart，确认单进程监听 8100。

结果：问题仍可复现，且 overflow 仍频繁。

## 6) 建议下一步（给接手 AI）
建议以“端到端时序观测”优先，而不是继续调单一阈值：
1. 对齐时间线：
   - 下行音频到达/入队/出队/实际播放
   - 上行音频是否被门控为 silence
   - interrupted/turn_complete 与本地 stop/suppress 的先后
2. 区分网络抖动与本地调度：
   - 是否出现突发大包导致短时下行洪峰
   - 是否出现播放线程饥饿后补偿性堆积
3. 先找“开场即复现”的最短路径，再基于证据做结构性修复。

## 7) 环境上下文
- 项目路径：`/Users/sunfl/Documents/study/ContextGen`
- iOS Debug 连接本地：`ws://Lius-MacBook-Air.local:8100`
- 本地后端入口：`SightLine/server.py`
- 当前诉求：达到类似 Gemini Live Mode 的连续流畅语音体验

---
该文档故意保持高层，不对根因下最终结论，避免误导后续排查。