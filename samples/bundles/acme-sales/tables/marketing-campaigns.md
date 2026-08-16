---
type: Table
title: marketing.campaigns
description: Marketing campaigns Acme has run.
tags:
  - database
  - table
  - marketing
generated:
  by: okfgen/0.1.1
  at: "2026-07-01T00:00:00+00:00"
---

# Examples

- **Rows:** 340

# Schema

| Column | Type | Mode | Description |
|---|---|---|---|
| `campaign_id` | STRING | REQUIRED | Primary key. |
| `channel` | STRING | REQUIRED | Acquisition channel (email, paid, social). |
| `started_at` | DATE | REQUIRED | Launch date. |

# Related

Referenced by:
- [marketing](/datasets/marketing.md)
- [marketing.touchpoints](/tables/marketing-touchpoints.md)
