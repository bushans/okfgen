"""BigQuery source: introspect a project's datasets and tables into concepts.

Requires the optional `google-cloud-bigquery` dependency and Application Default
Credentials. Because a bare project id is indistinguishable from a folder name,
this source is selected via an explicit prefix (`bq:`/`bigquery:`) or
`--type bigquery`.
"""

from __future__ import annotations

from typing import List

from ..model import Bundle, Concept, LogEntry, slugify, utcnow_iso
from .base import Source, SourceError

_PREFIXES = ("bq:", "bigquery:")


def _strip_prefix(value: str) -> str:
    for p in _PREFIXES:
        if value.lower().startswith(p):
            return value[len(p):].strip()
    return value.strip()


class BigQuerySource(Source):
    kind = "bigquery"

    @classmethod
    def matches(cls, input_value: str) -> bool:
        return input_value.lower().startswith(_PREFIXES)

    def build(self) -> Bundle:
        try:
            from google.cloud import bigquery  # type: ignore
        except Exception as exc:
            raise SourceError(
                "google-cloud-bigquery is not installed. Install it with:\n"
                "    pip install 'okfgen[bigquery]'\n"
                "and authenticate with `gcloud auth application-default login`."
            ) from exc

        project = _strip_prefix(self.input_value) or self.options.get("project")
        if not project:
            raise SourceError("No BigQuery project id supplied (use bq:PROJECT_ID).")

        try:
            client = bigquery.Client(project=project)
        except Exception as exc:
            raise SourceError(f"Could not create BigQuery client for {project}: {exc}") from exc

        bundle = Bundle(
            title=f"BigQuery: {project}",
            description=f"Data catalog for BigQuery project `{project}`.",
            source=f"bigquery://{project}",
        )

        dataset_slug = self.options.get("dataset")
        try:
            datasets = list(client.list_datasets(project=project))
        except Exception as exc:
            raise SourceError(f"Failed to list datasets in {project}: {exc}") from exc

        if not datasets:
            raise SourceError(f"No datasets found (or no access) in project {project}.")

        bundle.add(Concept(
            path="overview.md",
            type="Data Project",
            title=f"BigQuery project {project}",
            description=f"{len(datasets)} dataset(s) in project `{project}`.",
            resource=f"https://console.cloud.google.com/bigquery?project={project}",
            tags=["bigquery", "gcp"],
            body="# Schema\n\n" + "\n".join(
                f"- `{d.dataset_id}`" for d in datasets
            ),
        ))

        n_tables = 0
        for ds_ref in datasets:
            ds_id = ds_ref.dataset_id
            if dataset_slug and ds_id != dataset_slug:
                continue
            dataset = client.get_dataset(ds_ref.reference)
            tables = list(client.list_tables(dataset.reference))

            bundle.add(Concept(
                path=f"datasets/{slugify(ds_id)}.md",
                type="BigQuery Dataset",
                title=ds_id,
                description=(dataset.description or f"Dataset `{ds_id}`.")[:200],
                resource=f"https://console.cloud.google.com/bigquery?project={project}&d={ds_id}",
                tags=["bigquery", "dataset"],
                extra={"location": dataset.location} if dataset.location else {},
                body="# Schema\n\n" + "\n".join(
                    f"- [{t.table_id}](/tables/{slugify(ds_id)}-{slugify(t.table_id)}.md)"
                    for t in tables
                ) if tables else "No tables in this dataset.",
            ))

            for t in tables:
                table = client.get_table(t.reference)
                bundle.add(self._table_concept(project, ds_id, table))
                n_tables += 1

        bundle.log_entries.append(LogEntry(
            date=utcnow_iso()[:10],
            action="Generated",
            text=f"Cataloged {n_tables} table(s) across {len(datasets)} dataset(s) from {project}.",
        ))
        return bundle

    def _table_concept(self, project: str, ds_id: str, table) -> Concept:
        rows: List[str] = ["# Schema", "", "| Column | Type | Mode | Description |", "|---|---|---|---|"]
        for fld in table.schema:
            desc = (fld.description or "").replace("|", "\\|")
            rows.append(f"| {fld.name} | {fld.field_type} | {fld.mode} | {desc} |")

        meta = []
        if table.num_rows is not None:
            meta.append(f"- **Rows:** {table.num_rows:,}")
        if table.num_bytes is not None:
            meta.append(f"- **Size:** {table.num_bytes:,} bytes")
        if getattr(table, "table_type", None):
            meta.append(f"- **Table type:** {table.table_type}")
        body = "\n".join(rows)
        if meta:
            body = "# Examples\n\n" + "\n".join(meta) + "\n\n" + body

        return Concept(
            path=f"tables/{slugify(ds_id)}-{slugify(table.table_id)}.md",
            type="BigQuery Table",
            title=f"{ds_id}.{table.table_id}",
            description=(table.description or f"Table `{ds_id}.{table.table_id}`.")[:200],
            resource=(
                f"https://console.cloud.google.com/bigquery?project={project}"
                f"&d={ds_id}&t={table.table_id}&page=table"
            ),
            tags=["bigquery", "table", ds_id],
            body=body,
        )
