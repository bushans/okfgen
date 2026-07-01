"""Pluggable source adapters that turn an input into an OKF Bundle."""

from __future__ import annotations

from typing import Dict, Type

from .base import Source, SourceError
from .localdir import LocalDirSource
from .git import GitSource
from .webdocs import WebDocsSource
from .bigquery import BigQuerySource
from .firebase import FirebaseSource
from .schema import SchemaSource
from .ckan import CkanSource
from .socrata import SocrataSource

# Registry keyed by the `--type` value / auto-detected kind.
REGISTRY: Dict[str, Type[Source]] = {
    LocalDirSource.kind: LocalDirSource,
    GitSource.kind: GitSource,
    WebDocsSource.kind: WebDocsSource,
    BigQuerySource.kind: BigQuerySource,
    FirebaseSource.kind: FirebaseSource,
    SchemaSource.kind: SchemaSource,
    CkanSource.kind: CkanSource,
    SocrataSource.kind: SocrataSource,
}

__all__ = [
    "Source",
    "SourceError",
    "REGISTRY",
    "LocalDirSource",
    "GitSource",
    "WebDocsSource",
    "BigQuerySource",
    "FirebaseSource",
    "SchemaSource",
    "CkanSource",
    "SocrataSource",
]
