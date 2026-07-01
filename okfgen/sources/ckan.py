"""CKAN open-data source (live, no auth).

CKAN is the open-source platform behind thousands of public data portals
(data.gov, data.gov.au, the EU Open Data Portal, and hundreds of city portals
like Toronto Open Data). Its Action API is unauthenticated JSON, so a single
adapter turns any CKAN dataset into an OKF bundle:

    dataset  -> a "Dataset" overview concept
    resource -> a "Data Resource" concept, with a live column schema and a few
                example rows pulled from the CKAN DataStore when available.

Selected via `ckan:` — either a dataset page URL or a portal root + `--dataset`:

    okfgen generate ckan:https://portal/dataset/some-slug
    okfgen generate ckan:https://portal --dataset some-slug
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..model import Bundle, Concept, LogEntry, slugify, utcnow_iso
from .base import Source, SourceError

_PREFIX = "ckan:"
_UA = "okfgen/0.1 (+https://github.com/GoogleCloudPlatform/knowledge-catalog)"


def _strip_prefix(value: str) -> str:
    return value[len(_PREFIX):].strip() if value.lower().startswith(_PREFIX) else value.strip()


class CkanSource(Source):
    kind = "ckan"

    @classmethod
    def matches(cls, input_value: str) -> bool:
        return input_value.lower().startswith(_PREFIX)

    # --- API helpers --------------------------------------------------------

    def _api(self, action: str, **params) -> dict:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{self._base}/api/3/action/{action}?{query}"
        req = Request(url, headers={"User-Agent": _UA})
        try:
            with urlopen(req, timeout=self.options.get("timeout", 30)) as resp:
                data = json.load(resp)
        except Exception as exc:
            raise SourceError(f"CKAN request failed ({action}): {exc}") from exc
        if not data.get("success"):
            raise SourceError(f"CKAN API returned an error for {action}: {data.get('error')}")
        return data["result"]

    def _parse_input(self) -> str:
        raw = _strip_prefix(self.input_value)
        if not raw.startswith(("http://", "https://")):
            raise SourceError("ckan: input must be an https URL (portal or dataset page).")
        if "/dataset/" in raw:
            root, _, tail = raw.partition("/dataset/")
            self._base = root.rstrip("/")
            slug = tail.split("/")[0].split("?")[0]
        else:
            self._base = raw.rstrip("/")
            slug = self.options.get("dataset")
        if not slug:
            raise SourceError(
                "No CKAN dataset specified. Use ckan:<portal>/dataset/<slug> "
                "or pass --dataset <slug>."
            )
        return slug

    # --- build --------------------------------------------------------------

    def build(self) -> Bundle:
        self._base = ""
        slug = self._parse_input()
        pkg = self._api("package_show", id=slug)

        portal = urlparse(self._base).netloc
        title = pkg.get("title") or slug
        org = (pkg.get("organization") or {}).get("title", "")
        tags = [t.get("name") for t in pkg.get("tags", []) if t.get("name")]

        bundle = Bundle(
            title=title,
            description=(pkg.get("notes") or f"CKAN dataset `{slug}`.").strip()[:200],
            source=f"{self._base}/dataset/{slug}",
        )

        resources = pkg.get("resources", [])
        body_lines: List[str] = []
        if pkg.get("notes"):
            body_lines += [pkg["notes"].strip(), ""]
        body_lines += ["# Schema", "", "Resources in this dataset:", ""]
        for r in resources:
            body_lines.append(
                f"- [{r.get('name') or r.get('id')}]"
                f"(/resources/{slugify(r.get('name') or r.get('id'))}.md) "
                f"— {r.get('format', '?')}"
            )
        body_lines += ["", "## Metadata", ""]
        if org:
            body_lines.append(f"- **Publisher:** {org}")
        if pkg.get("license_title"):
            body_lines.append(f"- **License:** {pkg['license_title']}")
        if pkg.get("metadata_modified"):
            body_lines.append(f"- **Last modified:** {pkg['metadata_modified']}")
        body_lines.append(f"- **Resources:** {len(resources)}")

        bundle.add(Concept(
            path="overview.md",
            type="Dataset",
            title=title,
            description=(pkg.get("notes") or f"CKAN dataset `{slug}`.").strip()[:200],
            resource=f"{self._base}/dataset/{slug}",
            tags=(["open-data", portal] + tags)[:12],
            body="\n".join(body_lines),
        ))

        n_schemas = 0
        for r in resources:
            concept, had_schema = self._resource_concept(slug, portal, r)
            bundle.add(concept)
            n_schemas += 1 if had_schema else 0

        bundle.log_entries.append(LogEntry(
            date=utcnow_iso()[:10], action="Fetched",
            text=f"Cataloged {len(resources)} resource(s) from CKAN dataset "
                 f"'{slug}' on {portal} ({n_schemas} with live column schemas).",
        ))
        return bundle

    def _resource_concept(self, slug: str, portal: str, r: Dict):
        rid = r.get("id", "")
        name = r.get("name") or rid
        body_parts: List[str] = []
        had_schema = False

        if r.get("description"):
            body_parts.append(r["description"].strip())

        # Pull live column schema + example rows from the DataStore, if enabled.
        if r.get("datastore_active") and rid:
            try:
                ds = self._api("datastore_search", resource_id=rid, limit=3)
                fields = [f for f in ds.get("fields", []) if not str(f.get("id", "")).startswith("_")]
                if fields:
                    had_schema = True
                    body_parts.append("# Schema")
                    body_parts.append("")
                    body_parts.append("| Column | Type |")
                    body_parts.append("|---|---|")
                    for f in fields:
                        body_parts.append(f"| `{f.get('id')}` | {f.get('type')} |")
                    rows = ds.get("records", [])
                    if rows:
                        body_parts.append("")
                        body_parts.append("# Examples")
                        body_parts.append("")
                        cols = [f["id"] for f in fields]
                        body_parts.append("| " + " | ".join(cols) + " |")
                        body_parts.append("|" + "|".join("---" for _ in cols) + "|")
                        for row in rows[:3]:
                            cells = [str(row.get(c, "")).replace("|", "\\|")[:40] for c in cols]
                            body_parts.append("| " + " | ".join(cells) + " |")
                    total = ds.get("total")
                    if total is not None:
                        body_parts.append("")
                        body_parts.append(f"_Total rows: {total:,}_")
            except SourceError:
                body_parts.append("_(DataStore schema unavailable for this resource.)_")

        return Concept(
            path=f"resources/{slugify(name)}.md",
            type="Data Resource",
            title=name,
            description=(r.get("description") or f"{r.get('format', 'data')} resource "
                        f"in dataset {slug}.").strip()[:200],
            resource=r.get("url") or f"{self._base}/dataset/{slug}",
            tags=["open-data", "resource"] + ([r["format"].lower()] if r.get("format") else []),
            extra={"format": r.get("format", "")} if r.get("format") else {},
            body="\n".join(body_parts).strip() or f"{r.get('format','Data')} resource.",
        ), had_schema
