"""Firebase source: catalog a Firebase/Firestore project into concepts.

Requires the optional `google-cloud-firestore` dependency and credentials
(Application Default Credentials or GOOGLE_APPLICATION_CREDENTIALS). Selected via
an explicit prefix (`firebase:`/`fb:`) or `--type firebase`.

Firestore is schemaless, so the catalog is built by sampling documents from each
top-level collection and inferring field names/types deterministically.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Dict

from ..model import Bundle, Concept, LogEntry, slugify, utcnow_iso
from .base import Source, SourceError

_PREFIXES = ("firebase:", "fb:", "firestore:")


def _strip_prefix(value: str) -> str:
    for p in _PREFIXES:
        if value.lower().startswith(p):
            return value[len(p):].strip()
    return value.strip()


def _py_type(value) -> str:
    name = type(value).__name__
    return {
        "str": "string", "int": "integer", "float": "float", "bool": "boolean",
        "dict": "map", "list": "array", "NoneType": "null",
    }.get(name, name)


class FirebaseSource(Source):
    kind = "firebase"

    @classmethod
    def matches(cls, input_value: str) -> bool:
        return input_value.lower().startswith(_PREFIXES)

    def build(self) -> Bundle:
        try:
            from google.cloud import firestore  # type: ignore
        except Exception as exc:
            raise SourceError(
                "google-cloud-firestore is not installed. Install it with:\n"
                "    pip install 'okfgen[firebase]'\n"
                "and authenticate with `gcloud auth application-default login`."
            ) from exc

        project = _strip_prefix(self.input_value) or self.options.get("project")
        if not project:
            raise SourceError("No Firebase project id supplied (use firebase:PROJECT_ID).")

        try:
            client = firestore.Client(project=project)
        except Exception as exc:
            raise SourceError(f"Could not create Firestore client for {project}: {exc}") from exc

        sample_size = int(self.options.get("sample", 50))
        bundle = Bundle(
            title=f"Firebase: {project}",
            description=f"Firestore data catalog for Firebase project `{project}`.",
            source=f"firebase://{project}",
        )

        try:
            collections = list(client.collections())
        except Exception as exc:
            raise SourceError(f"Failed to list Firestore collections in {project}: {exc}") from exc

        if not collections:
            raise SourceError(
                f"No top-level Firestore collections found (or no access) in {project}."
            )

        bundle.add(Concept(
            path="overview.md",
            type="Firebase Project",
            title=f"Firebase project {project}",
            description=f"{len(collections)} top-level Firestore collection(s).",
            resource=f"https://console.firebase.google.com/project/{project}/firestore",
            tags=["firebase", "firestore", "gcp"],
            body="# Schema\n\n" + "\n".join(
                f"- [{c.id}](/collections/{slugify(c.id)}.md)" for c in collections
            ),
        ))

        for coll in collections:
            bundle.add(self._collection_concept(project, coll, sample_size))

        bundle.log_entries.append(LogEntry(
            date=utcnow_iso()[:10],
            action="Generated",
            text=f"Cataloged {len(collections)} Firestore collection(s) from {project}.",
        ))
        return bundle

    def _collection_concept(self, project: str, coll, sample_size: int) -> Concept:
        # Deterministically infer a field -> set-of-types map by sampling docs.
        field_types: "OrderedDict[str, set]" = OrderedDict()
        doc_count = 0
        examples = []
        try:
            for doc in coll.limit(sample_size).stream():
                doc_count += 1
                data = doc.to_dict() or {}
                if len(examples) < 2:
                    examples.append(doc.id)
                for key, value in data.items():
                    field_types.setdefault(key, set()).add(_py_type(value))
        except Exception as exc:
            # Surface as a note rather than failing the whole bundle.
            return Concept(
                path=f"collections/{slugify(coll.id)}.md",
                type="Firestore Collection",
                title=coll.id,
                description=f"Collection `{coll.id}` (could not sample: {exc}).",
                resource=f"https://console.firebase.google.com/project/{project}/firestore/data/{coll.id}",
                tags=["firebase", "collection"],
                body=f"Sampling failed: {exc}",
            )

        rows = ["# Schema", "", "| Field | Inferred type(s) |", "|---|---|"]
        for name, types in field_types.items():
            rows.append(f"| {name} | {', '.join(sorted(types))} |")
        body = "\n".join(rows)
        if examples:
            body += "\n\n# Examples\n\n" + "\n".join(f"- Document id `{e}`" for e in examples)

        return Concept(
            path=f"collections/{slugify(coll.id)}.md",
            type="Firestore Collection",
            title=coll.id,
            description=f"Collection `{coll.id}` — {doc_count} document(s) sampled, "
                        f"{len(field_types)} field(s) inferred.",
            resource=f"https://console.firebase.google.com/project/{project}/firestore/data/{coll.id}",
            tags=["firebase", "firestore", "collection"],
            body=body,
        )
