from trpg_server.agents.cache import (
    ExactResponseCache,
    ProviderPrefixCache,
    SemanticCache,
)


def test_provider_prefix_cache_tracks_ttl_and_hit():
    cache = ProviderPrefixCache(default_ttl=60)
    assert cache.lookup("scenario:key") is False
    assert cache.lookup("scenario:key") is True
    assert cache.stats("scenario:key")["hits"] == 1


def test_exact_cache_reuses_value_until_expiry():
    cache = ExactResponseCache(default_ttl=60)
    cache.set("rules", {"text": "result"})
    assert cache.get("rules") == {"text": "result"}
    assert cache.get("missing") is None


def test_semantic_cache_is_bound_to_state_fingerprint():
    cache = SemanticCache(default_ttl=60)
    cache.set("open door", {"active_scene_id": "scene-1"}, "result-1")
    assert cache.get("open door", {"active_scene_id": "scene-1"}) == "result-1"
    assert cache.get("open door", {"active_scene_id": "scene-2"}) is None

