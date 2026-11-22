from __future__ import annotations

from pathlib import Path

import pytest

from mcp_connect_starter import security


@pytest.fixture(autouse=True)
def _reset_policy_cache():
    security.reset_policy_cache()
    yield
    security.reset_policy_cache()


@pytest.fixture(autouse=True)
def _default_grants(monkeypatch: pytest.MonkeyPatch) -> None:
    # Point at a scopes file that doesn't exist so tests are driven purely
    # by the `scopes=` passed to the decorator, unless a test overrides it.
    monkeypatch.setattr("mcp_connect_starter.config.SCOPES_FILE", Path("/nonexistent/scopes.yaml"))
    monkeypatch.setattr("mcp_connect_starter.config.tool_allowlist", lambda: None)


async def test_allows_call_when_scope_is_granted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mcp_connect_starter.config.granted_scopes", lambda: frozenset({"demo:read"}))

    @security.secure_tool("demo_tool", scopes=["demo:read"])
    def demo_tool(x: int) -> int:
        return x * 2

    assert await demo_tool(21) == 42


async def test_denies_call_when_scope_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mcp_connect_starter.config.granted_scopes", lambda: frozenset())

    @security.secure_tool("demo_tool", scopes=["demo:write"])
    def demo_tool() -> str:
        return "should not run"

    with pytest.raises(security.ToolAccessError):
        await demo_tool()


async def test_scopes_file_can_disable_a_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scopes_file = tmp_path / "scopes.yaml"
    scopes_file.write_text("tools:\n  demo_tool:\n    enabled: false\n    scopes: []\n")
    monkeypatch.setattr("mcp_connect_starter.config.SCOPES_FILE", scopes_file)
    monkeypatch.setattr("mcp_connect_starter.config.granted_scopes", lambda: frozenset({"demo:read"}))

    @security.secure_tool("demo_tool", scopes=["demo:read"])
    def demo_tool() -> str:
        return "should not run"

    with pytest.raises(security.ToolAccessError):
        await demo_tool()


async def test_hard_allowlist_overrides_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mcp_connect_starter.config.granted_scopes", lambda: frozenset({"demo:read"}))
    monkeypatch.setattr("mcp_connect_starter.config.tool_allowlist", lambda: frozenset({"other_tool"}))

    @security.secure_tool("demo_tool", scopes=["demo:read"])
    def demo_tool() -> str:
        return "should not run"

    with pytest.raises(security.ToolAccessError):
        await demo_tool()


async def test_output_is_redacted_even_if_connector_forgets_to(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mcp_connect_starter.config.granted_scopes", lambda: frozenset({"demo:read"}))

    @security.secure_tool("demo_tool", scopes=["demo:read"])
    def demo_tool() -> dict:
        return {"email": "someone@example.com"}

    result = await demo_tool()
    assert result["email"] == "[REDACTED_EMAIL]"


async def test_underlying_exceptions_propagate_after_being_audited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mcp_connect_starter.config.granted_scopes", lambda: frozenset({"demo:read"}))

    @security.secure_tool("demo_tool", scopes=["demo:read"])
    def demo_tool() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await demo_tool()
