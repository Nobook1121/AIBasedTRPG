from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_TS_ROOTS = [
    PROJECT_ROOT / "frontend" / "src" / "js",
    PROJECT_ROOT / "frontend" / "src" / "tools",
]
FRONTEND_TSCONFIG = PROJECT_ROOT / "tsconfig.frontend.json"
SCENARIO_MODEL_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "models" / "ScenarioModel.ts"
NETWORK_TS = PROJECT_ROOT / "frontend" / "src" / "js" / "network.ts"


def _ts_sources():
    for root in FRONTEND_TS_ROOTS:
        yield from root.rglob("*.ts")


def _read(path):
    return path.read_text(encoding="utf-8")


def test_frontend_sources_do_not_disable_type_checking_or_use_explicit_any():
    violations = []
    for source_path in _ts_sources():
        source = _read(source_path)
        if "@ts-nocheck" in source:
            violations.append(f"{source_path.relative_to(PROJECT_ROOT)} contains @ts-nocheck")
        if " any" in source or ":any" in source or "<any" in source or "as any" in source:
            violations.append(f"{source_path.relative_to(PROJECT_ROOT)} contains explicit any")

    assert violations == []


def test_frontend_build_config_keeps_strict_type_checking_enabled():
    config_source = _read(FRONTEND_TSCONFIG)

    assert '"strict": false' not in config_source
    assert '"noImplicitAny": false' not in config_source


def test_scenario_model_does_not_embed_default_scenarios_in_frontend():
    source = _read(SCENARIO_MODEL_TS)

    assert "loadDefaultScenarios" not in source
    assert "古宅奇案" not in source
    assert "星际探索" not in source


def test_network_status_refreshes_are_awaited():
    source = _read(NETWORK_TS)

    assert "await loadPenetrationConfig();" in source
    assert source.count("await updateNetworkStatus();") >= 2
