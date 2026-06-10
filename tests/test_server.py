import logging

import server


def test_log_listening_addresses_includes_all_discovered_addresses(caplog, monkeypatch):
    monkeypatch.setattr(
        server,
        "get_local_ipv4_addresses",
        lambda: ["127.0.0.1", "192.168.192.31", "192.168.0.169"],
    )

    with caplog.at_level(logging.INFO):
        server._log_listening_addresses("ignored", 8099)

    messages = [record.message for record in caplog.records]
    assert any("listening on http://127.0.0.1:8099" in message for message in messages)
    assert any("listening on http://192.168.192.31:8099" in message for message in messages)
    assert any("listening on http://192.168.0.169:8099" in message for message in messages)
