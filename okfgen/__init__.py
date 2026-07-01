"""okfgen — deterministic Open Knowledge Format (OKF) bundle generator.

Turn a source (git repo URL, BigQuery project, Firebase project, local
directory, or web docs site) into a conformant OKF v0.1 bundle: a directory of
markdown files with YAML frontmatter.

See https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
"""

__version__ = "0.1.0"
OKF_VERSION = "0.1"

__all__ = ["__version__", "OKF_VERSION"]
