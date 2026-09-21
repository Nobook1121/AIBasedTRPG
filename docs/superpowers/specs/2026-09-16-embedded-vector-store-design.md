# Embedded Vector Store Design

## Goal

Make the application runnable without Qdrant or Docker by providing a persistent embedded vector store, while preserving the existing knowledge-card retrieval behavior and keeping Qdrant as an optional backend.

## Context and constraints

- `KnowledgeBaseService` already performs scenario/version/scene/spoiler hard filtering and lexical-plus-vector score fusion.
- Existing JSON knowledge indexes remain human-readable backups at `data/scenarios/scenario-<id>/knowledge-index/<version>.json`.
- Default startup must require no external service. Qdrant is enabled only when `AI_TRPG_VECTOR_BACKEND=qdrant` or `AI_TRPG_VECTOR_DB_URL` is set.
- Existing import progress stages and API response shapes must remain unchanged.
- Embedded data lives under `data/runtime/vector-db/embedded/`; the existing Qdrant path remains `data/runtime/vector-db/qdrant/`.

## Design

### Storage contract

`backend/trpg_server/agents/vector_store.py` defines a backend-neutral `VectorStore` contract with `upsert(chunks)`, `delete(ids)`, `delete_by_filter(filter)`, `query(vector, filter, top_k)`, `count(filter=None)`, and `health()`.

The contract accepts `KnowledgeChunk`-like mappings. Results use the existing shape `{id, score, payload}` so `KnowledgeBaseService` can keep its score-fusion logic.

### Embedded backend

`EmbeddedVectorStore` stores one row per chunk in SQLite at `data/runtime/vector-db/embedded/vectors.sqlite3`. It creates the schema lazily, serializes vectors as compact JSON, indexes common metadata fields, and uses a process lock for writes. Queries apply SQL metadata filters before calculating cosine similarity in Python, then return the top `k` results. This avoids native extensions and external services while supporting the expected single-machine scale.

### Optional Qdrant backend

`QdrantVectorStore` keeps its current optional import behavior but implements the same contract. It maps chunk metadata to Qdrant payloads and translates filters/results at the adapter boundary. It is never imported as a required dependency during default startup.

### Selection and lifecycle

`create_vector_store()` selects Qdrant only for an explicit `qdrant` backend or non-empty URL; otherwise it returns `EmbeddedVectorStore`. The app factory creates the selected store and initializes its schema. Scenario indexing upserts embedded/Qdrant vectors and still writes the JSON backup. A migration helper imports all versioned JSON indexes idempotently into the selected embedded store.

### Compatibility

`KnowledgeBaseService` continues to perform hard filtering before score fusion. It uses `query()` when available and accepts the legacy `search()` adapter shape during transition. Existing fake stores in tests remain valid. Embedding fallback behavior is unchanged.

## Testing

- Contract tests cover upsert, metadata filtering, version/scene isolation, deletion, counting, and health.
- Knowledge-base tests verify the embedded store is queried only after hard filters and preserves lexical/vector score components.
- Selection tests verify default embedded behavior, explicit Qdrant behavior, and URL compatibility.
- Migration tests verify JSON indexes import idempotently and preserve metadata.
- Existing `pytest`, frontend typecheck/build, `scripts/verify.ps1`, and `git diff --check` remain required gates.

