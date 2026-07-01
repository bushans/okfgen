# okfgen sample bundles

Three ready-to-browse OKF bundles, each demonstrating a different **producer**
perspective from the [OKF blog post](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/),
paired with the **recipe** that produced it. They are committed so you can
browse them without running anything.

| Bundle | Producer perspective | Recipe |
|---|---|---|
| [`bundles/acme-sales/`](bundles/acme-sales) | **A database** — datasets, tables, column schemas, and inferred join paths | [`recipes/acme_sales.schema.json`](recipes/acme_sales.schema.json) |
| [`bundles/petclinic-api/`](bundles/petclinic-api) | **A source system** — a code repo's structure, modules, and dependencies | [`recipes/petclinic_app/`](recipes/petclinic_app) |
| [`bundles/observability-docs/`](bundles/observability-docs) | **A documentation site** — cross-linked docs pages | [`recipes/observability_docs/`](recipes/observability_docs) |
| [`bundles/toronto-beaches/`](bundles/toronto-beaches) | **A live public dataset** — Toronto Beaches Water Quality (E. coli readings) via CKAN | [`build_live_samples.py`](build_live_samples.py) |

Each bundle also ships a self-contained **`graph.html`** — open it in any browser
to explore the knowledge graph (no server, no build step, no data leaves the page).

## Browse them

```bash
# Interactive viewer — just open the file:
open samples/bundles/acme-sales/graph.html        # macOS
start samples/bundles/acme-sales/graph.html       # Windows

# Or point the consumers at a bundle:
okfgen search samples/bundles/acme-sales "orders"
okfgen ask    samples/bundles/acme-sales "how do orders relate to customers?"
okfgen validate samples/bundles/observability-docs
```

## The `acme-sales` bundle shows enrichment

It is generated from a schema file (the *draft* pass) and then run through the
**enrichment agent** (pass 2), which inferred the foreign-key **join paths**
between tables — e.g. `orders.customer_id → customers` — and added **backlinks**.
Look at [`bundles/acme-sales/tables/sales-orders.md`](bundles/acme-sales/tables/sales-orders.md)
for the `# Joins` and `# Related` sections the agent added.

## Rebuild

The build is deterministic (a fixed timestamp is used), so regenerating produces
a clean git diff:

```bash
python samples/build_samples.py
```

This regenerates the three offline bundles, runs the enrichment agent on
`acme-sales`, writes each `graph.html`, and validates every bundle.

## The live `toronto-beaches` bundle

Generated from a **real, live** open-data portal (no auth, no cloud account):

```bash
python samples/build_live_samples.py
# or point it at any CKAN dataset anywhere:
python samples/build_live_samples.py ckan:https://<portal>/dataset/<slug>
```

CKAN powers thousands of government open-data portals, so the same `ckan:` source
works against data.gov, data.gov.au, the EU Open Data Portal, and hundreds of
city portals. Each resource concept includes a **live column schema and example
rows** pulled from the CKAN DataStore. The committed copy is a snapshot; re-run
to refresh it. Try it:

```bash
okfgen ask samples/bundles/toronto-beaches "which column has E. coli readings?"
```
