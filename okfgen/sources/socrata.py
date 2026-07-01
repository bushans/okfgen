"""Socrata (SODA) open-data source (live, no auth).

Socrata powers a large share of US government open-data portals — NYC Open Data,
data.seattle.gov, data.cityofchicago.org, many state portals. Each dataset has a
stable 4x4 identifier (e.g. `erm2-nwe9`) and an unauthenticated metadata + data
API, so a single adapter turns any Socrata dataset into an OKF bundle:

    dataset metadata -> a "Dataset" overview concept
    the tabular data -> a "Table" concept with the column schema + example rows

Selected via `socrata:` — a dataset URL, `domain/4x4-id`, or a domain + --dataset:

    okfgen generate socrata:https://data.cityofnewyork.us/d/erm2-nwe9
    okfgen generate socrata:data.cityofnewyork.us/erm2-nwe9
    okfgen generate socrata:https://data.seattle.gov --dataset kzjm-xkqj
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..model import Bundle, Concept, LogEntry, slugify, utcnow_iso
from .base import Source, SourceError

_PREFIX = "socrata:"
_UA = "okfgen/0.1 (+https://github.com/GoogleCloudPlatform/knowledge-catalog)"
_ID_RE = re.compile(r"[a-z0-9]{4}-[a-z0-9]{4}")


def _strip_prefix(value: str) -> str:
    return value[len(_PREFIX):].strip() if value.lower().startswith(_PREFIX) else value.strip()


class SocrataSource(Source):
    kind = "socrata"

    @classmethod
    def matches(cls, input_value: str) -> bool:
        return input_value.lower().startswith(_PREFIX)

    def _get(self, url: str):
        req = Request(url, headers={"User-Agent": _UA})
        try:
            with urlopen(req, timeout=self.options.get("timeout", 30)) as resp:
                return json.load(resp)
        except Exception as exc:
            raise SourceError(f"Socrata request failed: {url}: {exc}") from exc

    def _parse_input(self):
        raw = _strip_prefix(self.input_value)
        # Domain: from the URL host, or the first path segment when scheme-less.
        if raw.startswith(("http://", "https://")):
            parsed = urlparse(raw)
            domain = parsed.netloc
            tail = parsed.path
        else:
            parts = raw.split("/", 1)
            domain = parts[0]
            tail = "/" + (parts[1] if len(parts) > 1 else "")
        if not domain:
            raise SourceError("socrata: input must include a portal domain.")

        m = _ID_RE.search(tail) or _ID_RE.search(self.options.get("dataset", "") or "")
        if not m:
            raise SourceError(
                "No Socrata dataset id (4x4, e.g. erm2-nwe9) found. Pass one in the "
                "URL or via --dataset."
            )
        return domain, m.group(0)

    def build(self) -> Bundle:
        domain, dataset_id = self._parse_input()
        base = f"https://{domain}"
        meta = self._get(f"{base}/api/views/{dataset_id}.json")

        name = meta.get("name") or dataset_id
        description = (meta.get("description") or f"Socrata dataset `{dataset_id}`.").strip()
        page_url = f"{base}/d/{dataset_id}"

        columns = [c for c in meta.get("columns", []) if not str(c.get("fieldName", "")).startswith(":")]

        bundle = Bundle(title=name, description=description[:200], source=page_url)

        # Overview concept.
        meta_lines = []
        if meta.get("category"):
            meta_lines.append(f"- **Category:** {meta['category']}")
        if meta.get("attribution"):
            meta_lines.append(f"- **Attribution:** {meta['attribution']}")
        if meta.get("viewCount") is not None:
            meta_lines.append(f"- **Views:** {meta['viewCount']:,}")
        meta_lines.append(f"- **Columns:** {len(columns)}")
        overview_body = [description, "", "# Schema", "",
                         f"- [{name} — table](/tables/{slugify(dataset_id)}.md) "
                         f"— {len(columns)} columns"]
        if meta_lines:
            overview_body += ["", "## Metadata", ""] + meta_lines

        bundle.add(Concept(
            path="overview.md",
            type="Dataset",
            title=name,
            description=description[:200],
            resource=page_url,
            tags=(["open-data", domain] + ([meta["category"]] if meta.get("category") else []))[:10],
            body="\n".join(overview_body),
        ))

        # Table concept with schema + example rows.
        bundle.add(self._table_concept(base, domain, dataset_id, name, columns))

        bundle.log_entries.append(LogEntry(
            date=utcnow_iso()[:10], action="Fetched",
            text=f"Cataloged Socrata dataset '{dataset_id}' from {domain} "
                 f"({len(columns)} columns).",
        ))
        return bundle

    def _table_concept(self, base, domain, dataset_id, name, columns) -> Concept:
        rows: List[str] = ["# Schema", "", "| Column | Field | Type | Description |",
                           "|---|---|---|---|"]
        for c in columns:
            desc = str(c.get("description", "")).replace("|", "\\|").replace("\n", " ")[:120]
            rows.append(f"| {c.get('name','')} | `{c.get('fieldName','')}` | "
                        f"{c.get('dataTypeName','')} | {desc} |")

        body = "\n".join(rows)

        # Example rows from the SODA data endpoint (best effort).
        try:
            sample = self._get(f"{base}/resource/{dataset_id}.json?$limit=3")
            if isinstance(sample, list) and sample:
                field_names = [c["fieldName"] for c in columns][:8]
                ex = ["", "# Examples", "", "| " + " | ".join(field_names) + " |",
                      "|" + "|".join("---" for _ in field_names) + "|"]
                for row in sample[:3]:
                    cells = [str(row.get(f, "")).replace("|", "\\|")[:40] for f in field_names]
                    ex.append("| " + " | ".join(cells) + " |")
                body += "\n" + "\n".join(ex)
        except SourceError:
            pass

        return Concept(
            path=f"tables/{slugify(dataset_id)}.md",
            type="Table",
            title=f"{name} (table)",
            description=f"Tabular data for Socrata dataset `{dataset_id}`.",
            resource=f"{base}/resource/{dataset_id}",
            tags=["open-data", "table", domain],
            body=body,
        )
