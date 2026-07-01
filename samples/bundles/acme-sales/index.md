---
okf_version: "0.1"
---

# Acme Sales

Warehouse of Acme's e-commerce sales data: customers, orders, order items, and products.

_Source: schema://acme_

## Root

- [Acme Sales](/overview.md) — Warehouse of Acme's e-commerce sales data: customers, orders, order items, and products.

## Datasets

- [marketing](/datasets/marketing.md) — Marketing attribution linking campaigns to customers.
- [sales](/datasets/sales.md) — Transactional sales facts and the dimensions they reference.

## Tables

- [marketing.campaigns](/tables/marketing-campaigns.md) — Marketing campaigns Acme has run.
- [marketing.touchpoints](/tables/marketing-touchpoints.md) — Customer interactions attributed to a campaign.
- [sales.customers](/tables/sales-customers.md) — One row per registered Acme customer.
- [sales.order_items](/tables/sales-order-items.md) — Line items belonging to an order; the fact grain of the warehouse.
- [sales.orders](/tables/sales-orders.md) — One row per completed customer order.
- [sales.products](/tables/sales-products.md) — Catalog of sellable products.
