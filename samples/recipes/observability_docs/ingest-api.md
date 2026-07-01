# Ingest API

The Ingest API accepts metrics, logs, and traces over HTTPS.

## Endpoints
- `POST /v1/metrics` — push metric samples
- `POST /v1/logs` — push structured log lines
- `POST /v1/traces` — push spans

Data sent here becomes queryable in [Dashboards](./dashboards.md). Rate limits
and retention are covered in the [Operations Guide](./operations.md).
