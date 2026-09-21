"""Import versioned JSON knowledge indexes into the embedded vector store."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from trpg_server.agents.vector_migration import migrate_json_indexes, migrate_qdrant_store  # noqa: E402
from trpg_server.agents.vector_store import EmbeddedVectorStore, QdrantVectorStore  # noqa: E402
from trpg_server.settings import EMBEDDED_VECTOR_DB_PATH, SCENARIOS_DIR  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios-dir", type=Path, default=SCENARIOS_DIR)
    parser.add_argument("--vector-db-dir", type=Path, default=EMBEDDED_VECTOR_DB_PATH)
    parser.add_argument("--qdrant-url", default="")
    parser.add_argument("--qdrant-path", type=Path)
    args = parser.parse_args()
    target = EmbeddedVectorStore(args.vector_db_dir)
    if args.qdrant_url or args.qdrant_path:
        source = QdrantVectorStore(url=args.qdrant_url or None, path=str(args.qdrant_path) if args.qdrant_path else None)
        result = migrate_qdrant_store(source, target)
    else:
        result = migrate_json_indexes(args.scenarios_dir, target)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
