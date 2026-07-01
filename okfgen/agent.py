"""Reasoning-agent consumer: answer questions over an OKF bundle.

Demonstrates the "agent that reasons over bundles" consumer. The default is a
deterministic retrieval agent: it finds the most relevant concepts via the
search index, expands one hop along the link graph (the join paths / cross-links
producers encode), and returns an answer grounded in citations plus a visible
traversal path. With `--llm` it hands the retrieved context to a model to phrase
a natural-language answer — retrieval stays deterministic and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .consumer import LoadedBundle, LoadedConcept, load_bundle
from .searchindex import SearchIndex


@dataclass
class AgentAnswer:
    question: str
    answer: str
    citations: List[LoadedConcept] = field(default_factory=list)
    traversal: List[str] = field(default_factory=list)  # human-readable steps

    def render(self) -> str:
        lines = [f"Q: {self.question}", "", self.answer, ""]
        if self.citations:
            lines.append("Citations:")
            for c in self.citations:
                res = f" — {c.resource}" if c.resource else ""
                lines.append(f"  - [{c.type}] {c.title} ({c.path}){res}")
        if self.traversal:
            lines.append("")
            lines.append("Reasoning path:")
            for step in self.traversal:
                lines.append(f"  {step}")
        return "\n".join(lines)


class ReasoningAgent:
    def __init__(self, bundle: LoadedBundle):
        self.bundle = bundle
        self.index = SearchIndex(bundle)

    def answer(self, question: str, top_k: int = 3, use_llm: bool = False) -> AgentAnswer:
        hits = self.index.search(question, limit=top_k)
        traversal: List[str] = []
        if not hits:
            return AgentAnswer(
                question=question,
                answer="No concepts in this bundle match the question.",
                traversal=[f"searched {len(self.bundle.concepts)} concept(s), 0 matches"],
            )

        primary = [h.concept for h in hits]
        traversal.append(
            "retrieved: " + ", ".join(f"{c.path} (score {h.score:.1f})"
                                      for c, h in zip(primary, hits))
        )

        # Expand one hop along outgoing + incoming links to gather context.
        backlinks = self.bundle.backlinks()
        neighbors: List[LoadedConcept] = []
        seen = {c.path for c in primary}
        for c in primary:
            for tgt in c.links:
                nb = self.bundle.get(tgt)
                if nb and nb.path not in seen:
                    neighbors.append(nb)
                    seen.add(nb.path)
                    traversal.append(f"followed link: {c.path} → {nb.path}")
            for src in backlinks.get(c.path, []):
                nb = self.bundle.get(src)
                if nb and nb.path not in seen:
                    neighbors.append(nb)
                    seen.add(nb.path)
                    traversal.append(f"followed backlink: {nb.path} → {c.path}")

        citations = primary + neighbors
        if use_llm:
            answer_text = self._llm_answer(question, citations)
        else:
            answer_text = self._deterministic_answer(question, primary, neighbors, hits)
        return AgentAnswer(question=question, answer=answer_text,
                           citations=citations, traversal=traversal)

    def _deterministic_answer(self, question, primary, neighbors, hits) -> str:
        top = primary[0]
        parts: List[str] = []
        desc = top.description or (top.body.splitlines()[0] if top.body else "")
        parts.append(f"Most relevant: **{top.title}** ({top.type}). {desc}".strip())

        if len(primary) > 1:
            others = "; ".join(f"{c.title} ({c.type})" for c in primary[1:])
            parts.append(f"Also relevant: {others}.")
        if neighbors:
            rel = ", ".join(c.title for c in neighbors[:5])
            parts.append(f"Related concepts reachable by links: {rel}.")

        snippet = next((h.snippet for h in hits if h.concept.path == top.path), "")
        if snippet and snippet not in desc:
            parts.append(f"Context: {snippet}")
        return "\n".join(parts)

    def _llm_answer(self, question: str, citations: List[LoadedConcept]) -> str:
        from .llm import synthesize_answer  # lazy import; optional dependency
        context = "\n\n".join(
            f"## {c.title} ({c.type}) [{c.path}]\n{c.description}\n{c.body[:1500]}"
            for c in citations
        )
        result = synthesize_answer(question, context)
        if result is None:
            return ("(LLM unavailable — set ANTHROPIC_API_KEY and install `anthropic`.)\n"
                    + self._deterministic_answer(question, citations[:1], [], []))
        return result


def ask(bundle_dir: str, question: str, top_k: int = 3, use_llm: bool = False) -> AgentAnswer:
    return ReasoningAgent(load_bundle(bundle_dir)).answer(question, top_k=top_k, use_llm=use_llm)
