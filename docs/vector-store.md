# Vector storage

The application defaults to `EmbeddedVectorStore`, a standard-library SQLite backend at `data/runtime/vector-db/embedded/vectors.sqlite3`. Startup creates the directory and schema automatically. Knowledge-card JSON indexes remain under each scenario's `knowledge-index/<version>.json` directory as a readable backup.

```text
room request -> version/scene/spoiler hard filters -> VectorStore.query -> lexical + vector fusion -> prompt
                                  |                         |
                      knowledge-index/<version>.json   embedded SQLite (default) / Qdrant (optional)
```

To use Qdrant instead, install `requirements-vector-qdrant.txt` and set:

```text
AI_TRPG_VECTOR_BACKEND=qdrant
AI_TRPG_VECTOR_DB_URL=http://127.0.0.1:6333
```

`AI_TRPG_VECTOR_DB_URL` remains backward compatible: when no explicit backend is set, a non-empty URL selects Qdrant. Docker is optional; the Qdrant client can also use its local persistence path at `data/runtime/vector-db/qdrant/`.

To import existing JSON indexes into the embedded store:

```powershell
python scripts/migrate-vector-store.py
```

The command is idempotent and does not remove source JSON files or Qdrant data. To copy an existing Qdrant deployment instead, add `--qdrant-url http://127.0.0.1:6333` (or `--qdrant-path data/runtime/vector-db/qdrant`); that mode requires `requirements-vector-qdrant.txt`.
