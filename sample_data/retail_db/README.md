# Retail Sample Database

A Docker-based PostgreSQL database with realistic retail/e-commerce data for testing FlowForge pipelines and reports.

## Quick Start

```powershell
docker-compose -f docker-compose.sample-db.yml up -d
```

First startup takes ~15–30 seconds to seed the data. Check progress:
```powershell
docker logs flowforge_retail_sample --follow
```

Stop (keeps data):
```powershell
docker-compose -f docker-compose.sample-db.yml stop
```

Destroy and re-seed from scratch:
```powershell
docker-compose -f docker-compose.sample-db.yml down -v
docker-compose -f docker-compose.sample-db.yml up -d
```

---

## FlowForge Connection Config

| Field    | Value           |
|----------|-----------------|
| Name     | Retail Sample   |
| Type     | PostgreSQL      |
| Host     | localhost       |
| Port     | **5439**        |
| Database | retail_sample   |
| Username | retail          |
| Password | retail123       |

---

## Schema

| Table                    | Rows (approx) | Description                                       |
|--------------------------|---------------|---------------------------------------------------|
| `customers`              | 300           | Name, region, age group, join date                |
| `products`               | 80            | 5 categories, price, cost, stock level            |
| `orders`                 | ~1,200        | Nov 2024 – May 2026, status, totals, dates        |
| `order_items`            | ~3,400        | Line items linking orders to products             |
| `returns`                | ~120          | Reason codes, refund amounts, approval status     |
| `monthly_revenue_summary`| 0 (procedure) | Populated by `populate_monthly_revenue()`         |

### Regions
`North` · `South` · `East` · `West`

### Product Categories
`Electronics` · `Clothing` · `Home & Garden` · `Sports` · `Books`

### Order Statuses
`pending` · `shipped` · `delivered` · `returned` · `cancelled`

---

## Stored Procedures

### `public.refresh_category_stats(p_category TEXT)`
Notification procedure — mirrors FlowForge manual test guide section 4a.
```json
{ "p_category": "Electronics" }
```

### `public.populate_monthly_revenue(p_month DATE)`
Aggregates orders and returns into `monthly_revenue_summary`. Returns row count.
```json
{ "p_month": "2025-11-01" }
```

### `public.update_inventory_levels()`
Deducts 30-day shipped/delivered quantities from `products.stock_level`. Returns updated count.
```json
{}
```

---

## Data Patterns (for AI Analysis)

These patterns are intentionally embedded in the seed data:

| Pattern | Detail |
|---------|--------|
| **North declining** | North's share of orders falls from ~25% → ~9% after August 2025 |
| **Holiday spike** | November and December each have ~80% more orders than average months |
| **Post-holiday dip** | January and February are the lowest-volume months |
| **Discounts** | ~28% of orders include a discount (up to $20 off) |
| **Free shipping** | ~38% of orders have $0 shipping cost |
| **Return volume** | ~10% of orders are returned; reasons: defective, changed mind, wrong item, not as described, damaged |

---

## Useful Queries for FlowForge Reports

### Monthly revenue by region
```sql
SELECT
  DATE_TRUNC('month', o.order_date)::DATE AS month,
  c.region,
  COUNT(DISTINCT o.order_id)              AS orders,
  ROUND(SUM(oi.line_total), 2)            AS gross_revenue,
  ROUND(AVG(o.order_total), 2)            AS avg_order_value
FROM   orders o
JOIN   customers   c  ON c.customer_id = o.customer_id
JOIN   order_items oi ON oi.order_id   = o.order_id
WHERE  o.status NOT IN ('cancelled')
GROUP  BY 1, 2
ORDER  BY 1, 2;
```


### Last One Monthly revenue by region
```sql
SELECT
  DATE_TRUNC('month', o.order_date)::DATE AS month,
  c.region,
  COUNT(DISTINCT o.order_id)              AS orders,
  ROUND(SUM(oi.line_total), 2)            AS gross_revenue,
  ROUND(AVG(o.order_total), 2)            AS avg_order_value
FROM   orders o
JOIN   customers   c  ON c.customer_id = o.customer_id
JOIN   order_items oi ON oi.order_id   = o.order_id
WHERE  o.status NOT IN ('cancelled')
AND  o.order_date >= NOW() - INTERVAL '1 months'
GROUP  BY 1, 2
ORDER  BY 1, 2;
```

### Top 20 products by revenue
```sql
SELECT
  p.name,
  p.category,
  SUM(oi.quantity)                               AS units_sold,
  ROUND(SUM(oi.line_total), 2)                   AS revenue,
  ROUND(SUM(oi.line_total) - SUM(p.cost * oi.quantity), 2) AS gross_profit,
  ROUND((SUM(oi.line_total) - SUM(p.cost * oi.quantity))
        / NULLIF(SUM(oi.line_total), 0) * 100, 1) AS margin_pct
FROM   order_items oi
JOIN   products p ON p.product_id = oi.product_id
JOIN   orders   o ON o.order_id   = oi.order_id
WHERE  o.status IN ('shipped','delivered','returned')
GROUP  BY p.product_id, p.name, p.category
ORDER  BY revenue DESC
LIMIT  20;
```

### Return rate by category
```sql
SELECT
  p.category,
  COUNT(DISTINCT r.return_id)                        AS returns,
  COUNT(DISTINCT o.order_id)                         AS total_orders,
  ROUND(COUNT(DISTINCT r.return_id) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1)  AS return_rate_pct
FROM   orders o
JOIN   order_items oi ON oi.order_id   = o.order_id
JOIN   products    p  ON p.product_id  = oi.product_id
LEFT   JOIN returns r  ON r.order_id   = o.order_id
WHERE  o.status NOT IN ('cancelled','pending')
GROUP  BY p.category
ORDER  BY return_rate_pct DESC;
```

### Customer lifetime value by region and age group
```sql
SELECT
  c.region,
  c.age_group,
  COUNT(DISTINCT c.customer_id)                                  AS customers,
  COUNT(DISTINCT o.order_id)                                     AS total_orders,
  ROUND(SUM(o.order_total) / COUNT(DISTINCT c.customer_id), 2)  AS avg_ltv,
  ROUND(COUNT(DISTINCT o.order_id)
        / COUNT(DISTINCT c.customer_id)::FLOAT, 1)              AS avg_orders_per_customer
FROM   customers c
JOIN   orders    o ON o.customer_id = c.customer_id
WHERE  o.status IN ('delivered','shipped')
GROUP  BY c.region, c.age_group
ORDER  BY c.region, avg_ltv DESC;
```

### North region trend (last 12 months)
```sql
SELECT
  DATE_TRUNC('month', o.order_date)::DATE AS month,
  c.region,
  COUNT(DISTINCT o.order_id)              AS orders
FROM   orders o
JOIN   customers c ON c.customer_id = o.customer_id
WHERE  o.order_date >= NOW() - INTERVAL '12 months'
  AND  o.status NOT IN ('cancelled')
GROUP  BY 1, 2
ORDER  BY 1, 2;
```

### Monthly revenue summary (after running the procedure)
```sql
-- First populate via FlowForge pipeline:
--   DB Procedure step → public.populate_monthly_revenue → { "p_month": "2025-11-01" }

SELECT month, region, category, orders, revenue, returns, net_revenue
FROM   monthly_revenue_summary
ORDER  BY month, region, category;
```

---

## AI Analysis Prompts

Once you have reports running against this DB, feed the results to an AI step with prompts like:

> "Which region shows the clearest decline in order volume over the past 6 months, and what might explain it?"

> "Based on this monthly revenue data, what seasonal patterns can you identify and what should we plan for next quarter?"

> "Which product categories have the highest return rates and what reasons are most common? What actions would you recommend?"

> "Identify the top customer segments by lifetime value and suggest which ones to target for a loyalty programme."

> "Are there any months where revenue and order volume move in opposite directions? What could explain that?"
