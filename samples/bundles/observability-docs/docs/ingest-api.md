---
type: Document
title: Ingest API
description: Documentation file `ingest-api.md`.
resource: ingest-api.md
tags:
  - documentation
sources:
  - resource: ingest-api.md
    title: ingest-api.md
    last_modified: 2026-07-01
generated:
  by: okfgen/0.1.2
  at: "2026-07-01T00:00:00+00:00"
---

# Ingest API

The Ingest API accepts metrics, logs, and traces over HTTPS.

## Endpoints
- `POST /v1/metrics` — push metric samples
- `POST /v1/logs` — push structured log lines
- `POST /v1/traces` — push spans

Data sent here becomes queryable in [Dashboards](./dashboards.md). Rate limits
and retention are covered in the [Operations Guide](./operations.md).
