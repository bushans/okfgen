"""Optional LLM hooks.

okfgen is deterministic by default. These helpers are only used when the user
opts in with `--llm`. They require the `anthropic` package and an
ANTHROPIC_API_KEY; when either is missing they return None so callers fall back
to deterministic behavior. Nothing here runs during normal (default) operation.
"""

from __future__ import annotations

import os
from typing import List, Optional

# Latest capable model per the current Anthropic lineup.
_DEFAULT_MODEL = os.environ.get("OKFGEN_LLM_MODEL", "claude-opus-4-8")


def _client():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic  # type: ignore
    except Exception:
        return None
    try:
        return anthropic.Anthropic()
    except Exception:
        return None


def _complete(system: str, user: str, max_tokens: int = 1024) -> Optional[str]:
    client = _client()
    if client is None:
        return None
    try:
        msg = client.messages.create(
            model=_DEFAULT_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(getattr(b, "text", "") for b in msg.content).strip()
    except Exception:
        return None


def available() -> bool:
    return _client() is not None


def synthesize_answer(question: str, context: str) -> Optional[str]:
    """Phrase a grounded answer from retrieved OKF context (reasoning agent)."""
    system = (
        "You answer questions strictly from the provided Open Knowledge Format "
        "concept excerpts. Cite concept titles inline. If the context is "
        "insufficient, say so. Be concise."
    )
    user = f"Question: {question}\n\nContext:\n{context}"
    return _complete(system, user, max_tokens=700)


def enrich_description(title: str, ctype: str, body: str, doc_context: str = "") -> Optional[str]:
    """Write a richer one-sentence description for a concept (enrichment agent)."""
    system = (
        "You write a single, precise sentence describing a data/knowledge "
        "concept for a catalog. No preamble, no markdown, one sentence."
    )
    user = f"Concept type: {ctype}\nTitle: {title}\nBody:\n{body[:2000]}"
    if doc_context:
        user += f"\n\nAuthoritative documentation:\n{doc_context[:2000]}"
    return _complete(system, user, max_tokens=120)
