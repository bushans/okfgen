"""Database schema source (offline).

A cloud-free "your database" producer: reads a schema description from a JSON
file (or a simple SQL `CREATE TABLE` DDL file) and mints dataset + table
concepts identical in shape to the BigQuery source — so join-path enrichment and
the visualizer work the same way, no credentials required.

Selected via `schema:PATH` or `--type schema` with a file path.

JSON shape:
    {
      "project": "acme",
      "title": "Acme Sales",
      "description": "...",
      "console_url": "https://...",           # optional
      "datasets": [
        {"id": "sales", "description": "...",
         "tables": [
            {"name": "orders", "description": "...", "num_rows": 12000,
             "columns": [
                {"name": "order_id", "type": "STRING", "mode": "REQUIRED",
                 "description": "..."}
             ]}
         ]}
      ]
    }
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

from ..model import Bundle, Concept, LogEntry, slugify, utcnow_iso
from .base import Source, SourceError

_PREFIX = "schema:"


def _strip_prefix(value: str) -> str:
    return value[len(_PREFIX):].strip() if value.lower().startswith(_PREFIX) else value.strip()


class SchemaSource(Source):
    kind = "schema"

    @classmethod
    def matches(cls, input_value: str) -> bool:
        v = input_value.strip()
        if v.lower().startswith(_PREFIX):
            return True
        # Auto-detect a .sql DDL file or a .json file that looks like a schema.
        p = Path(v)
        if p.suffix.lower() == ".sql" and p.is_file():
            return True
        if p.suffix.lower() == ".json" and p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return isinstance(data, dict) and "datasets" in data
            except Exception:
                return False
        return False

    def build(self) -> Bundle:
        path = Path(_strip_prefix(self.input_value)).expanduser()
        if not path.is_file():
            raise SourceError(f"Schema file not found: {path}")
        if path.suffix.lower() == ".sql":
            data = self._parse_sql(path.read_text(encoding="utf-8"), path.stem)
        else:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise SourceError(f"Invalid schema JSON in {path}: {exc}") from exc
        return self._to_bundle(data)

    # --- builders -----------------------------------------------------------

    def _to_bundle(self, data: Dict) -> Bundle:
        project = data.get("project") or self.options.get("title") or "database"
        title = data.get("title") or f"Database: {project}"
        console = data.get("console_url", "")
        bundle = Bundle(
            title=title,
            description=data.get("description", f"Data catalog for `{project}`."),
            source=f"schema://{project}",
        )

        datasets = data.get("datasets") or []
        if not datasets:
            raise SourceError("Schema has no 'datasets'.")

        bundle.add(Concept(
            path="overview.md",
            type="Data Project",
            title=title,
            description=data.get("description", f"{len(datasets)} dataset(s) in `{project}`.")[:200],
            resource=console,
            tags=["database", "catalog"],
            body="# Schema\n\n" + "\n".join(
                f"- [{d.get('id')}](/datasets/{slugify(d.get('id',''))}.md)" for d in datasets
            ),
        ))

        n_tables = 0
        for ds in datasets:
            ds_id = ds.get("id") or "dataset"
            tables = ds.get("tables") or []
            bundle.add(Concept(
                path=f"datasets/{slugify(ds_id)}.md",
                type="Dataset",
                title=ds_id,
                description=(ds.get("description") or f"Dataset `{ds_id}`.")[:200],
                resource=ds.get("resource", ""),
                tags=["database", "dataset"],
                body="# Schema\n\n" + ("\n".join(
                    f"- [{t.get('name')}](/tables/{slugify(ds_id)}-{slugify(t.get('name',''))}.md)"
                    for t in tables
                ) or "No tables."),
            ))
            for t in tables:
                bundle.add(self._table_concept(ds_id, t))
                n_tables += 1

        bundle.log_entries.append(LogEntry(
            date=utcnow_iso()[:10], action="Generated",
            text=f"Cataloged {n_tables} table(s) across {len(datasets)} dataset(s) from schema file.",
        ))
        return bundle

    def _table_concept(self, ds_id: str, table: Dict) -> Concept:
        name = table.get("name") or "table"
        cols = table.get("columns") or []
        rows = ["# Schema", "", "| Column | Type | Mode | Description |", "|---|---|---|---|"]
        for c in cols:
            desc = str(c.get("description", "")).replace("|", "\\|")
            rows.append(f"| `{c.get('name','')}` | {c.get('type','')} | {c.get('mode','')} | {desc} |")
        body = "\n".join(rows)
        meta = []
        if table.get("num_rows") is not None:
            meta.append(f"- **Rows:** {table['num_rows']:,}")
        if table.get("type"):
            meta.append(f"- **Table type:** {table['type']}")
        if meta:
            body = "# Examples\n\n" + "\n".join(meta) + "\n\n" + body
        return Concept(
            path=f"tables/{slugify(ds_id)}-{slugify(name)}.md",
            type="Table",
            title=f"{ds_id}.{name}",
            description=(table.get("description") or f"Table `{ds_id}.{name}`.")[:200],
            resource=table.get("resource", ""),
            tags=["database", "table", ds_id],
            body=body,
        )

    # --- minimal SQL DDL parsing -------------------------------------------

    def _parse_sql(self, sql: str, default_ds: str) -> Dict:
        """Parse a handful of `CREATE TABLE name (col type, ...);` statements."""
        datasets: Dict[str, Dict] = {}
        pattern = re.compile(
            r"create\s+table\s+(?:if\s+not\s+exists\s+)?([`\"\[\]\w.]+)\s*\((.*?)\)\s*;",
            re.IGNORECASE | re.DOTALL,
        )
        for m in pattern.finditer(sql):
            raw_name = m.group(1).strip().strip('`"[]')
            body = m.group(2)
            if "." in raw_name:
                ds_id, tbl = raw_name.split(".", 1)
            else:
                ds_id, tbl = default_ds, raw_name
            columns = []
            for col_line in self._split_columns(body):
                col_line = col_line.strip()
                if not col_line or re.match(r"(?i)(primary|foreign|constraint|unique|key|check)\b", col_line):
                    continue
                parts = col_line.split(None, 1)
                if not parts:
                    continue
                col_name = parts[0].strip('`"[]')
                col_type = (parts[1].split(",")[0].strip() if len(parts) > 1 else "").split()[0] if len(parts) > 1 else ""
                columns.append({"name": col_name, "type": col_type.upper(), "mode": ""})
            ds = datasets.setdefault(ds_id, {"id": ds_id, "tables": []})
            ds["tables"].append({"name": tbl, "columns": columns})
        if not datasets:
            raise SourceError("No CREATE TABLE statements found in SQL file.")
        return {"project": default_ds, "title": f"Database: {default_ds}",
                "datasets": list(datasets.values())}

    def _split_columns(self, body: str) -> List[str]:
        """Split a column list on commas that are not inside parentheses."""
        out, depth, cur = [], 0, []
        for ch in body:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                out.append("".join(cur)); cur = []
            else:
                cur.append(ch)
        if cur:
            out.append("".join(cur))
        return out
