"""Git repository source: shallow-clone a repo URL and scan it."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..model import Bundle
from .base import Source, SourceError
from .scan import scan_directory

# Recognize common git remote spellings.
_GIT_URL_RE = re.compile(
    r"^(?:"
    r"https?://[^\s]+?(?:\.git)?/?|"           # https://host/org/repo(.git)
    r"git@[^\s:]+:[^\s]+?(?:\.git)?|"          # git@host:org/repo(.git)
    r"ssh://git@[^\s]+|"
    r"git://[^\s]+"
    r")$"
)
_KNOWN_HOSTS = ("github.com", "gitlab.com", "bitbucket.org", "dev.azure.com")


class GitSource(Source):
    kind = "git"

    @classmethod
    def matches(cls, input_value: str) -> bool:
        v = input_value.strip()
        if v.endswith(".git"):
            return True
        if v.startswith("git@") or v.startswith("git://") or v.startswith("ssh://git@"):
            return True
        if v.startswith(("http://", "https://")) and any(h in v for h in _KNOWN_HOSTS):
            return True
        return False

    def _repo_name(self, url: str) -> str:
        name = url.rstrip("/").split("/")[-1]
        name = name.split(":")[-1]  # git@host:org/repo form
        if name.endswith(".git"):
            name = name[:-4]
        return name or "repository"

    def build(self) -> Bundle:
        url = self.input_value.strip()
        if shutil.which("git") is None:
            raise SourceError(
                "The `git` executable was not found on PATH. Install git, or clone "
                "the repo yourself and pass the local path instead."
            )
        name = self.options.get("title") or self._repo_name(url)
        tmp = Path(tempfile.mkdtemp(prefix="okfgen-git-"))
        clone_dir = tmp / "repo"
        try:
            proc = subprocess.run(
                ["git", "clone", "--depth", "1", "--quiet", url, str(clone_dir)],
                capture_output=True, text=True, timeout=self.options.get("timeout", 300),
            )
            if proc.returncode != 0:
                raise SourceError(
                    f"git clone failed for {url}:\n{proc.stderr.strip() or proc.stdout.strip()}"
                )
            bundle = scan_directory(
                clone_dir,
                title=name,
                source_label=url,
                resource_base=self._web_resource_base(url),
            )
            return bundle
        except subprocess.TimeoutExpired:
            raise SourceError(f"git clone timed out for {url}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _web_resource_base(self, url: str) -> str:
        """Best-effort https browse URL for building `resource` links."""
        u = url
        if u.startswith("git@"):
            host, _, path = u[4:].partition(":")
            u = f"https://{host}/{path}"
        if u.endswith(".git"):
            u = u[:-4]
        if u.startswith(("http://", "https://")):
            # Point resources at the default-branch blob view when we can guess it.
            if any(h in u for h in ("github.com", "gitlab.com")):
                return u.rstrip("/") + "/blob/HEAD"
            return u.rstrip("/")
        return ""
