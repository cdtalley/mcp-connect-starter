from __future__ import annotations

from pydantic import BaseModel

from mcp_connect_starter.redaction import redact_any, redact_text


def test_redacts_email():
    text = redact_text("contact me at jane.doe@example.com please")
    assert "jane.doe@example.com" not in text
    assert "[REDACTED_EMAIL]" in text


def test_redacts_ssn():
    text = redact_text("SSN on file: 123-45-6789")
    assert "123-45-6789" not in text
    assert "[REDACTED_SSN]" in text


def test_redacts_phone_number():
    text = redact_text("call 415-555-0132 tomorrow")
    assert "415-555-0132" not in text
    assert "[REDACTED_PHONE]" in text


def test_redacts_credit_card_number_that_passes_luhn():
    text = redact_text("card on file: 4111111111111111")
    assert "4111111111111111" not in text
    assert "[REDACTED_CARD]" in text


def test_does_not_redact_long_number_that_fails_luhn():
    # Same length as a card number but fails the Luhn checksum, so it is
    # treated as an ordinary identifier rather than PII.
    text = redact_text("order id: 1234567890123456")
    assert "1234567890123456" in text


def test_redacts_secret_like_key_value_pairs():
    text = redact_text("api_key=sk-ABCDEF1234567890")
    assert "sk-ABCDEF1234567890" not in text
    assert "api_key=[REDACTED_SECRET]" in text


def test_redacts_aws_access_key():
    text = redact_text("found AKIAABCDEFGHIJKLMNOP in the logs")
    assert "AKIAABCDEFGHIJKLMNOP" not in text
    assert "[REDACTED_AWS_KEY]" in text


def test_leaves_clean_text_untouched():
    text = "This is a perfectly ordinary sentence with no PII at all."
    assert redact_text(text) == text


def test_empty_string_is_noop():
    assert redact_text("") == ""


def test_redact_any_recurses_into_nested_dicts_and_lists():
    data = {"user": {"email": "a@b.com", "notes": ["call 415-555-0132 now"]}}
    redacted = redact_any(data)
    assert redacted["user"]["email"] == "[REDACTED_EMAIL]"
    assert "415-555-0132" not in redacted["user"]["notes"][0]
    assert "[REDACTED_PHONE]" in redacted["user"]["notes"][0]


def test_redact_any_preserves_non_string_types():
    data = {"count": 3, "active": True, "ratio": 1.5, "nothing": None}
    assert redact_any(data) == data


def test_redact_any_handles_pydantic_models():
    class Note(BaseModel):
        body: str
        count: int

    note = Note(body="email me at test@example.com", count=2)
    redacted = redact_any(note)

    assert isinstance(redacted, Note)
    assert "test@example.com" not in redacted.body
    assert redacted.count == 2


def test_redact_any_handles_list_of_models():
    class Note(BaseModel):
        body: str

    notes = [Note(body="SSN 123-45-6789"), Note(body="nothing sensitive")]
    redacted = redact_any(notes)

    assert all(isinstance(n, Note) for n in redacted)
    assert "123-45-6789" not in redacted[0].body
    assert redacted[1].body == "nothing sensitive"
