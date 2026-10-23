from __future__ import annotations

from app.services.audit_service import redact_sensitive


def test_redact_sensitive_masks_credentials_recursively():
    payload = {
        "username": "teacher1",
        "password": "plain",
        "new_password": "plain2",
        "profile": {
            "api_key": "zy_secret",
            "nested_token": "jwt",
            "display_name": "Teacher",
        },
        "items": [{"secret": "s", "label": "ok"}],
    }

    redacted = redact_sensitive(payload)

    assert redacted["username"] == "teacher1"
    assert redacted["password"] == "***"
    assert redacted["new_password"] == "***"
    assert redacted["profile"]["api_key"] == "***"
    assert redacted["profile"]["nested_token"] == "***"
    assert redacted["profile"]["display_name"] == "Teacher"
    assert redacted["items"][0]["secret"] == "***"
    assert redacted["items"][0]["label"] == "ok"


def test_redact_sensitive_handles_scalars_and_empty_values():
    assert redact_sensitive(None) is None
    assert redact_sensitive("plain") == "plain"
    assert redact_sensitive({"password_changed": True}) == {"password_changed": True}
