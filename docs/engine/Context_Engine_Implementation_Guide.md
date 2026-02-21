# SightLine Context Engine: Implementation Guide

> Date: 2026-02-21
> Status: Research-backed implementation specification
> Raw Research: `../raw_research/engine/`

---

## Executive Summary

经过对 18 篇学术论文、15+ 开源框架和 13 个商业产品的系统调研，我们确认：

> **没有任何现有产品同时实现 (a) 跨会话用户记忆 + (b) 实时多传感器环境感知 + (c) 自适应信息密度（LOD）—— 专为视障用户设计。**

这不是"锦上添花"。RAVEN (ASSETS 2025) 研究中 5/8 的盲人用户明确要求自适应细节层级；Say It My Way (CHI 2026) 证明盲人用户需要但目前缺乏持久偏好系统；Describe Now (DIS 2025) 证明手动控制反而增加认知负荷。

SightLine 的 Context Engine 是填补这个空白的核心组件。

---

## 1. Architecture Overview

```
                    ┌─────────────────────────────┐
                    │     Context Engine           │
                    │  (Dynamic System Prompt 构建) │
                    └──────────┬──────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  Ephemeral   │  │   Session    │  │  Long-term   │
    │  Context     │  │   Context    │  │  Context     │
    │  (ms~s)      │  │  (min~hr)    │  │  (跨会话)    │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                 │
    SEP-Telemetry      Gemini Context     Vertex AI
    JSON Stream        Window 内维持      Memory Bank
    + 规则引擎           + Session State    (首选, ~30行)
      语义化               Manager        Firestore fallback
```

三层上下文融合后，输入 LOD Decision Engine，决定 LOD 1/2/3，然后构建 Dynamic System Prompt 交给 Orchestrator（Gemini 2.5 Flash Live API）。

---

## 2. Layer 1: Ephemeral Context — 实时传感器

### 2.1 数据来源

轻量化设计：Core 字段全部来自手机传感器，无需额外硬件。

```json
{
  "timestamp": "2026-02-21T10:30:00Z",

  // === Core 字段 (手机自带传感器) ===
  "step_cadence": 72,                 // 手机加速度计 (iOS CMPedometer, steps per minute)
  "motion_state": "walking",          // 手机 Core Motion / Activity Recognition
                                      // "stationary" | "walking" | "running" | "in_vehicle"
  "ambient_noise_db": 65,             // 手机麦克风后台 RMS → dB
  "gps": { "lat": 37.7749, "lng": -122.4194 },
  "time_context": { "hour": 8, "period": "morning_commute" },

  // === Optional 字段 (智能手表，有则启用) ===
  "heart_rate": 78,                   // null if no watch connected

  "device_type": "phone_only"         // "phone_only" | "phone_and_watch" | "simulation_console"
}
```

### 2.2 传感器 → 语义转化（ContextLLM 方法）

**不要直接把 JSON 塞进 prompt**。参考 ContextLLM (ACM 2025) 的三层管道：

```
Layer 1 (Raw):     motion_state=walking, step_cadence=96/min, ambient_noise_db=78, heart_rate=145 (optional)
Layer 2 (Sparse):  "快速行走 + 高噪声环境 + 心率偏高"
Layer 3 (Semantic): "用户处于紧张的快速移动状态，身处嘈杂街道，可能在过马路"
```

实现方式——用规则引擎（不用 LLM，太慢）：

```python
def telemetry_to_semantic(t: Telemetry) -> str:
    segments = []

    # 运动状态 (Core: 手机加速度计)
    # 优先使用系统级 motion_state，step_cadence 作为补充
    if t.motion_state == "in_vehicle":
        segments.append("用户在交通工具中")
    elif t.motion_state == "running" or t.step_cadence > 120:
        segments.append("快速移动")
    elif t.motion_state == "walking":
        if t.step_cadence < 60:
            segments.append("缓慢行走，探索状态")
        else:
            segments.append("正常步行")
    else:  # stationary
        segments.append("用户静止")

    # 环境噪声 (Core: 手机麦克风)
    if t.ambient_noise_db > 80:
        segments.append("高噪声环境（如地铁站、街道）")
    elif t.ambient_noise_db > 60:
        segments.append("中等噪声（如咖啡厅）")
    elif t.ambient_noise_db < 40:
        segments.append("安静环境（如室内、图书馆）")

    # 压力状态 (Optional: 智能手表)
    if t.heart_rate is not None:
        if t.heart_rate > 120:
            segments.append("高压力/恐慌信号")
        elif t.heart_rate > 100:
            segments.append("轻度紧张")
        else:
            segments.append("心率正常")

    # 时间上下文 (Core: 手机时钟)
    if t.time_context and t.time_context.period:
        period_map = {
            "morning_commute": "早高峰通勤时段",
            "work_hours": "工作时段",
            "evening": "傍晚/休闲时段",
            "late_night": "深夜（注意安全提示）",
        }
        if t.time_context.period in period_map:
            segments.append(period_map[t.time_context.period])

    return "。".join(segments)
```

### 2.3 PANIC 中断机制

学术依据：Pedestrian Stress with Biometric Sensors (ScienceDirect, 2025) 证明心率突升对行走压力检测可靠。

```python
# PANIC 检测：heart_rate 为可选字段，无手表时跳过心率恐慌检测
if t.heart_rate is not None and t.heart_rate > 120:
    # PANIC: 强制 LOD 1，清空 TTS 队列
    lod_manager.force_downgrade(level=1)
    tts_queue.clear()
    return safety_response("周围安全，深呼吸。需要我帮你做什么吗？")
```

### 2.4 Telemetry LOD-Aware 节流（P0）

> **工程加固点**：Telemetry 发送频率必须与 LOD 联动——LOD 1 行走时需要更频繁的传感器更新（安全优先），LOD 3 静止时可大幅降低（节省带宽+token）。

```python
# TelemetryAggregator: LOD-Aware 发送间隔
LOD_TELEMETRY_INTERVAL: dict[int, tuple[float, float]] = {
    1: (3.0, 4.0),   # 行走中：3-4 秒，安全优先但避免淹没
    2: (2.0, 3.0),   # 探索中：2-3 秒，需要较频繁更新以检测空间变化
    3: (5.0, 10.0),  # 静止中：5-10 秒，用户状态稳定，无需高频更新
}

class TelemetryAggregator:
    def __init__(self):
        self._current_lod: int = 2
        self._last_send_time: float = 0

    def update_lod(self, lod: int):
        """LOD 变化时由 LOD Engine 回调"""
        self._current_lod = lod

    @property
    def send_interval(self) -> float:
        lo, hi = LOD_TELEMETRY_INTERVAL[self._current_lod]
        return lo  # 使用区间下限；生产环境可加抖动

    def should_send(self, now: float) -> bool:
        """定时发送检查（ImmediateTrigger 不受此限制）"""
        return (now - self._last_send_time) >= self.send_interval

    def mark_sent(self, now: float):
        self._last_send_time = now
```

**与 ImmediateTrigger 的关系**：PANIC、motion_state 切换、heart_rate_spike 等 `ImmediateTrigger` 事件**不受节流限制**，始终立即发送。LOD-Aware 节流仅控制定时轮询频率。

---

## 3. Layer 2: Session Context — 当前行程状态

### 3.1 Session State Manager

在 Gemini Live API 的上下文窗口内维持，不需要外部存储：

```python
class SessionContext:
    trip_purpose: str           # "去面试" / "日常通勤" / "购物"
    space_type: str             # "indoor" / "outdoor" / "vehicle"
    space_transitions: list     # ["室外 → 大堂", "大堂 → 电梯"]
    avg_cadence_30min: float    # 30 分钟步频均值（判断趋势）
    conversation_topics: list   # 近期对话主题
    active_task: str | None     # "正在读菜单" / None
    narrative_snapshot: dict | None  # LOD 降级时的断点
```

### 3.2 空间转换检测

```python
def detect_space_transition(prev_gps, curr_gps, prev_light, curr_light):
    """基于 GPS 跳变 + 光线变化检测室内外切换"""
    if gps_distance(prev_gps, curr_gps) < 5:  # 5m 内
        if abs(curr_light - prev_light) > threshold:
            return "outdoor_to_indoor" if curr_light < prev_light else "indoor_to_outdoor"
    return None
```

空间转换是 LOD 升级的天然触发器——进入新空间时用户需要更多信息（LOD 2）。

### 3.3 Narrative Snapshot（LOD 降级断点保存）

这是 SightLine 的独创设计，参考 Letta/MemGPT 的 context checkpoint 概念：

```python
# 降级时保存
def on_lod_downgrade(current_task):
    if current_task:
        snapshot = {
            "task_type": current_task.type,      # "menu_reading"
            "progress": current_task.progress,    # "已读到第3道菜：宫保鸡丁"
            "remaining": current_task.remaining,  # ["第4-8道菜", "饮品区"]
            "timestamp": now()
        }
        session.narrative_snapshot = snapshot
        tts.say("好的，我先暂停。")

# 恢复时继续
def on_lod_upgrade():
    if session.narrative_snapshot:
        snap = session.narrative_snapshot
        time_delta = now() - snap["timestamp"]
        if time_delta < timedelta(minutes=10):
            # 从断点继续
            prompt_inject = f"用户之前在{snap['task_type']}，已完成: {snap['progress']}。请从 {snap['remaining'][0]} 继续。"
            session.narrative_snapshot = None
            return prompt_inject
        else:
            # 超时，重新开始
            session.narrative_snapshot = None
            return None
```

---

## 4. Layer 3: Long-term Context — 跨会话用户记忆

### 4.1 架构选择

调研了 Mem0（41K stars）、Letta（38K stars）、Zep/Graphiti（20K stars）三个框架后的建议：

| 方案 | 优点 | 缺点 | 建议 |
|------|------|------|------|
| **Firestore 原生向量搜索**（当前方案） | 无额外依赖，已在技术栈内 | 查询能力有限，无自动提取 | 作为存储层保留 |
| **+ Mem0 式自动提取逻辑** | 自动从对话中提取结构化记忆 | 需要额外 LLM 调用 | 采用其设计模式，自行实现 |
| **+ Graphiti 式时序查询**（可选） | "用户上周 vs 现在的偏好" | 增加复杂度 | Phase 2 考虑 |

**推荐方案**: **Vertex AI Memory Bank**（首选，~30 行集成，ADK 原生）。详见 `Memory_System_Research_and_Integration.md` §3。以下自建方案仅作为 **fallback 备选**（当 Memory Bank 提取逻辑不够灵活时再启用）。

### 4.2 记忆分类与存储

#### Explicit Profile（用户主动填写）

基于 Beyond the Cane (ACM TACCESS 2022) 的研究发现设计：

```python
class UserProfile:
    # === 基本信息 ===
    vision_status: str          # "totally_blind" | "low_vision"
    blindness_onset: str        # "congenital" | "acquired"
    onset_age: int | None       # 后天盲的发生年龄
    has_guide_dog: bool         # 有导盲犬 → 不需要水坑/台阶预警
    has_white_cane: bool        # 有白杖 → 不需要碰撞危险预警

    # === 偏好 ===
    tts_speed: float            # 1.0 - 3.0x（盲人用户普遍偏好 2.0-3.0x）
    verbosity_preference: str   # "minimal" | "standard" | "detailed"
    language: str               # "zh-CN" | "en-US" | ...
    description_priority: str   # "spatial" | "object" | "text"
    # Beyond the Cane 发现：先天盲优先空间信息，后天盲优先物体位置

    # === O&M（定向行走）训练 ===
    om_level: str               # "beginner" | "intermediate" | "advanced"
    travel_frequency: str       # "daily" | "weekly" | "rarely"
    # Beyond the Cane 发现：高频出行者需要的信息量显著更少
```

**为什么这些字段重要**:
- 先天盲用户出行频率高 11x，提问少 3x（Beyond the Cane）
- 有导盲犬的用户不需要地面障碍预警（SightLine Final Spec）
- TTS 语速偏好差异巨大，错误的语速直接影响可用性（社区共识）
- O&M 训练水平和出行频率是信息需求量的最强预测因子

#### Implicit Episodic Memory（系统自动学习）

```python
class EpisodicMemory:
    category: str       # "preference" | "location" | "person" |
                        # "behavior" | "stress_trigger" | "routine"
    content: str        # "用户偏好先描述左侧再描述右侧"
    source: str         # "conversation_extraction" | "behavior_pattern"
    confidence: float   # 0.0 - 1.0
    created_at: datetime
    last_accessed: datetime
    access_count: int
    embedding: list[float]  # gemini-embedding-001, 3072 dims → truncate to 2048
```

**存储示例**:

```json
[
  {
    "category": "location",
    "content": "用户称腾讯大厦B座为'公司'",
    "confidence": 0.95,
    "embedding": [...]
  },
  {
    "category": "person",
    "content": "face_id_abc123 是用户的老板 David，关系: 上下级",
    "confidence": 0.90,
    "embedding": [...]
  },
  {
    "category": "stress_trigger",
    "content": "用户在人多的地铁站心率持续升高，需要预防性 LOD 降级",
    "confidence": 0.75,
    "embedding": [...]
  },
  {
    "category": "routine",
    "content": "工作日 8:30 从家出发，步行 → 地铁 → 公司，约 45 分钟",
    "confidence": 0.85,
    "embedding": [...]
  }
]
```

### 4.3 记忆自动提取流程

参考 Mem0 的设计模式，在 Session 结束时执行：

```python
MAX_NEW_MEMORIES_PER_SESSION = 5  # P1: 写入预算，防止单次会话记忆膨胀

async def consolidate_session_memories(conversation_history, user_id):
    """Session 结束时的记忆巩固"""

    # 1. 用 Gemini Flash 提取潜在记忆
    extraction_prompt = f"""
    分析以下对话，提取值得长期记住的信息。
    分类: preference, location, person, behavior, stress_trigger, routine
    只提取高置信度的事实，不要推测。
    如果对话中没有值得记住的信息，返回空列表。
    最多提取 {MAX_NEW_MEMORIES_PER_SESSION} 条（按重要性排序）。

    对话:
    {conversation_history}
    """
    new_memories = await gemini_flash.generate(extraction_prompt)

    # P1: 写入预算截断——防止长会话产生过多记忆写入
    if len(new_memories) > MAX_NEW_MEMORIES_PER_SESSION:
        new_memories = sorted(new_memories, key=lambda m: m.confidence, reverse=True)
        new_memories = new_memories[:MAX_NEW_MEMORIES_PER_SESSION]

    # 2. 检查冲突——新记忆是否与已有记忆矛盾
    for memory in new_memories:
        existing = await firestore.vector_search(
            collection="memories",
            query_embedding=embed(memory.content),
            top_k=3,
            filters={"user_id": user_id, "category": memory.category}
        )
        if existing and cosine_similarity(existing[0].embedding, memory.embedding) > 0.85:
            # 更新已有记忆，而非新建
            await update_memory(existing[0].id, memory)
        else:
            # 新建记忆
            await create_memory(user_id, memory)

    # 3. 衰减旧记忆
    await decay_unused_memories(user_id, decay_factor=0.95)
```

### 4.4 记忆检索（为 Dynamic Prompt 服务）

```python
async def retrieve_relevant_memories(user_id, current_context: str, top_k=5):
    """基于当前上下文检索相关长期记忆"""

    query_embedding = await embed(current_context)

    results = await firestore.vector_search(
        collection="memories",
        query_embedding=query_embedding,
        top_k=top_k * 2,  # 检索多一些，后面排序
        filters={"user_id": user_id}
    )

    # Mem0 式排序：relevance * recency * importance
    scored = []
    for r in results:
        relevance = r.similarity_score
        recency = recency_score(r.last_accessed)  # 越近越高
        importance = importance_weight(r.category)  # stress_trigger > routine > preference
        final_score = relevance * 0.5 + recency * 0.3 + importance * 0.2
        scored.append((r, final_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [r for r, _ in scored[:top_k]]
```

### 4.5 记忆删除接口 —"忘掉刚才的"（P2 预留）

> **工程预留**：用户应能口头请求删除记忆（"忘掉刚才我说的"）。Phase 2 实现，Hackathon 阶段仅预留接口。

```python
async def forget_recent_memory(user_id: str, hint: str | None = None):
    """P2: 用户请求删除最近写入的记忆

    触发方式：用户说 "忘掉刚才的" / "delete that" / "别记住这个"
    Orchestrator 通过 Function Calling 调用此接口。

    Args:
        user_id: 用户 ID
        hint: 可选，用户描述要删除的内容（用于语义匹配）
    """
    if hint:
        # 语义匹配删除
        candidates = await firestore.vector_search(
            collection="memories",
            query_embedding=embed(hint),
            top_k=3,
            filters={"user_id": user_id}
        )
        if candidates and candidates[0].similarity_score > 0.75:
            await delete_memory(candidates[0].id)
            return f"已删除记忆: {candidates[0].content[:50]}..."
    else:
        # 删除最近一条写入的记忆
        latest = await get_latest_memory(user_id)
        if latest:
            await delete_memory(latest.id)
            return f"已删除最近记忆: {latest.content[:50]}..."

    return "没有找到匹配的记忆"
```

**Function Declaration（预留）**：
```python
forget_memory_func = FunctionDeclaration(
    name="forget_recent_memory",
    description="用户请求删除最近的记忆。当用户说'忘掉'、'别记住'、'delete that'时调用。",
    parameters={"hint": {"type": "string", "description": "用户描述要删除的内容（可选）"}},
    behavior=FunctionCallingBehavior.WHEN_IDLE,
)
```

---

## 5. LOD Decision Engine — 三层融合决策

### 5.1 Decision Algorithm

参考 ContextAgent (NeurIPS 2025) 的主动必要性评分，但扩展为连续 LOD 值。

> **Think-Before-Act 策略** (来源: ContextAgent §5.4)
> ContextAgent 实验表明，在 few-shot 场景下加入 Chain-of-Thought 推理可提升 20.1% 的 Proactive Accuracy。
> SightLine 应用：LOD 决策在规则引擎之外，可以在 Orchestrator 的 System Prompt 中加入轻量 CoT 引导，
> 让 Gemini 在非紧急场景下先内部推理再输出。详见 §5.3 LOD CoT Prompt。

```python
def decide_lod(ephemeral: EphemeralContext,
               session: SessionContext,
               profile: UserProfile) -> int:
    """融合三层 Context 决定 LOD 等级"""

    # === Rule 1: PANIC 中断（最高优先级，仅在有手表心率时触发） ===
    if ephemeral.heart_rate is not None and ephemeral.heart_rate > 120:
        return 1  # 强制 LOD 1

    # === Rule 2: 基于运动状态的基线（Core: 手机传感器） ===
    # 优先使用 motion_state（系统级分类，更鲁棒），step_cadence 作为精细化补充
    if ephemeral.motion_state == "running" or ephemeral.step_cadence > 120:
        base_lod = 1  # 快速移动 → 沉默
    elif ephemeral.motion_state == "walking":
        if ephemeral.step_cadence < 60:
            base_lod = 2  # 缓慢行走/探索 → 标准描述
        else:
            base_lod = 1  # 正常行走 → 默认沉默
    elif ephemeral.motion_state == "in_vehicle":
        base_lod = 3  # 在交通工具中 → 可以详细叙述（不需要听路况）
    else:  # stationary
        base_lod = 3  # 静止 → 可以详细叙述

    # === Rule 3: 环境噪声调整（Core: 手机麦克风） ===
    if ephemeral.ambient_noise_db > 80:
        base_lod = min(base_lod, 1)  # 极高噪声 → 强制精简，用户可能听不清
    elif ephemeral.ambient_noise_db < 40:
        # 安静环境不改变 LOD，但标记 AI 应低语（在 prompt 中处理）
        pass

    # === Rule 4: 空间转换提升 ===
    if session.recent_space_transition:
        base_lod = max(base_lod, 2)  # 进入新空间至少 LOD 2

    # === Rule 5: 用户偏好调整 ===
    if profile.verbosity_preference == "minimal":
        base_lod = max(1, base_lod - 1)
    elif profile.verbosity_preference == "detailed":
        base_lod = min(3, base_lod + 1)

    # === Rule 6: O&M 水平调整 ===
    if profile.om_level == "advanced" and profile.travel_frequency == "daily":
        base_lod = max(1, base_lod - 1)  # 高水平用户需要更少信息

    # === Rule 7: 用户显式请求（最终覆盖） ===
    if session.user_requested_detail:
        return 3
    if session.user_said_stop:
        return 1

    return base_lod
```

### 5.2 "发声有成本"机制

```python
class SpeechCostManager:
    """每次发声分配认知成本分数"""

    def should_speak(self, info_value: float, current_lod: int,
                     step_cadence: float, ambient_noise_db: float = 50.0) -> bool:
        # 运动越快，发声阈值越高
        movement_penalty = (step_cadence / 60.0) * 2.0  # 归一化为步/秒后乘以权重

        # 噪声越高，发声阈值越高（嘈杂环境中只说关键信息）
        noise_penalty = max(0, (ambient_noise_db - 60) * 0.1)  # 60dB 以上开始增加成本

        threshold = BASE_THRESHOLD + movement_penalty + noise_penalty

        # 只有高价值信息能突破阈值
        return info_value > threshold

    def calculate_info_value(self, info_type: str) -> float:
        VALUES = {
            "safety_warning": 10.0,    # 始终突破
            "navigation_instruction": 8.0,
            "face_recognition": 7.0,
            "space_description": 5.0,
            "object_enumeration": 3.0,
            "ambient_description": 1.0,  # 几乎从不在行走时说
        }
        return VALUES.get(info_type, 1.0)
```

### 5.3 LOD CoT Prompt — 轻量推理链

> **来源**: ContextAgent (NeurIPS 2025) — Think-Before-Act 策略在 few-shot 下提升 20.1% Acc-P

在非紧急场景下（排除 PANIC 规则引擎直接接管的情况），让 Orchestrator 在内部先推理 LOD 决策再输出语音。通过 System Prompt 注入轻量 CoT：

```python
LOD_COT_PROMPT = """
Before responding, internally reason about the appropriate response level:
<think>
1. User physical state: [moving/stationary/in_vehicle] at [cadence] steps/sec
2. Environment: [noise_level]dB, [space_type]
3. Current task: [active_task or "none"]
4. Persona factors: [vision_status], [verbosity_preference], [om_level]
→ Therefore LOD should be: [1/2/3] because [one-sentence reason]
</think>
Then respond according to the determined LOD level.
Do NOT output the <think> block to the user — it is for internal reasoning only.
"""
```

**使用限制**:
- LOD 1 (行走中) 时**不启用 CoT**——延迟不可接受，安全信息必须即时传达
- LOD 2/3 (探索/静止) 时启用——用户处于放松状态，50-100ms 的推理延迟可接受
- PANIC 规则引擎触发时，直接跳过 CoT，硬编码响应

```python
def get_system_prompt_with_cot(base_prompt: str, current_lod: int) -> str:
    """仅在 LOD 2/3 时注入 CoT 推理链"""
    if current_lod >= 2:
        return base_prompt + "\n\n" + LOD_COT_PROMPT
    return base_prompt  # LOD 1: 不加 CoT，极速响应
```

### 5.4 LOD Decision Log — 可解释日志（P0）

> **工程加固点**：LOD 决策是一个纯规则引擎的黑盒。必须记录每次决策的输入、触发的规则和输出，用于调试、Demo 展示和后期阈值调优。

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class LODDecisionLog:
    """每次 LOD 决策的完整可解释日志"""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # 输入快照
    motion_state: str = ""
    step_cadence: float = 0.0
    ambient_noise_db: float = 50.0
    heart_rate: float | None = None
    space_transition: bool = False
    verbosity_preference: str = "standard"
    om_level: str = "intermediate"
    user_override: str | None = None  # "详细说说" / "停" / None

    # 决策过程
    triggered_rules: list[str] = field(default_factory=list)  # ["Rule2:walking→LOD1", "Rule4:space_transition→LOD2"]
    base_lod_before_adjustments: int = 2

    # 输出
    final_lod: int = 2
    reason: str = ""  # 一句话总结，如 "walking + space_transition → LOD 2"

    def to_debug_dict(self) -> dict:
        """供 DebugOverlay 显示的精简版"""
        return {
            "lod": self.final_lod,
            "reason": self.reason,
            "rules": self.triggered_rules,
            "hr": self.heart_rate,
            "motion": self.motion_state,
            "noise_db": self.ambient_noise_db,
        }
```

**集成到 `decide_lod()`**：

```python
def decide_lod(ephemeral: EphemeralContext,
               session: SessionContext,
               profile: UserProfile) -> tuple[int, LODDecisionLog]:
    """融合三层 Context 决定 LOD 等级，同时返回可解释日志"""

    log = LODDecisionLog(
        motion_state=ephemeral.motion_state,
        step_cadence=ephemeral.step_cadence,
        ambient_noise_db=ephemeral.ambient_noise_db,
        heart_rate=ephemeral.heart_rate,
        space_transition=session.recent_space_transition,
        verbosity_preference=profile.verbosity_preference,
        om_level=profile.om_level,
    )

    # Rule 1: PANIC
    if ephemeral.heart_rate is not None and ephemeral.heart_rate > 120:
        log.triggered_rules.append("Rule1:PANIC→LOD1")
        log.final_lod = 1
        log.reason = f"PANIC: heart_rate={ephemeral.heart_rate}>120"
        return 1, log

    # Rule 2: 运动状态基线 ... (existing logic)
    # 每条规则触发时：log.triggered_rules.append("Rule2:walking→LOD1")

    # ... 最终
    log.final_lod = base_lod
    log.reason = " + ".join(log.triggered_rules) + f" → LOD {base_lod}"
    return base_lod, log
```

**日志输出位置**：
- **开发阶段**：通过 WebSocket 发送 `{"type":"debug_lod","data":{...}}` 到 iOS DebugOverlay
- **生产阶段**：写入 Cloud Logging（structured JSON），可用 BigQuery 做阈值回归分析

---

## 6. Proactive-Oriented Context Extraction (Vision Agent)

> **来源**: ContextAgent (NeurIPS 2025) §4.1 — Proactive-Oriented Context Extraction
> **核心发现**: 面向目的的上下文提取显著优于泛泛的场景描述

### 6.1 问题

标准 VLM 描述（"用户坐在椅子上系鞋带"）包含大量与主动服务无关的信息，同时遗漏关键线索。ContextAgent 的消融实验证明：

| 提取方式 | Acc-P | Tool F1 | Acc-Args |
|---------|-------|---------|----------|
| Proactive-Oriented (ICL) | 基线 | 基线 | 基线 |
| Zero-shot VLM 提取 | -3.0% | -3.3% | -1.9% |

差距虽然看似不大，但在实时辅助场景中，3% 的工具选择错误意味着用户收到不相关的信息或错过关键提示。

### 6.2 对 SightLine Vision Agent 的具体优化

**原则**: 不让 Vision Agent 回答"你看到了什么"，而是回答"对视障用户当前行动有什么影响"。

**Vision Agent System Prompt 注入（LOD-Adaptive）**:

```python
VISION_EXTRACTION_PROMPTS = {
    1: """Analyze this frame for SAFETY-CRITICAL information only.
Focus on: obstacles, moving vehicles, approaching people, stairs, uneven ground.
Ignore: decorations, colors, distant objects, brand names.
Output format: [SAFETY] <threat_type>: <brief description + direction + distance>
If nothing safety-critical: output "CLEAR".""",

    2: """Analyze this frame for NAVIGATION and SPATIAL information.
Focus on:
- Spatial layout (entrances, exits, paths, barriers)
- Key landmarks for orientation (counters, doors, large furniture)
- People and their relative positions
- Signs or text that affect navigation
Ignore: fine visual details, colors (unless high-contrast wayfinding), decorative elements.
Output: structured spatial description, start with overall layout, then key objects with clock-position directions.""",

    3: """Analyze this frame COMPREHENSIVELY for full scene narration.
Include:
- Complete spatial layout with dimensions
- All readable text (signs, menus, labels, screens)
- People: count, positions, expressions, activities
- Objects: type, position, notable features
- Atmosphere: lighting, crowding level, noise indicators
Output: rich narrative description suitable for someone who cannot see.""",
}
```

**关键差异**（vs. 之前的通用描述 prompt）:
- LOD 1 只提取安全威胁，输出可以是单词"CLEAR"——极大减少无用信息
- LOD 2 用"clock-position"方向系统，直接可用于空间导航描述
- LOD 3 才做全量描述，且强调"suitable for someone who cannot see"引导 VLM 输出盲人友好的描述
- 每个级别都有明确的 Ignore 列表，避免信息过载

### 6.3 多模态消融数据支撑

ContextAgent 消融实验量化了各模态的重要性：

| 缺失模态 | Acc-P 变化 | Tool F1 变化 |
|---------|-----------|-------------|
| 缺失视觉 | **-17.9%** | **-23.3%** |
| 缺失音频 | 较小但显著 | 较小但显著 |
| 缺失 Persona | **-9.0%** | **-12.3%** |

**对 SightLine 的设计验证**:
- 视觉是最关键模态，确认 1FPS JPEG 输入是正确的核心设计
- Persona 贡献 9% 准确率——不是锦上添花，是必需品（见 §4 UserProfile 设计）
- 在嘈杂环境中应降低对音频上下文的依赖权重，更多依赖视觉+传感器

---

## 7. Dynamic System Prompt Construction

### 7.1 Prompt 结构

所有上下文层汇总为一个 System Prompt，交给 Orchestrator：

```python
def build_dynamic_prompt(lod: int,
                         profile: UserProfile,
                         ephemeral_semantic: str,
                         session: SessionContext,
                         long_term_memories: list[Memory],
                         vision_result: str | None = None,
                         face_result: str | None = None) -> str:

    prompt = f"""你是 SightLine，为视障用户提供环境语义翻译的 AI 助手。

## 用户档案
- 视力: {profile.vision_status}（{'先天' if profile.blindness_onset == 'congenital' else '后天'}）
- 辅助工具: {'导盲犬' if profile.has_guide_dog else ''}{'白杖' if profile.has_white_cane else ''}
- TTS 语速: {profile.tts_speed}x
- O&M 水平: {profile.om_level}
- 描述偏好: {profile.verbosity_preference}

## 当前状态（LOD {lod}）
{LOD_INSTRUCTIONS[lod]}

## 实时 Context
{ephemeral_semantic}

## 行程 Context
- 出行目的: {session.trip_purpose or '未指定'}
- 当前空间: {session.space_type}
- 空间转换: {session.space_transitions[-1] if session.space_transitions else '无'}
"""

    # 条件注入
    if session.narrative_snapshot:
        prompt += f"""
## 之前的任务
{session.narrative_snapshot['task_type']}进行中，已完成: {session.narrative_snapshot['progress']}。
请从 {session.narrative_snapshot['remaining'][0]} 继续，不要重头开始。
"""

    if long_term_memories:
        prompt += "\n## 相关历史记忆\n"
        for m in long_term_memories:
            prompt += f"- [{m.category}] {m.content}\n"

    if vision_result:
        prompt += f"\n## 视觉分析\n{vision_result}\n"

    if face_result:
        prompt += f"\n## 人脸识别\n{face_result}\n"

    return prompt
```

### 7.2 LOD 指令模板

```python
LOD_INSTRUCTIONS = {
    1: """当前 LOD 1（静默/低语模式）。
规则: 完全沉默或最多1句话（15-40字）。只说安全关键信息。
风格: 简短、平静、不抢注意力。
示例: "前方台阶" / "右侧有人靠近"
如果没有安全关键信息，保持沉默。""",

    2: """当前 LOD 2（标准模式）。
规则: 中等描述（80-150字）。包含空间布局 + 关键物体。
风格: 中等语速，清晰。
描述顺序: 先整体空间 → 关键物体 → 可操作信息。
示例: "你进入了一个约20米长的走廊，左侧有三扇门，右侧有落地窗。前方10米处有电梯入口。"
""",

    3: """当前 LOD 3（叙事模式）。
规则: 详细描述（400-800字）。完整场景描述，包括细节、氛围、人物。
风格: 慢速、富有表现力、叙事性。
可以主动读取文字、描述菜单、详细介绍环境。
用户处于放松/静止状态，可以接受丰富信息。"""
}
```

---

## 8. Token Optimization via LOD

利用 Gemini 3 的 `media_resolution` 参数实现 LOD 与 token 成本联动：

| LOD | media_resolution | Tokens/帧 | 节省比例 | 使用场景 |
|-----|-----------------|-----------|---------|---------|
| 1 | `low` | 70 | 94% | 快速安全扫描 |
| 2 | `medium` | 560 | 50% | 标准空间描述 |
| 3 | `high` | 1120 | 0%（基线） | 精细叙事描述 |

```python
def get_vision_config(lod: int) -> dict:
    configs = {
        1: {"media_resolution": "low", "thinking_level": "none"},
        2: {"media_resolution": "medium", "thinking_level": "low"},
        3: {"media_resolution": "high", "thinking_level": "medium"},
    }
    return configs[lod]
```

---

## 9. Competitive Landscape — Why This Matters

### 9.1 辅助产品的上下文鸿沟

| 产品 | 用户记忆 | 实时感知 | 自适应密度 | Context 融合 |
|------|---------|---------|-----------|-------------|
| Be My Eyes | 无 | 快照式 | 无 | 单源 |
| Google Lookout | 无 | 7 模式手动切换 | 无 | 单源 |
| Seeing AI | 仅人脸库 | 快照式 | 无 | 最小 |
| Aira | 人工笔记 | 实时（人工） | 人工判断 | 人工融合 |
| OrCam MyEye | 仅人脸库 | 离线 | 无 | 单源 |
| Envision | 人脸库 | 可穿戴 | 无 | 新兴 |
| Sullivan+ | 无 | 连续 | 无 | 最小 |
| **SightLine** | **三层记忆** | **连续+多传感器** | **自动 LOD 1/2/3** | **三层自动融合** |

### 9.2 学术验证

| 研究 | 发现 | 对 SightLine 的意义 |
|------|------|-------------------|
| RAVEN (ASSETS 2025) | 5/8 盲人用户要求自适应细节层级 | 用户需求已验证 |
| Say It My Way (CHI 2026) | 盲人用户需要持久偏好系统 | Long-term Context 是刚需 |
| Describe Now (DIS 2025) | 手动控制增加认知负荷 | 自动 LOD 是正确方向 |
| Beyond the Cane (ACM 2022) | 先天盲 vs 后天盲信息需求差异大 | 用户 Profile 维度设计 |
| LlamaPIE (2025) | 主动提醒提升准确率 37%→87% | 主动模式有效且不打扰 |
| EgoBlind (NUS, 2025) | 最佳 MLLM 仅 56% vs 人类 87% | 适配层比原始模型更重要 |
| BLV LVLM Preferences (2025) | 一刀切描述失败 | 个性化是必需的 |
| Augmented Cane (Science Robotics, 2021) | 认知减负提升行走速度 18% | LOD 降级有可量化的物理效益 |

### 9.3 核心壁垒

> LOD Engine 不是一个 feature，而是一个 architectural decision。一旦竞品想要跟进，需要重构整个信息传递管线。

具体来说：
1. 需要重新设计 prompt 系统（从固定到动态）
2. 需要建立传感器融合管道（从无到有）
3. 需要构建跨会话记忆系统（从无状态到有状态）
4. 需要重新训练/调整输出格式控制（从固定冗余度到自适应）

这四个改动互相依赖，不能单独实现。这就是为什么现有竞品不太可能快速跟进——它不是加一个功能，而是架构级别的重构。

---

## 10. Implementation Risks & Mitigations

| 风险 | 严重程度 | 缓解策略 |
|------|---------|---------|
| Gemini Live API 延迟 > 1s | 高 | Orchestrator 先说"让我看看..."，异步等待结果；LOD 1 不调用 Vision Agent |
| 用户隐私（连续录音+生物数据） | 高 | 明确 opt-in 流程；生物数据仅本地处理不上传原始值；仅上传语义化后的状态描述 |
| 记忆错误（LLM 幻觉记忆） | 中 | 新记忆 confidence < 0.7 不存储；关键记忆（人名、关系）需用户确认 |
| LOD 误判（该说不说/该停不停） | 中 | 用户可随时语音覆盖（"详细说说"/"停"）；A/B 测试阈值参数 |
| Token 成本失控（LOD 3 高频触发） | 中 | media_resolution 联动；LOD 3 仅在静止时触发；Gemini 3 Flash 免费覆盖 sub-agent 调用 |
| 硬件碎片化 | 低 | SEP 协议已解耦，任何遵循 JSON 格式的设备都能接入 |

---

## 11. Recommended Implementation Phases

### Phase 1: MVP Core Loop（Hackathon Target）
- [ ] Ephemeral → LOD Decision（规则引擎）
- [ ] Static User Profile（手动填写）
- [ ] Dynamic System Prompt 构建
- [ ] LOD 1/2/3 输出格式控制
- [ ] Developer Console + Telemetry 滑块

### Phase 2: Memory Layer
- [ ] Session Context Manager（空间转换、Narrative Snapshot）
- [ ] Mem0 式 Session-End 记忆提取
- [ ] Firestore 向量搜索集成
- [ ] 记忆冲突检测与合并

### Phase 3: Full Context Fusion
- [ ] 人脸识别 → 社交记忆联动
- [ ] 位置实体记忆（"公司"="腾讯B座"）
- [ ] 压力触发器学习与预防性 LOD 调整
- [ ] 用户行为模式识别（通勤路线等）

### Phase 4: Optimization
- [ ] media_resolution × LOD 联动 token 优化
- [ ] 记忆衰减与清理策略
- [ ] A/B 测试 LOD 阈值参数
- [ ] 用户反馈循环（LOD 满意度追踪）

---

## References

### Academic Papers
- RAVEN (ASSETS 2025): [arXiv 2510.06573](https://arxiv.org/abs/2510.06573)
- Say It My Way (CHI 2026): [arXiv 2602.16930](https://arxiv.org/html/2602.16930)
- Describe Now (DIS 2025): [ACM DL](https://dl.acm.org/doi/10.1145/3715336.3735685)
- Beyond the Cane (ACM TACCESS 2022): [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9491388/)
- ContextAgent (NeurIPS 2025): [arXiv 2505.14668](https://arxiv.org/html/2505.14668v1)
- ContextLLM (ACM 2025): [ACM DL](https://dl.acm.org/doi/pdf/10.1145/3708468.3711892)
- EgoBlind (NUS 2025): [arXiv 2503.08221](https://arxiv.org/abs/2503.08221)
- VIPTour/FocusFormer (npj AI 2025): [Nature](https://www.nature.com/articles/s44387-025-00006-w)
- BLV LVLM Preferences (CHI 2025): [arXiv 2502.14883](https://arxiv.org/abs/2502.14883)
- LlamaPIE (2025): [arXiv](https://arxiv.org/html/2505.04066v2)
- Augmented Cane (Science Robotics 2021): DOI: 10.1126/scirobotics.abg6594
- Pedestrian Stress (ScienceDirect 2025): Biometric sensor fusion for walking stress

### Open-Source Frameworks
- ContextAgent: [GitHub](https://github.com/openaiotlab/ContextAgent)
- Letta/MemGPT: [GitHub](https://github.com/letta-ai/letta) (38K stars)
- Mem0: [GitHub](https://github.com/mem0ai/mem0) (41K stars)
- Zep/Graphiti: [GitHub](https://github.com/getzep/graphiti) (20K stars)

### Commercial Products
- Be My Eyes: [bemyeyes.com](https://www.bemyeyes.com/)
- Google Lookout: [Google Blog](https://blog.google/outreach-and-initiatives/accessibility/)
- Microsoft Seeing AI: [seeing-ai.com](https://www.microsoft.com/en-us/ai/seeing-ai)
- Aira: [aira.io](https://aira.io/)
- OrCam MyEye 3 Pro: [orcam.com](https://www.orcam.com/)
- Envision Glasses: [letsenvision.com](https://www.letsenvision.com/)
- Sullivan+: [Google Play](https://play.google.com/store/apps/details?id=tuat.kr.sullivan)
- Meta Ray-Ban Smart Glasses: [meta.com](https://www.meta.com/ai-glasses/)

### Raw Research Data
- `../raw_research/engine/research_academic_context_aware_ai.md`
- `../raw_research/engine/research_opensource_frameworks.md`
- `../raw_research/engine/research_commercial_products.md`
