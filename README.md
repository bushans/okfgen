# okfgen

**A deterministic producer *and* consumer toolkit for the [Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md).**

OKF is a vendor-neutral way to represent knowledge — the metadata, context, and
curated insight around your data and systems — as **just markdown files with
YAML frontmatter** ([blog post](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/)).
A *bundle* is a directory of those files; each file is a *concept*.

`okfgen` gives you a working reference implementation of **both sides** of the
OKF ecosystem:

- **Producers** turn a source system, database, or docs site *into* a bundle.
- **Consumers** read a bundle back out — a viewer, a search index, an agent.

Everything is **deterministic by default**: `okfgen` extracts structured facts
straight from the source (schemas, file structure, READMEs, dependency
manifests, page headings). No LLM and no API key are required to run it; an
optional `--llm` flag adds Claude-powered enrichment where you want it.

```
              PRODUCERS                              CONSUMERS
   git repo  ─┐                          ┌─  visualize  → interactive HTML graph
   database  ─┤                          ├─  search     → full-text index
   firebase  ─┼─►  generate ─► BUNDLE ─► ┼─  ask        → reasoning agent
   local dir ─┤        │       (.md +    └─  validate   → conformance check
   web docs  ─┘        ▼      frontmatter)
                    enrich  (pass 2: join paths, backlinks, citations)
```

---

## Install

```bash
pip install -e .            # core: git, local, web, schema sources (zero deps)
pip install -e '.[all]'     # add BigQuery, Firebase, PyYAML
```

Optional extras: `.[bigquery]`, `.[firebase]`, `.[yaml]`, `.[dev]`.

---

## Producers — make a bundle from *your* data

```bash
okfgen generate https://github.com/psf/requests.git   # a source system (git)
okfgen generate ./my-project                          # a source system (local)
okfgen generate schema:./warehouse.schema.json        # a database (offline)
okfgen generate schema:./ddl.sql                      # a database (SQL DDL)
okfgen generate bq:my-gcp-project                     # BigQuery datasets/tables
okfgen generate firebase:my-firebase-project          # Firestore collections
okfgen generate https://docs.mytool.dev/              # a documentation site
okfgen generate ckan:https://portal/dataset/some-set  # a live CKAN open-data portal
okfgen generate socrata:https://data.cityofnewyork.us/d/erm2-nwe9  # a live Socrata dataset
```

| Input | Detected as | What it extracts |
|---|---|---|
| `git@…` / `*.git` / github URL | `git` | shallow-clones, then scans like a local dir |
| a directory path | `local` | README overview, per-directory code modules (functions/classes/types), doc files, dependency inventory |
| `schema:FILE.json` / `.sql` | `schema` | dataset + table concepts with full column schemas — **no cloud creds** |
| `bq:PROJECT` | `bigquery` | one concept per dataset and per table, with column schemas |
| `firebase:PROJECT` | `firebase` | one concept per Firestore collection, fields/types inferred from sampled docs |
| `ckan:PORTAL/dataset/SLUG` | `ckan` | a live [CKAN](https://ckan.org) open-data dataset → one concept per resource, with **live column schemas + example rows** from the DataStore. No auth; works against data.gov, data.gov.au, the EU portal, city portals, etc. |
| `socrata:DOMAIN/d/4x4-ID` | `socrata` | a live [Socrata](https://dev.socrata.com) dataset (NYC Open Data, Seattle, Chicago, many state portals) → Dataset + Table concepts with **live column schema + descriptions + example rows**. No auth. |
| `http(s)://…` | `web` | crawls same-host pages (depth/page budget) into one concept per page |

Cloud sources use Application Default Credentials
(`gcloud auth application-default login`). Output goes to `./<name>-okf/`.

### The enrichment agent (pass 2)

Producers *draft* concepts; the enrichment agent *enriches* them — exactly the
two-pass pattern from the OKF blog. Deterministically, it infers **join paths**
between tables from foreign-key naming (`customer_id → customers`) and wires
**backlinks** so the graph is navigable both ways:

```bash
okfgen enrich ./my-okf                 # in place
okfgen enrich ./my-okf -o ./enriched   # to a new directory
okfgen enrich ./my-okf --llm           # also rewrite descriptions via Claude
```

---

## Consumers — read a bundle back out

The OKF value proposition is producer/consumer independence: any consumer works
on any bundle, regardless of who produced it.

```bash
# Viewer: a self-contained interactive graph (no backend, no CDN, data stays local)
okfgen visualize ./my-okf -o graph.html

# Search index: full-text, TF-IDF ranked
okfgen search ./my-okf "weekly active users"
okfgen search ./my-okf --export index.json      # portable JSON index

# Reasoning agent: retrieves concepts, follows join links, answers with citations
okfgen ask ./my-okf "how do orders relate to customers?"
okfgen ask ./my-okf "..." --llm                 # phrase answer via Claude

# Conformance validation
okfgen validate ./my-okf --strict
```

`okfgen ask` shows its work — the retrieved concepts, the links it traversed, and
the citations behind the answer — so the reasoning is auditable.

---

## Try it against your own data (2 minutes)

```bash
pip install -e .

# 1. Produce a bundle from something you have:
okfgen generate ./path/to/your/repo -o my-okf
#    ...or a database schema (no cloud needed): see samples/recipes/acme_sales.schema.json
#    ...or BigQuery: pip install -e '.[bigquery]' && okfgen generate bq:your-project

# 2. Enrich it (adds join paths + backlinks):
okfgen enrich my-okf

# 3. Explore it three ways:
okfgen visualize my-okf -o my-okf/graph.html   # open graph.html in a browser
okfgen search my-okf "your search terms"
okfgen ask my-okf "a question about your data"
```

---

## Sample bundles

**Browse the sample knowledge graphs online:** https://bushans.github.io/okfgen/

Ready-to-browse bundles live in [`samples/bundles/`](samples/bundles). Open any
`graph.html` in a browser, or point the consumers at them. The same visualizers
are published to GitHub Pages from [`docs/`](docs) (regenerate with
`python samples/build_pages.py`).

- Three **offline, reproducible** bundles (database, source system, docs site):
  `python samples/build_samples.py`
- One **live public-data** bundle — *Toronto Beaches Water Quality* from the
  Toronto Open Data CKAN portal: `python samples/build_live_samples.py`

See [samples/README.md](samples/README.md) for details.

---

## Output layout

```
<name>-okf/
├── index.md            # root listing + okf_version: "0.1"
├── log.md              # generation / enrichment log (ISO-dated)
├── overview.md         # the root "Project" / "Data Project" concept
├── dependencies.md     # parsed manifests (git/local)
├── docs/…              # documentation concepts
├── modules/…           # per-directory code concepts (git/local)
├── datasets/… tables/… # database / BigQuery concepts
├── collections/…       # Firestore concepts
├── pages/…             # web page concepts
└── graph.html          # (after `visualize`) the interactive viewer
```

Every concept carries the required `type` frontmatter field plus recommended
`title`/`description`/`resource`/`tags`/`timestamp`, and bodies use the
conventional OKF `# Schema`, `# Examples`, `# Citations`, `# Joins` headings.

---

## Design notes

- **Deterministic by default.** git/local/web/schema run on the **standard
  library alone** (zero third-party deps). Cloud SDKs and the LLM are optional
  extras, loaded lazily and off unless you ask.
- **Producer/consumer split.** Consumers depend only on markdown + frontmatter
  (`okfgen/consumer.py`), never on producer internals.
- **Scriptable.** Every command prints its primary output path to **stdout** and
  logs to **stderr**: `BUNDLE=$(okfgen generate ./repo)`.

## Development

```bash
pip install -e '.[dev]'
pytest
```

## License

Apache-2.0.
