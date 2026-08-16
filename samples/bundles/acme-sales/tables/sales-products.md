---
type: Table
title: sales.products
description: Catalog of sellable products.
tags:
  - database
  - table
  - sales
generated:
  by: okfgen/0.1.2
  at: "2026-07-01T00:00:00+00:00"
---

# Examples

- **Rows:** 5,231

# Schema

| Column | Type | Mode | Description |
|---|---|---|---|
| `product_id` | STRING | REQUIRED | Primary key for the product. |
| `name` | STRING | REQUIRED | Display name. |
| `category` | STRING | NULLABLE | Merchandising category. |
| `unit_price` | NUMERIC | REQUIRED | List price in USD. |

# Related

Referenced by:
- [sales](/datasets/sales.md)
- [sales.order_items](/tables/sales-order-items.md)
