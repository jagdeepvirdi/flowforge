-- ============================================================
-- Retail Sample Database — Stored Procedures
--
-- Three procedures matching FlowForge manual test scenarios:
--
--   refresh_category_stats(p_category)  → section 4a  (RAISE NOTICE pattern)
--   populate_monthly_revenue(p_month)   → section 4a  (writes to summary table)
--   update_inventory_levels()           → section 4a  (updates products table)
-- ============================================================


-- ------------------------------------------------------------
-- 1. refresh_category_stats
--    Mirrors the manual test guide section 4a pattern exactly.
--    Use in FlowForge DB Procedure step:
--      Procedure : public.refresh_category_stats
--      Parameters: { "p_category": "Electronics" }
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.refresh_category_stats(p_category TEXT DEFAULT 'ALL')
RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
  RAISE NOTICE 'refresh_category_stats: processing category=''%''', p_category;

  -- Simulate work (in a real system this would refresh a materialized view)
  PERFORM COUNT(*) FROM products
  WHERE (p_category = 'ALL' OR category = p_category);

  RAISE NOTICE 'refresh_category_stats: complete';
END;
$$;


-- ------------------------------------------------------------
-- 2. populate_monthly_revenue
--    Aggregates order/return data into monthly_revenue_summary.
--    Returns the number of rows inserted.
--
--    Use in FlowForge DB Procedure step:
--      Procedure : public.populate_monthly_revenue
--      Parameters: { "p_month": "2025-11-01" }
--
--    Then query monthly_revenue_summary for reports.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.populate_monthly_revenue(p_month DATE)
RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
  v_rows INT;
  v_month DATE := DATE_TRUNC('month', p_month)::DATE;
BEGIN
  RAISE NOTICE 'populate_monthly_revenue: processing %', v_month;

  -- Replace existing rows for this month
  DELETE FROM monthly_revenue_summary WHERE month = v_month;

  INSERT INTO monthly_revenue_summary (month, region, category, orders, revenue, returns, net_revenue)
  SELECT
    v_month,
    c.region,
    p.category,
    COUNT(DISTINCT o.order_id)             AS orders,
    COALESCE(SUM(oi.line_total),      0)   AS revenue,
    COALESCE(SUM(r.refund_amount),    0)   AS returns,
    COALESCE(SUM(oi.line_total), 0)
      - COALESCE(SUM(r.refund_amount), 0)  AS net_revenue
  FROM   orders o
  JOIN   customers   c  ON  c.customer_id  = o.customer_id
  JOIN   order_items oi ON  oi.order_id    = o.order_id
  JOIN   products    p  ON  p.product_id   = oi.product_id
  LEFT   JOIN returns r ON  r.order_id     = o.order_id
  WHERE  DATE_TRUNC('month', o.order_date) = v_month
    AND  o.status NOT IN ('cancelled', 'pending')
  GROUP  BY c.region, p.category;

  GET DIAGNOSTICS v_rows = ROW_COUNT;
  RAISE NOTICE 'populate_monthly_revenue: inserted % rows for %', v_rows, v_month;
  RETURN v_rows;
END;
$$;


-- ------------------------------------------------------------
-- 3. update_inventory_levels
--    Deducts quantities sold (shipped + delivered orders in the
--    last 30 days) from products.stock_level.
--    Returns count of products updated.
--
--    Use in FlowForge DB Procedure step:
--      Procedure : public.update_inventory_levels
--      Parameters: {}
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.update_inventory_levels()
RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
  v_updated INT;
BEGIN
  RAISE NOTICE 'update_inventory_levels: calculating recent sales...';

  WITH recent_sales AS (
    SELECT  oi.product_id,
            SUM(oi.quantity) AS qty_sold
    FROM    order_items oi
    JOIN    orders o ON o.order_id = oi.order_id
    WHERE   o.status     IN ('shipped', 'delivered')
      AND   o.order_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP   BY oi.product_id
  )
  UPDATE products p
  SET    stock_level = GREATEST(0, p.stock_level - rs.qty_sold),
         updated_at  = NOW()
  FROM   recent_sales rs
  WHERE  p.product_id = rs.product_id;

  GET DIAGNOSTICS v_updated = ROW_COUNT;
  RAISE NOTICE 'update_inventory_levels: updated stock for % products', v_updated;
  RETURN v_updated;
END;
$$;
