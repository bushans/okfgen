# Contributing to okfgen

Thanks for your interest! okfgen is a deterministic producer/consumer toolkit
for the [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md).
Contributions of all sizes are welcome — new source adapters, bug fixes, docs,
and tests especially.

## Ways to contribute

- **Add a source adapter** (a new producer — e.g. Postgres, Notion, OpenAPI, a
  new open-data platform). This is the highest-leverage contribution — see below.
- **Improve extraction** in an existing adapter (better schema/def parsing).
- **Add or improve a consumer** (visualizer, search, agent).
- **Fix a bug** or improve error messages.
- **Docs, examples, and sample bundles.**

Have an idea? Open an issue to discuss first for anything non-trivial, so we can
agree on the approach before you invest time.

## Development setup

```bash
git clone https://github.com/bushans/okfgen.git
cd okfgen
python -m venv .venv && . .venv/bin/activate     # Windows: .\.venv\Scripts\Activate.ps1
pip install -e '.[dev]'
pytest
```

[TESTING.md](TESTING.md) has a full VS Code / PowerShell walkthrough and example
commands for every producer and consumer.

## Guiding principles

Please keep changes aligned with what makes okfgen okfgen:

1. **Deterministic by default.** Extract real facts from the source; never
   require an LLM or network beyond what a source inherently needs. Anything
   LLM-powered must sit behind an explicit `--llm` flag and degrade gracefully
   when it's unavailable.
2. **Minimal dependencies.** The core (git/local/web/schema) runs on the Python
   standard library alone. New third-party deps must be **optional extras**,
   imported lazily inside the code path that needs them (see how
   `okfgen/sources/bigquery.py` imports its SDK).
3. **Conformance.** Every bundle okfgen emits must pass `okfgen validate`. New
   producers should have a test asserting the output is conformant.
4. **Consumers depend only on markdown + frontmatter** (`okfgen/consumer.py`),
   never on producer internals.

## How to add a source adapter

The producer interface is small. To add one:

1. Create `okfgen/sources/<name>.py` with a `Source` subclass:

   ```python
   from ..model import Bundle, Concept, LogEntry, slugify, utcnow_iso
   from .base import Source, SourceError

   class MySource(Source):
       kind = "mysource"

       @classmethod
       def matches(cls, input_value: str) -> bool:
           # Used for auto-detection. Prefer an explicit prefix ("mysource:")
           # for anything ambiguous with a path or URL.
           return input_value.lower().startswith("mysource:")

       def build(self) -> Bundle:
           bundle = Bundle(title="...", source=self.input_value)
           bundle.add(Concept(path="overview.md", type="...", title="...",
                              description="...", body="# Schema\n..."))
           # raise SourceError("...") for bad input / missing deps / auth issues
           return bundle
   ```

2. Register it in `okfgen/sources/__init__.py` (`REGISTRY` + `__all__`) and add
   its `kind` to `_DETECT_ORDER` in `okfgen/detect.py` (prefix-based adapters
   should come before the generic `local`/`git`/`web` fallbacks).

3. Add a test in `tests/`. For network sources, **stub the API** (subclass and
   override the fetch method) so tests stay offline and fast — see
   `tests/test_ckan.py` for the pattern.

4. If it produces table-like concepts, keep column names in a `# Schema`
   markdown table so the enrichment agent can infer join paths.

5. Document it in the README's producer table.

## Tests & quality

- Run `pytest` — please keep it green and add tests for new behavior.
- Tests must not hit the network (stub it) and must not depend on cloud
  credentials.
- Match the surrounding code style: type hints, small focused functions,
  comments that explain *why* rather than *what*.

To regenerate the sample bundles after a producer change:

```bash
python samples/build_samples.py       # offline, reproducible
python samples/build_pages.py         # refresh the docs/ visualizers
```

## Pull requests

- Branch off `main`, keep PRs focused, and describe the change and its rationale.
- Ensure `pytest` passes; CI runs it on Python 3.9–3.12.
- Reference any related issue.

## Reporting bugs

Open an issue with: the command you ran, what you expected, what happened
(include the error), your OS and Python version, and — if relevant — a small
sample source that reproduces it.

## License

By contributing, you agree that your contributions will be licensed under the
project's [Apache-2.0 License](LICENSE).
