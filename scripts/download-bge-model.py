#!/usr/bin/env python3
"""Download the recommended local BGE embedding model.

The default destination matches ``AI_TRPG_LOCAL_EMBEDDING_MODEL_PATH``.  The
script prefers Hugging Face Hub and can fall back to ModelScope, which is useful
on networks where Hugging Face is slow or unavailable.
"""
from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"
DEFAULT_DEST = Path("data/runtime/models/embedding/bge-small-zh-v1.5")


def download(model: str, destination: Path, source: str = "auto") -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    if source in {"auto", "huggingface"}:
        try:
            from huggingface_hub import snapshot_download

            snapshot_download(repo_id=model, local_dir=str(destination))
            return destination
        except Exception as exc:  # pragma: no cover - depends on network/package
            errors.append(f"Hugging Face: {exc}")
            if source == "huggingface":
                raise RuntimeError("Unable to download model from Hugging Face: " + str(exc)) from exc
    if source in {"auto", "modelscope"}:
        try:
            from modelscope import snapshot_download

            snapshot_download(model, local_dir=str(destination))
            return destination
        except Exception as exc:  # pragma: no cover - depends on network/package
            errors.append(f"ModelScope: {exc}")
    raise RuntimeError("Unable to download model. Install huggingface_hub or modelscope. " + " | ".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a local BGE embedding model")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model repository id")
    parser.add_argument("--destination", type=Path, default=DEFAULT_DEST, help="Local model directory")
    parser.add_argument("--source", choices=("auto", "huggingface", "modelscope"), default="auto")
    args = parser.parse_args()
    path = download(args.model, args.destination, args.source)
    print(f"Embedding model downloaded: {args.model}")
    print(f"Local path: {path.resolve()}")
    print("Set AI_TRPG_LOCAL_EMBEDDING_MODEL_PATH to this path if you use a custom destination.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
