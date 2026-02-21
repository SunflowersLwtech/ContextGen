# Google ADK (Agent Development Kit) Research Report for SightLine

> **Research Date**: 2026-02-21
> **Source**: Parallel research agent - Google ADK multi-agent framework

---

## 1. Google ADK Architecture

### Overview

Google's [Agent Development Kit (ADK)](https://google.github.io/adk-docs/) is an open-source, code-first Python framework launched at Google Cloud NEXT 2025. It is built on the same foundation powering Google's own applications like Agentspace. The core repository is at [google/adk-python](https://github.com/google/adk-python).

Install with:
```bash
pip install google-adk
```

### Agent Types

ADK provides three categories of agents:

| Category | Types | LLM-Powered? | Use Case |
|---|---|---|---|
| **LLM Agents** | `LlmAgent` (alias: `Agent`) | Yes | Reasoning, tool calling, routing |
| **Workflow Agents** | `SequentialAgent`, `ParallelAgent`, `LoopAgent` | No (deterministic) | Predictable orchestration pipelines |
| **Custom Agents** | Subclass `BaseAgent` | Optional | Full control over execution logic |

### Defining and Orchestrating Multiple Sub-Agents

The fundamental pattern is **hierarchical composition** via the `sub_agents` parameter:

```python
from google.adk.agents import LlmAgent

# --- Specialized Sub-Agents ---
scene_description_agent = LlmAgent(
    name="SceneDescriber",
    model="gemini-2.5-pro",
    description="Describes visual scenes in detail for visually impaired users.",
    instruction="""You are a visual scene describer...""",
    output_key="scene_description",
)

navigation_agent = LlmAgent(
    name="NavigationAssistant",
    model="gemini-2.5-flash",
    description="Provides real-time navigation guidance and obstacle warnings.",
    instruction="""You are a navigation assistant...""",
    output_key="navigation_guidance",
)

text_reader_agent = LlmAgent(
    name="TextReader",
    model="gemini-2.5-flash",
    description="Reads and interprets text from images.",
    instruction="""You are an OCR and text interpretation agent...""",
    output_key="text_content",
)

# --- Orchestrator ---
sightline_coordinator = LlmAgent(
    name="SightLineCoordinator",
    model="gemini-2.5-flash",
    description="Main coordinator that routes user requests to specialized vision agents.",
    instruction="""Route based on intent...""",
    sub_agents=[scene_description_agent, navigation_agent, text_reader_agent],
)
```

### How Agent Transfer / Routing Works

When `sub_agents` is defined on an `LlmAgent`, ADK automatically enables **LLM-driven dynamic routing**. The coordinator's LLM generates a `transfer_to_agent` function call with the target agent's name. The LLM makes routing decisions based on:
- Each sub-agent's `description` field
- The coordinator's `instruction`
- The conversation context

### Agent Communication: Shared State

Agents communicate via **shared session state**:

```python
# Agent A writes to state via output_key="scene_description"
# Agent B reads it from state:
agent_b = LlmAgent(
    name="Summarizer",
    instruction="Summarize the scene: {scene_description}",
)

# Or in a tool function:
def my_tool(tool_context):
    scene = tool_context.state.get("scene_description", "")
    tool_context.state["processed_result"] = process(scene)
```

**State key prefixes** control persistence scope:
- No prefix: temporary, current invocation only
- `temp:` prefix: temporary, cleared between turns
- `user:` prefix: persists across all sessions for that user
- `app:` prefix: persists across all sessions for all users

### Workflow Agent Patterns

```python
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent

# --- PARALLEL: Run vision analysis tasks concurrently ---
parallel_analysis = ParallelAgent(
    name="ParallelVisionAnalysis",
    sub_agents=[scene_description_agent, navigation_agent, text_reader_agent],
)

# --- SEQUENTIAL: Analyze then synthesize ---
analyze_and_respond = SequentialAgent(
    name="AnalyzeThenRespond",
    sub_agents=[parallel_analysis, synthesis_agent],
)

# --- LOOP: Iterative refinement ---
refinement_loop = LoopAgent(
    name="DescriptionRefinement",
    sub_agents=[describe_agent, critique_agent],
    max_iterations=3,
)
```

### Custom Agent (Full Orchestration Control)

```python
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing import AsyncGenerator

class SightLineOrchestrator(BaseAgent):
    scene_agent: LlmAgent
    nav_agent: LlmAgent
    text_agent: LlmAgent

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # Priority 1: Always check for navigation hazards
        async for event in self.nav_agent.run_async(ctx):
            yield event

        nav_result = ctx.session.state.get("navigation_guidance", "")
        if "hazard" in nav_result.lower():
            return  # Urgent: stop here

        # Priority 2: Route based on user intent
        if self._is_text_request(ctx.user_content):
            async for event in self.text_agent.run_async(ctx):
                yield event
        else:
            async for event in self.scene_agent.run_async(ctx):
                yield event
```

---

## 2. ADK Features

### Function Calling / Tool Definition

```python
def get_location_info(latitude: float, longitude: float, tool_context=None) -> dict:
    """Get information about a location."""
    result = {"address": "123 Main St", "nearby": ["crosswalk", "bus stop"]}
    if tool_context:
        tool_context.state["current_location"] = result
    return result

nav_agent = LlmAgent(
    name="Navigator",
    model="gemini-2.5-flash",
    instruction="Help users navigate safely.",
    tools=[get_location_info],
)
```

### Session Management and State Persistence

```python
from google.adk.sessions import InMemorySessionService, DatabaseSessionService
from google.adk.runners import Runner

session_service = InMemorySessionService()
runner = Runner(agent=sightline_coordinator, app_name="sightline", session_service=session_service)

session = await session_service.create_session(
    app_name="sightline",
    user_id="user_123",
    state={"user:preferences": {"verbosity": "detailed"}},
)
```

### Error Handling and Callbacks

```python
def safety_check_callback(callback_context):
    if callback_context.state.get("emergency_mode"):
        return adk_types.Content(
            role="model",
            parts=[adk_types.Part.from_text("Emergency mode active.")]
        )
    return None

agent = LlmAgent(
    name="SafeAgent",
    before_agent_callback=safety_check_callback,
)
```

---

## 3. ADK + Gemini Live API Integration

### Bidirectional Streaming (Bidi-Streaming)

ADK provides **native bidi-streaming** built on the Gemini Live API:

- **`LiveRequestQueue`**: asyncio-based FIFO buffer that multiplexes audio/video/text inputs
- **`run_live()`**: streaming equivalent of `run_async()`
- **Voice Activity Detection (VAD)**: automatic speech start/stop detection
- **Transcription events**: automatic speech-to-text for agent transfers

```python
from fastapi import FastAPI, WebSocket
app = FastAPI()

@app.websocket("/ws/sightline")
async def sightline_stream(websocket: WebSocket):
    await websocket.accept()
    session = await runner.session_service.create_session(app_name="sightline", user_id="user_1")

    live_request_queue = runner.create_live_request_queue()
    live_events = runner.run_live(
        session_id=session.id, user_id="user_1",
        live_request_queue=live_request_queue,
    )

    async def receive_from_client():
        while True:
            data = await websocket.receive_bytes()
            live_request_queue.send_realtime(data)

    async def send_to_client():
        async for event in live_events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'inline_data'):
                        await websocket.send_bytes(part.inline_data.data)

    await asyncio.gather(receive_from_client(), send_to_client())
```

---

## 4. ADK Deployment on Cloud Run

### CLI Deployment (Simplest)

```bash
adk deploy cloud_run \
  --project=$PROJECT_ID \
  --region=us-central1 \
  --service_name=sightline-agent \
  --with_ui \
  ./sightline_app
```

### Custom Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["adk", "api_server", "--port", "8080", "sightline_app"]
```

### Scaling Considerations

- `--min-instances 1`: avoid cold starts
- `--memory 2Gi`: streaming needs memory
- `--cpu 2`: parallel agents benefit from more CPU
- `--timeout 300`: long-lived streaming sessions
- Cloud Run supports WebSocket natively

---

## 5. Alternatives Comparison

### ADK vs LangGraph

| Dimension | Google ADK | LangGraph |
|---|---|---|
| Gemini Live API | **Native** | No support |
| Bidi-streaming | **Built-in** | No |
| Multi-Agent Routing | Automatic `transfer_to_agent` | Manual graph edges |
| Deployment | One-command Cloud Run | Self-hosted |
| Model Support | Gemini-optimized + 100+ via LiteLLM | Model-agnostic |

### ADK vs CrewAI

| Dimension | Google ADK | CrewAI |
|---|---|---|
| Real-time streaming | **Native** | None |
| Design | Code-first engineering | Role-based collaboration |
| Use case | Real-time multimodal | Batch task workflows |

**Verdict**: ADK wins decisively for SightLine due to native Gemini Live bidi-streaming.

---

## Sources

- [ADK Official Documentation](https://google.github.io/adk-docs/)
- [google/adk-python GitHub](https://github.com/google/adk-python)
- [google/adk-samples](https://github.com/google/adk-samples)
- [Multi-Agent Systems](https://google.github.io/adk-docs/agents/multi-agents/)
- [Bidi-Streaming](https://google.github.io/adk-docs/streaming/)
- [Cloud Run Deployment](https://google.github.io/adk-docs/deploy/cloud-run/)
- [Session & State](https://google.github.io/adk-docs/sessions/state/)
- [Callbacks](https://google.github.io/adk-docs/callbacks/)
- [ADK vs LangGraph (ZenML)](https://www.zenml.io/blog/google-adk-vs-langgraph)
- [ADK Bidi-Streaming Visual Guide](https://medium.com/google-cloud/adk-bidi-streaming-a-visual-guide-to-real-time-multimodal-ai-agent-development-62dd08c81399)
