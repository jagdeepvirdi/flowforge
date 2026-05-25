-- ============================================================
-- Retail Sample Database — Seed Data
-- Generates: 300 customers, ~1,200 orders, ~3,400 items, ~120 returns
--
-- Data patterns embedded (for AI analysis):
--   • North region order share drops from ~25% → ~9% after Aug 2025
--   • Holiday spike: Nov/Dec ~80% above average monthly volume
--   • Post-holiday dip: Jan/Feb lowest-volume months
--   • ~38% of orders qualify for free shipping
--   • ~28% of orders include a discount
-- ============================================================

DO $$
DECLARE
  -- First names (40)
  fn TEXT[] := ARRAY[
    'James','Mary','John','Patricia','Robert','Jennifer','Michael','Linda','William','Barbara',
    'David','Susan','Richard','Jessica','Joseph','Sarah','Thomas','Karen','Charles','Lisa',
    'Emma','Noah','Olivia','Liam','Ava','Sophia','Mia','Charlotte','Amelia','Lucas',
    'Mason','Ethan','Oliver','Aiden','Elijah','Logan','Benjamin','Emily','Hannah','Chloe'
  ];
  -- Last names (40)
  ln TEXT[] := ARRAY[
    'Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis','Rodriguez','Martinez',
    'Hernandez','Lopez','Gonzalez','Wilson','Anderson','Thomas','Taylor','Moore','Jackson','Martin',
    'Lee','Perez','Thompson','White','Harris','Sanchez','Clark','Ramirez','Lewis','Robinson',
    'Walker','Young','Allen','King','Wright','Scott','Torres','Nguyen','Hill','Flores'
  ];

  -- Loop counters
  i INT; j INT; k INT;

  -- Working variables
  r           FLOAT;
  v_region    TEXT;
  v_age       TEXT;
  v_cid       INT;
  v_pid       INT;
  v_oid       INT;
  v_odate     TIMESTAMP;
  v_status    TEXT;
  v_qty       INT;
  v_price     NUMERIC(10,2);
  v_ltotal    NUMERIC(10,2);
  v_ototal    NUMERIC(10,2);
  v_nitems    INT;
  v_mdate     DATE;
  v_nmth      INT;
  v_norders   INT;
  v_nshare    FLOAT;
  v_fname     TEXT;
  v_lname     TEXT;
  v_email     TEXT;
  v_jdays     INT;
  v_agemths   FLOAT;
  v_disc      NUMERIC(10,2);
  v_ship      NUMERIC(10,2);
  v_shipped   TIMESTAMP;
  v_delivered TIMESTAMP;
BEGIN
  PERFORM setseed(0.42);

  -- ==================================================================
  -- CUSTOMERS (300)
  -- Distribution: North 23%, South 30%, East 27%, West 20%
  -- Age groups:   18-25 20%, 26-35 35%, 36-50 30%, 51+ 15%
  -- Join dates:   spread over the past 2 years
  -- ==================================================================
  FOR i IN 1..300 LOOP
    r := random();
    v_region := CASE
      WHEN r < 0.23 THEN 'North'
      WHEN r < 0.53 THEN 'South'
      WHEN r < 0.80 THEN 'East'
      ELSE 'West'
    END;

    r := random();
    v_age := CASE
      WHEN r < 0.20 THEN '18-25'
      WHEN r < 0.55 THEN '26-35'
      WHEN r < 0.85 THEN '36-50'
      ELSE '51+'
    END;

    v_fname := fn[1 + floor(random() * array_length(fn, 1))::INT];
    v_lname := ln[1 + floor(random() * array_length(ln, 1))::INT];
    v_email := lower(v_fname) || '.' || lower(v_lname) || i || '@shopexample.com';
    v_jdays := (random() * 730)::INT;

    INSERT INTO customers (first_name, last_name, email, region, age_group, join_date, created_at, updated_at)
    VALUES (
      v_fname, v_lname, v_email, v_region, v_age,
      CURRENT_DATE - v_jdays,
      NOW() - (v_jdays || ' days')::INTERVAL,
      NOW() - (v_jdays || ' days')::INTERVAL
    );
  END LOOP;

  -- ==================================================================
  -- ORDERS + ORDER ITEMS
  -- Months 0–17 = November 2024 through May 2026
  --
  -- Volume per month:
  --   Nov/Dec  → 90–115 orders  (holiday spike)
  --   Jan/Feb  → 38–48 orders   (post-holiday dip)
  --   Other    → 52–67 orders   (baseline)
  --
  -- North share:
  --   Months  0–8  (Nov 2024 – Jul 2025) → ~25% of orders
  --   Months  9–17 (Aug 2025 – May 2026) → ~9%  of orders  (declining)
  -- ==================================================================
  FOR v_nmth IN 0..17 LOOP
    v_mdate := ('2024-11-01'::DATE + (v_nmth || ' months')::INTERVAL)::DATE;

    v_norders := CASE
      WHEN EXTRACT(MONTH FROM v_mdate) IN (11, 12) THEN 90  + (random() * 25)::INT
      WHEN EXTRACT(MONTH FROM v_mdate) IN (1,  2)  THEN 38  + (random() * 10)::INT
      ELSE                                               52  + (random() * 15)::INT
    END;

    v_nshare := CASE WHEN v_nmth <= 8 THEN 0.25 ELSE 0.09 END;

    FOR j IN 1..v_norders LOOP

      -- Pick region (North share declines in second half)
      r := random();
      v_region := CASE
        WHEN r < v_nshare            THEN 'North'
        WHEN r < v_nshare + 0.32     THEN 'South'
        WHEN r < v_nshare + 0.59     THEN 'East'
        ELSE                              'West'
      END;

      -- Pick a customer from this region
      SELECT customer_id INTO v_cid
      FROM   customers
      WHERE  region = v_region
      ORDER  BY random()
      LIMIT  1;

      -- Random timestamp within the month (days 1–28)
      v_odate := v_mdate::TIMESTAMP
               + ((random() * 27)::INT    || ' days')::INTERVAL
               + ((random() * 86399)::INT || ' seconds')::INTERVAL;

      -- Order status determined by how old the order is
      v_agemths := EXTRACT(EPOCH FROM (NOW() - v_odate)) / 2592000.0;
      r := random();
      v_status := CASE
        WHEN v_agemths > 3 THEN
          CASE WHEN r < 0.78 THEN 'delivered'
               WHEN r < 0.90 THEN 'returned'
               WHEN r < 0.97 THEN 'cancelled'
               ELSE               'shipped'  END
        WHEN v_agemths > 1 THEN
          CASE WHEN r < 0.62 THEN 'delivered'
               WHEN r < 0.78 THEN 'shipped'
               WHEN r < 0.88 THEN 'returned'
               WHEN r < 0.96 THEN 'cancelled'
               ELSE               'pending'  END
        ELSE
          CASE WHEN r < 0.30 THEN 'delivered'
               WHEN r < 0.68 THEN 'shipped'
               WHEN r < 0.86 THEN 'pending'
               WHEN r < 0.95 THEN 'cancelled'
               ELSE               'returned' END
      END;

      v_disc  := CASE WHEN random() < 0.28 THEN round((random() * 20)::NUMERIC, 2) ELSE 0.00 END;
      v_ship  := CASE WHEN random() < 0.38 THEN 0.00 ELSE 5.99 END;

      v_shipped := CASE WHEN v_status IN ('shipped','delivered','returned')
                        THEN v_odate + ((1 + (random() * 3)::INT) || ' days')::INTERVAL
                        ELSE NULL END;

      v_delivered := CASE WHEN v_status IN ('delivered','returned')
                          THEN v_odate + ((3 + (random() * 7)::INT) || ' days')::INTERVAL
                          ELSE NULL END;

      INSERT INTO orders (
        customer_id, status, order_total, discount_amount, shipping_cost,
        order_date, shipped_date, delivered_date, created_at, updated_at
      ) VALUES (
        v_cid, v_status, 0, v_disc, v_ship,
        v_odate, v_shipped, v_delivered, v_odate, v_odate
      )
      RETURNING order_id INTO v_oid;

      -- Order items: 1–4 items per order
      v_nitems := 1 + (random() * 3)::INT;
      v_ototal := 0;

      FOR k IN 1..v_nitems LOOP
        SELECT product_id, price INTO v_pid, v_price
        FROM   products
        ORDER  BY random()
        LIMIT  1;

        v_qty    := 1 + (random() * 1.5)::INT;   -- mostly 1, occasionally 2
        v_ltotal := round(v_price * v_qty, 2);
        v_ototal := v_ototal + v_ltotal;

        INSERT INTO order_items (order_id, product_id, quantity, unit_price, line_total, created_at)
        VALUES (v_oid, v_pid, v_qty, v_price, v_ltotal, v_odate);
      END LOOP;

      UPDATE orders
      SET    order_total = round(v_ototal - v_disc + v_ship, 2)
      WHERE  order_id = v_oid;

    END LOOP;
  END LOOP;

  -- ==================================================================
  -- RETURNS — one record per 'returned' order
  -- Reason mix: defective 30%, changed_mind 25%, wrong_item 20%,
  --             not_as_described 15%, damaged 10%
  -- Status mix: refunded 50%, approved 25%, pending 15%, rejected 10%
  -- ==================================================================
  INSERT INTO returns (order_id, customer_id, reason, refund_amount, return_date, status, created_at)
  SELECT
    o.order_id,
    o.customer_id,
    (ARRAY['defective','defective','defective',
           'changed_mind','changed_mind',
           'wrong_item','wrong_item',
           'not_as_described',
           'damaged'])[1 + floor(random() * 9)::INT],
    round((o.order_total * (0.80 + random() * 0.20))::NUMERIC, 2),
    o.delivered_date + ((2 + floor(random() * 14)::INT) || ' days')::INTERVAL,
    (ARRAY['refunded','refunded','refunded','refunded','refunded',
           'approved','approved','approved','approved','approved',
           'pending','pending','pending',
           'rejected','rejected'])[1 + floor(random() * 15)::INT],
    NOW()
  FROM   orders o
  WHERE  o.status = 'returned'
    AND  o.delivered_date IS NOT NULL
  ORDER  BY o.order_id;   -- deterministic scan order for reproducibility

END $$;
