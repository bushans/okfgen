---
type: Table
title: sales.customers
description: One row per registered Acme customer.
tags:
  - database
  - table
  - sales
timestamp: "2026-07-01T00:00:00+00:00"
---

# Examples

- **Rows:** 184,203

# Schema

| Column | Type | Mode | Description |
|---|---|---|---|
| `customer_id` | STRING | REQUIRED | Globally unique customer identifier (primary key). |
| `email` | STRING | NULLABLE | Account email address. |
| `country` | STRING | NULLABLE | ISO-3166 country code of the billing address. |
| `created_at` | TIMESTAMP | REQUIRED | When the account was created. |

# Related

Referenced by:
- [sales](/datasets/sales.md)
- [marketing.touchpoints](/tables/marketing-touchpoints.md)
- [sales.orders](/tables/sales-orders.md)
