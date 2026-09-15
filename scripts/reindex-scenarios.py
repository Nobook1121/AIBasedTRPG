"""Rebuild versioned scenario knowledge indexes without changing scenarios."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from trpg_server.scenario_store import scenario_descriptor_paths, load_scenario_record
from trpg_server.agents.knowledge_base import persist_knowledge_index

def reindex_scenarios(scenarios_dir: Path) -> dict[str, int]:
    result = {"written": 0, "skipped": 0, "failed": 0}
    for descriptor in scenario_descriptor_paths(Path(scenarios_dir)):
        try:
            versions = sorted((descriptor.parent / "versions").glob("*.json"))
            if not versions: versions = [descriptor]
            for version_path in versions:
                scenario = load_scenario_record(version_path, Path(scenarios_dir))
                persist_knowledge_index(descriptor, scenario); result["written"] += 1
        except Exception:
            result["failed"] += 1
    return result

if __name__ == "__main__":
    from trpg_server.settings import SCENARIOS_DIR
    print(reindex_scenarios(SCENARIOS_DIR))
