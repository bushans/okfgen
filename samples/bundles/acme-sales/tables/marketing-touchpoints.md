---
type: Table
title: marketing.touchpoints
description: Customer interactions attributed to a campaign.
tags:
  - database
  - table
  - marketing
timestamp: "2026-07-01T00:00:00+00:00"
---

# Examples

- **Rows:** 2,100,553

# Schema

| Column | Type | Mode | Description |
|---|---|---|---|
| `touchpoint_id` | STRING | REQUIRED | Primary key. |
| `customer_id` | STRING | REQUIRED | Customer touched (FK to customers). |
| `campaign_id` | STRING | REQUIRED | Campaign responsible (FK to campaigns). |
| `occurred_at` | TIMESTAMP | REQUIRED | When the touch happened. |

# Joins

- `customer_id` → [sales.customers](/tables/sales-customers.md)
- `campaign_id` → [marketing.campaigns](/tables/marketing-campaigns.md)

# Related

Referenced by:
- [marketing](/datasets/marketing.md)
