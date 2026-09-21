from pathlib import Path

from trpg_server.agents.vector_store import EmbeddedVectorStore
from trpg_server.agents.vector_migration import migrate_json_indexes


def test_json_indexes_migrate_idempotently(tmp_path: Path):
    scenarios = tmp_path / "scenarios" / "scenario-case-1" / "knowledge-index"
    scenarios.mkdir(parents=True)
    (scenarios / "1.json").write_text(
        '[{"scenario_id":"case-1","scenario_version":"1","scene_id":"scene-1","card_type":"scene","visibility":"player_visible","spoiler_level":0,"unlock_condition":null,"text":"brass key","chunk_id":"scene-1","embedding":[1.0,0.0],"source_ref":null,"metadata":{}}]',
        encoding="utf-8",
    )
    store = EmbeddedVectorStore(tmp_path / "vectors")

    first = migrate_json_indexes(scenarios.parent.parent, store)
    second = migrate_json_indexes(scenarios.parent.parent, store)

    assert first["chunks"] == 1
    assert second["chunks"] == 1
    assert store.count({"scenario_id": "case-1", "scenario_version": "1"}) == 1

