# RAG & Long-Term Memory System Research for SightLine

> **Research Date**: 2026-02-21
> **Source**: Parallel research agent - RAG and context memory systems

---

## 1. Google Vertex AI RAG Engine

- Fully managed, GA service: parsing, chunking, embedding, vector storage, retrieval
- Spanner-backed vector database
- Creates `RagCorpus` (personal knowledge base), imports PDF/HTML/Google Docs
- **Setup Complexity: 4/5** -- heavy for hackathon
- **Hackathon Suitability: MODERATE** -- too complex for 23-day sprint

---

## 2. Firestore as a Vector Store -- RECOMMENDED

### Native KNN Vector Search (GA)

| Feature | Value |
|---------|-------|
| Max dimensions | 2,048 |
| Distance measures | COSINE, EUCLIDEAN, DOT_PRODUCT |
| Index type | Flat (exact KNN) |
| Free tier | 50K reads, 20K writes/day |

```python
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
import google.generativeai as genai

db = firestore.Client(project="sightline-project")

def store_user_memory(user_id, memory_text, memory_type):
    embedding = genai.embed_content(
        model="models/text-embedding-004", content=memory_text
    )['embedding']
    db.collection("users").document(user_id)\
      .collection("memories").document().set({
        "text": memory_text,
        "type": memory_type,
        "embedding": Vector(embedding),
        "created_at": firestore.SERVER_TIMESTAMP,
    })

def retrieve_memories(user_id, query, limit=5):
    query_vec = genai.embed_content(
        model="models/text-embedding-004", content=query
    )['embedding']
    return db.collection("users").document(user_id)\
             .collection("memories").find_nearest(
        vector_field="embedding",
        query_vector=Vector(query_vec),
        distance_measure=DistanceMeasure.COSINE,
        limit=limit,
    )
```

### Vector Index Creation (gcloud CLI)

```bash
gcloud firestore indexes composite create \
  --collection-group=memories \
  --query-scope=COLLECTION \
  --field-config field-path=embedding,vector-config='{"dimension":"768","flat":"{}"}'
```

---

## 3. Lightweight Vector Databases (Alternatives)

| Feature | ChromaDB | Pinecone | Weaviate |
|---------|----------|----------|----------|
| Setup | 1/5 | 2/5 | 3/5 |
| Hosting | In-process | Managed | Self-hosted |
| Free Tier | Unlimited local | 2GB | Open source |
| Latency | <10ms | <50ms | <100ms |

**Recommendation**: Use Firestore native vector search. No separate DB needed.

---

## 4. 3-Tier Memory Architecture

```
TIER 1: EPHEMERAL (ms~s)
  - Current conversation context
  - Active scene description
  - Lives in: Gemini context window / ADK session state
  - TTL: Current turn only

TIER 2: SESSION (min~hr)
  - Full conversation history
  - Objects/people identified this session
  - Lives in: ADK Session State (in-memory)
  - TTL: Duration of session

TIER 3: LONG-TERM (permanent)
  - User preferences, frequent locations
  - Stress triggers, behavior patterns
  - Past conversation summaries
  - Lives in: Firestore (with vector embeddings)
  - TTL: Permanent (with decay)
```

### ADK Built-in Memory

- **Session State**: key-value pairs, `user:` prefix persists across sessions
- **Memory Service**: `InMemoryMemoryService` (dev) or `VertexAiMemoryBankService` (production)

### Memory Consolidation (End of Session)

```python
# Use Gemini Flash to extract important facts from conversation
# Categories: preference, location, behavior, stress_trigger, routine
# Store with embeddings in Firestore
```

### Relevance Scoring

```python
relevance = (
    0.4 * query_similarity +
    0.25 * recency_score +      # exponential decay, 30-day half-life
    0.15 * frequency_score +     # logarithmic access count
    0.2 * importance_score       # explicit rating
)
```

---

## 5. Gemini Context Caching

| Feature | Implicit | Explicit |
|---------|----------|----------|
| Setup | Automatic | Manual cache creation |
| Cost savings | Up to 90% | Guaranteed 87.5-90% |
| Min tokens | N/A | 2,048 |
| Storage cost | None | Per-hour |

```python
cache = client.caches.create(
    model="gemini-2.5-flash",
    config=CreateCachedContentConfig(
        display_name="sightline-context",
        system_instruction=system_prompt,
        ttl="3600s",
    )
)
# Cached input: Flash $0.019/1M (87.5% savings), Pro $0.125/1M (90% savings)
```

---

## 6. Google Search Grounding

```python
# Direct API
tools = [types.Tool(google_search=types.GoogleSearch())]

# With ADK
from google.adk.tools import google_search
agent = Agent(tools=[google_search])

# In Live API
tools = [{"google_search": {}}]
```

Works in Gemini Live API. Provides citations and source URLs.

---

## Recommended Stack for Hackathon

| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| 1 | Google Search Grounding | 1 hour | High |
| 2 | Firestore vector search | 1 day | High |
| 3 | ADK Session State | 2 hours | High |
| 4 | Memory consolidation | 1 day | Medium |
| 5 | Context caching | 2 hours | Medium |

### What to Skip
- Vertex AI RAG Engine (too complex)
- Pinecone/Weaviate/ChromaDB (unnecessary)
- Vertex AI Memory Bank (nice-to-have)

---

## Sources

- [Firestore Vector Search](https://firebase.google.com/docs/firestore/vector-search)
- [Vertex AI RAG Engine](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/rag-overview)
- [ADK Memory Docs](https://google.github.io/adk-docs/sessions/memory/)
- [Gemini Context Caching](https://ai.google.dev/gemini-api/docs/caching)
- [Google Search Grounding](https://ai.google.dev/gemini-api/docs/google-search)
- [ADK Grounding](https://google.github.io/adk-docs/grounding/google_search_grounding/)
