#!/usr/bin/env python3
"""Convert a txt/markdown/docx scenario into importable scenario JSON.

Usage: python scripts/convert_scenario.py input.docx -o scenario.json --title "My scenario"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from trpg_server.scenario_importer import convert_script_to_scenario, extract_script_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a TRPG script to scenario modules")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--title", default="Imported scenario")
    args = parser.parse_args()
    scenario = convert_script_to_scenario(
        extract_script_text(args.input), {"title": args.title, "source_filename": args.input.name}
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(scenario, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"converted {args.input} -> {args.output} ({len(scenario['modules'])} modules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
