-- Run this against your FlowForge PostgreSQL database to create the target table.
-- psql -U flowforge -d flowforge -f setup_table.sql

DROP TABLE IF EXISTS public.bulk_test_subscribers;

CREATE TABLE public.bulk_test_subscribers (
    subscriber_id   VARCHAR(20)     NOT NULL,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    email           VARCHAR(255),
    plan            VARCHAR(50),
    start_date      DATE,
    monthly_amount  NUMERIC(10, 2),
    status          VARCHAR(20),
    loaded_at       TIMESTAMP DEFAULT NOW()   -- FlowForge appends this automatically
);

-- Quick check after loading:
-- SELECT plan, status, COUNT(*), SUM(monthly_amount) AS mrr
-- FROM public.bulk_test_subscribers
-- GROUP BY plan, status
-- ORDER BY plan, status;
