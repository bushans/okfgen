"""Search-index consumer: a full-text index over an OKF bundle.

Demonstrates the "search index" consumer from the OKF blog post. Builds a small
inverted index with TF-IDF-ish ranking using only the standard library, so any
bundle becomes searchable without a database or external service.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from .consumer import LoadedBundle, LoadedConcept, load_bundle

_TOKEN_RE = re.compile(r"[a-z0-9_]+")

# Field weights: a term in the title matters more than one buried in the body.
_FIELD_WEIGHTS = {"title": 5.0, "tags": 4.0, "type": 3.0, "description": 3.0, "body": 1.0}


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


@dataclass
class SearchHit:
    concept: LoadedConcept
    score: float
    snippet: str


class SearchIndex:
    def __init__(self, bundle: LoadedBundle):
        self.bundle = bundle
        self._doc_terms: Dict[str, Dict[str, float]] = {}  # path -> term -> weighted tf
        self._df: Dict[str, int] = {}  # term -> document frequency
        self._build()

    def _build(self) -> None:
        for c in self.bundle.concepts:
            weighted: Dict[str, float] = {}
            fields = {
                "title": c.title,
                "tags": " ".join(c.tags),
                "type": c.type,
                "description": c.description,
                "body": c.body,
            }
            for field_name, value in fields.items():
                w = _FIELD_WEIGHTS[field_name]
                for tok in _tokens(value):
                    weighted[tok] = weighted.get(tok, 0.0) + w
            self._doc_terms[c.path] = weighted
            for tok in weighted:
                self._df[tok] = self._df.get(tok, 0) + 1

    def _idf(self, term: str) -> float:
        n = len(self.bundle.concepts)
        df = self._df.get(term, 0)
        if df == 0:
            return 0.0
        return math.log(1 + n / df)

    def search(self, query: str, limit: int = 10) -> List[SearchHit]:
        q_terms = _tokens(query)
        if not q_terms:
            return []
        hits: List[SearchHit] = []
        for c in self.bundle.concepts:
            weighted = self._doc_terms[c.path]
            score = 0.0
            for term in q_terms:
                tf = weighted.get(term, 0.0)
                if tf:
                    score += tf * self._idf(term)
            if score > 0:
                hits.append(SearchHit(concept=c, score=score, snippet=self._snippet(c, q_terms)))
        hits.sort(key=lambda h: (-h.score, h.concept.path))
        return hits[:limit]

    def _snippet(self, concept: LoadedConcept, q_terms: List[str], width: int = 160) -> str:
        text = re.sub(r"\s+", " ", concept.body).strip()
        if not text:
            return concept.description
        low = text.lower()
        pos = -1
        for term in q_terms:
            pos = low.find(term)
            if pos != -1:
                break
        if pos == -1:
            return text[:width] + ("..." if len(text) > width else "")
        start = max(0, pos - width // 3)
        end = min(len(text), start + width)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        return prefix + text[start:end].strip() + suffix

    def to_dict(self) -> dict:
        """Export a portable JSON search index (docs + postings)."""
        docs = [
            {
                "path": c.path, "type": c.type, "title": c.title,
                "description": c.description, "resource": c.resource, "tags": c.tags,
            }
            for c in self.bundle.concepts
        ]
        postings: Dict[str, List[List]] = {}
        for path, weighted in self._doc_terms.items():
            for term, tf in weighted.items():
                postings.setdefault(term, []).append([path, round(tf, 2)])
        return {
            "okf_version": self.bundle.okf_version,
            "documents": docs,
            "postings": postings,
            "idf": {t: round(self._idf(t), 4) for t in self._df},
        }


def build_index(bundle_dir: str) -> SearchIndex:
    return SearchIndex(load_bundle(bundle_dir))


def export_index(bundle_dir: str, out_path: Optional[str] = None) -> str:
    idx = build_index(bundle_dir)
    data = json.dumps(idx.to_dict(), indent=2)
    if out_path:
        from pathlib import Path
        Path(out_path).write_text(data, encoding="utf-8")
    return data
