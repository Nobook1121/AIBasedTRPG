from pathlib import Path

from trpg_server.agents.embedding_provider import HashedTokenEmbedding, select_embedding_provider


def test_embedding_provider_uses_hashed_fallback_without_local_or_remote_config(tmp_path):
    provider = select_embedding_provider(local_model_path=tmp_path / "missing", dimensions=32)
    assert isinstance(provider, HashedTokenEmbedding)
    assert len(provider.embed(["灯塔"])[0]) == 32


def test_embedding_provider_prefers_existing_local_model_directory(tmp_path):
    model = tmp_path / "bge-small-zh-v1.5"
    model.mkdir()
    provider = select_embedding_provider(local_model_path=model, dimensions=512)
    assert provider.__class__.__name__ == "LocalSentenceTransformerEmbedding"


def test_embedding_providers_expose_configuration_and_dimensions(tmp_path):
    fallback = HashedTokenEmbedding(32)
    assert fallback.configured is True
    assert fallback.dimensions == 32

    model = tmp_path / "model"
    model.mkdir()
    local = select_embedding_provider(local_model_path=model, dimensions=512)
    assert local.configured is True
    assert local.dimensions is None
