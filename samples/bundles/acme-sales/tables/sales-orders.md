---
type: Table
title: sales.orders
description: One row per completed customer order.
tags:
  - database
  - table
  - sales
timestamp: "2026-07-01T00:00:00+00:00"
---

# Examples

- **Rows:** 992,104

# Schema

| Column | Type | Mode | Description |
|---|---|---|---|
| `order_id` | STRING | REQUIRED | Primary key for the order. |
| `customer_id` | STRING | REQUIRED | The customer who placed the order (FK to customers). |
| `status` | STRING | REQUIRED | Order lifecycle status. |
| `total_amount` | NUMERIC | REQUIRED | Order total in USD. |
| `ordered_at` | TIMESTAMP | REQUIRED | When the order was placed. |

# Joins

- `customer_id` → [sales.customers](/tables/sales-customers.md)

# Related

Referenced by:
- [sales](/datasets/sales.md)
- [sales.order_items](/tables/sales-order-items.md)
