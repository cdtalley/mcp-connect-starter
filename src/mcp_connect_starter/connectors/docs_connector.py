"""Docs/knowledge-base connector: search and read a folder of markdown files.

Swap `config.DOCS_DIR` (via `MCP_CONNECT_DOCS_DIR`) for a folder synced from
Confluence, Notion, or a Google Drive export, and this connector works
unchanged -- it only assumes a directory of `.md` files.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel

from mcp_connect_starter import config
from mcp_connect_starter.redaction import redact_text

_WORD_RE = re.compile(r"\w+")


class DocHit(BaseModel):
    path: str
    title: str
    score: int
    snippet: str


class DocContent(BaseModel):
    path: str
    title: str
    content: str


def _docs_root() -> Path:
    return config.DOCS_DIR


def _iter_markdown_files(root: Path) -> Iterator[Path]:
    if not root.exists():
        return
    yield from sorted(root.rglob("*.md"))


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _make_snippet(text: str, terms: list[str], context_chars: int = 140) -> str:
    lower = text.lower()
    positions = [lower.find(term) for term in terms]
    positions = [p for p in positions if p != -1]
    first_idx = min(positions) if positions else 0
    start = max(0, first_idx - context_chars // 3)
    end = min(len(text), first_idx + context_chars)
    snippet = " ".join(text[start:end].split())
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return redact_text(f"{prefix}{snippet}{suffix}")


def search_docs(query: str, limit: int = 5) -> list[DocHit]:
    """Rank bundled markdown docs by term-frequency match against `query`."""
    root = _docs_root()
    terms = [t.lower() for t in _WORD_RE.findall(query)]
    if not terms:
        return []

    hits: list[DocHit] = []
    for path in _iter_markdown_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        lower = text.lower()
        score = sum(lower.count(term) for term in terms)
        if score == 0:
            continue
        hits.append(
            DocHit(
                path=str(path.relative_to(root)),
                title=_extract_title(text, fallback=path.stem),
                score=score,
                snippet=_make_snippet(text, terms),
            )
        )

    hits.sort(key=lambda hit: hit.score, reverse=True)
    return hits[: max(0, limit)]


def _resolve_within_docs(rel_path: str) -> Path:
    if Path(rel_path).is_absolute():
        raise ValueError("Document path must be relative to the docs root, not absolute.")

    root = _docs_root().resolve()
    candidate = (root / rel_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"'{rel_path}' escapes the docs directory.")
    if not candidate.is_file():
        raise FileNotFoundError(f"No such document: '{rel_path}'.")
    return candidate


def read_doc(path: str) -> DocContent:
    """Read one markdown document by its path relative to the docs root."""
    resolved = _resolve_within_docs(path)
    text = resolved.read_text(encoding="utf-8", errors="replace")
    return DocContent(
        path=str(resolved.relative_to(_docs_root().resolve())),
        title=_extract_title(text, fallback=resolved.stem),
        content=redact_text(text),
    )
