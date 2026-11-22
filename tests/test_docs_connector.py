from __future__ import annotations

from pathlib import Path

import pytest

from mcp_connect_starter.connectors import docs_connector


@pytest.fixture(autouse=True)
def _point_at_fixture_docs(docs_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mcp_connect_starter.config.DOCS_DIR", docs_dir)


def test_search_docs_ranks_best_match_first() -> None:
    hits = docs_connector.search_docs("refund")
    assert hits
    assert hits[0].path == "refund-policy.md"
    assert hits[0].title == "Refund Policy"


def test_search_docs_returns_empty_for_no_match() -> None:
    assert docs_connector.search_docs("xyzzy_not_present_anywhere") == []


def test_search_docs_respects_limit() -> None:
    hits = docs_connector.search_docs("doc", limit=1)
    assert len(hits) <= 1


def test_search_docs_finds_nested_files() -> None:
    hits = docs_connector.search_docs("onboarding")
    assert any(h.path == "nested/onboarding.md" for h in hits)


def test_read_doc_returns_redacted_content() -> None:
    doc = docs_connector.read_doc("security.md")
    assert "415-555-0132" not in doc.content
    assert "[REDACTED_PHONE]" in doc.content
    assert doc.title == "Security"


def test_read_doc_blocks_relative_path_traversal() -> None:
    with pytest.raises(ValueError):
        docs_connector.read_doc("../../etc/passwd")


def test_read_doc_blocks_absolute_paths(tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside\nShould not be readable.\n")
    with pytest.raises(ValueError):
        docs_connector.read_doc(str(outside))


def test_read_doc_raises_for_unknown_file() -> None:
    with pytest.raises(FileNotFoundError):
        docs_connector.read_doc("does-not-exist.md")
