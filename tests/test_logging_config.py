from trpg_server.logging_config import redact_sensitive


def test_redact_sensitive_masks_known_secret_keys():
    payload = {
        "api_key": "secret",
        "auth_token": "token",
        "password": "pass",
        "name": "public",
    }

    assert redact_sensitive(payload) == {
        "api_key": "***",
        "auth_token": "***",
        "password": "***",
        "name": "public",
    }
