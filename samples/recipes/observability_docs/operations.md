# Operations Guide

Running Nimbus in production.

## Retention
Metrics are retained 13 months; logs 30 days by default.

## Rate limits
The [Ingest API](./ingest-api.md) enforces per-key rate limits. Request an
increase from support if you see `429` responses.

## Upgrades
Upgrade the agent described in [Installation](./installation.md) during a
maintenance window.
