-- ============================================================
-- Retail Sample Database — Schema
-- FlowForge sample data for report and pipeline testing
-- ============================================================

CREATE TABLE customers (
    customer_id  SERIAL       PRIMARY KEY,
    first_name   VARCHAR(50)  NOT NULL,
    last_name    VARCHAR(50)  NOT NULL,
    email        VARCHAR(100) NOT NULL UNIQUE,
    region       VARCHAR(20)  NOT NULL,   -- North | South | East | West
    age_group    VARCHAR(10)  NOT NULL,   -- 18-25 | 26-35 | 36-50 | 51+
    join_date    DATE         NOT NULL,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE products (
    product_id   SERIAL        PRIMARY KEY,
    name         VARCHAR(100)  NOT NULL,
    category     VARCHAR(30)   NOT NULL,  -- Electronics | Clothing | Home & Garden | Sports | Books
    price        NUMERIC(10,2) NOT NULL,
    cost         NUMERIC(10,2) NOT NULL,
    stock_level  INTEGER       NOT NULL DEFAULT 0,
    created_at   TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE TABLE orders (
    order_id        SERIAL        PRIMARY KEY,
    customer_id     INTEGER       NOT NULL REFERENCES customers(customer_id),
    status          VARCHAR(20)   NOT NULL,  -- pending | shipped | delivered | returned | cancelled
    order_total     NUMERIC(10,2) NOT NULL,
    discount_amount NUMERIC(10,2) NOT NULL DEFAULT 0,
    shipping_cost   NUMERIC(10,2) NOT NULL DEFAULT 5.99,
    order_date      TIMESTAMP     NOT NULL,
    shipped_date    TIMESTAMP,
    delivered_date  TIMESTAMP,
    created_at      TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE TABLE order_items (
    item_id      SERIAL        PRIMARY KEY,
    order_id     INTEGER       NOT NULL REFERENCES orders(order_id),
    product_id   INTEGER       NOT NULL REFERENCES products(product_id),
    quantity     INTEGER       NOT NULL DEFAULT 1,
    unit_price   NUMERIC(10,2) NOT NULL,
    line_total   NUMERIC(10,2) NOT NULL,
    created_at   TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE TABLE returns (
    return_id     SERIAL        PRIMARY KEY,
    order_id      INTEGER       NOT NULL REFERENCES orders(order_id),
    customer_id   INTEGER       NOT NULL REFERENCES customers(customer_id),
    reason        VARCHAR(30)   NOT NULL,  -- defective | wrong_item | not_as_described | changed_mind | damaged
    refund_amount NUMERIC(10,2) NOT NULL,
    return_date   TIMESTAMP     NOT NULL,
    status        VARCHAR(20)   NOT NULL DEFAULT 'pending',  -- pending | approved | rejected | refunded
    created_at    TIMESTAMP     NOT NULL DEFAULT NOW()
);

-- Output table for the populate_monthly_revenue() procedure
CREATE TABLE monthly_revenue_summary (
    id          SERIAL        PRIMARY KEY,
    month       DATE          NOT NULL,
    region      VARCHAR(20)   NOT NULL,
    category    VARCHAR(30)   NOT NULL,
    orders      INTEGER       NOT NULL DEFAULT 0,
    revenue     NUMERIC(12,2) NOT NULL DEFAULT 0,
    returns     NUMERIC(12,2) NOT NULL DEFAULT 0,
    net_revenue NUMERIC(12,2) NOT NULL DEFAULT 0,
    created_at  TIMESTAMP     NOT NULL DEFAULT NOW(),
    UNIQUE (month, region, category)
);

-- Indexes for common query patterns
CREATE INDEX idx_orders_customer      ON orders(customer_id);
CREATE INDEX idx_orders_date          ON orders(order_date);
CREATE INDEX idx_orders_status        ON orders(status);
CREATE INDEX idx_order_items_order    ON order_items(order_id);
CREATE INDEX idx_order_items_product  ON order_items(product_id);
CREATE INDEX idx_returns_order        ON returns(order_id);
CREATE INDEX idx_customers_region     ON customers(region);
CREATE INDEX idx_customers_age_group  ON customers(age_group);
CREATE INDEX idx_products_category    ON products(category);
