---
type: Table
title: sales.order_items
description: Line items belonging to an order; the fact grain of the warehouse.
tags:
  - database
  - table
  - sales
timestamp: "2026-07-01T00:00:00+00:00"
---

# Examples

- **Rows:** 4,381,992

# Schema

| Column | Type | Mode | Description |
|---|---|---|---|
| `order_item_id` | STRING | REQUIRED | Primary key for the line item. |
| `order_id` | STRING | REQUIRED | Parent order (FK to orders). |
| `product_id` | STRING | REQUIRED | Product sold (FK to products). |
| `quantity` | INT64 | REQUIRED | Units purchased. |
| `line_total` | NUMERIC | REQUIRED | quantity * unit_price at time of sale. |

# Joins

- `order_id` → [sales.orders](/tables/sales-orders.md)
- `product_id` → [sales.products](/tables/sales-products.md)

# Related

Referenced by:
- [sales](/datasets/sales.md)
