"""Local directory source: generate a bundle from a folder on disk."""

from __future__ import annotations

from pathlib import Path

from ..model import Bundle
from .base import Source, SourceError
from .scan import scan_directory


class LocalDirSource(Source):
    kind = "local"

    @classmethod
    def matches(cls, input_value: str) -> bool:
        try:
            return Path(input_value).is_dir()
        except OSError:
            return False

    def build(self) -> Bundle:
        root = Path(self.input_value).expanduser().resolve()
        if not root.is_dir():
            raise SourceError(f"Not a directory: {root}")
        title = self.options.get("title") or root.name
        return scan_directory(root, title=title, source_label=str(root))
