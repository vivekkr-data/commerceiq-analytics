-- CommerceIQ Analytics PostgreSQL source-layer schema.

CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    customer_unique_id VARCHAR(32) NOT NULL,
    customer_zip_code_prefix INTEGER NOT NULL,
    customer_city TEXT NOT NULL,
    customer_state CHAR(2) NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(32) PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL REFERENCES customers(customer_id),
    order_status VARCHAR(20) NOT NULL,
    order_purchase_timestamp TIMESTAMP NOT NULL,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(32) PRIMARY KEY,
    product_category_name TEXT,
    product_name_lenght NUMERIC,
    product_description_lenght NUMERIC,
    product_photos_qty NUMERIC,
    product_weight_g NUMERIC,
    product_length_cm NUMERIC,
    product_height_cm NUMERIC,
    product_width_cm NUMERIC
);

CREATE TABLE IF NOT EXISTS sellers (
    seller_id VARCHAR(32) PRIMARY KEY,
    seller_zip_code_prefix INTEGER NOT NULL,
    seller_city TEXT NOT NULL,
    seller_state CHAR(2) NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    order_id VARCHAR(32) NOT NULL REFERENCES orders(order_id),
    order_item_id INTEGER NOT NULL,
    product_id VARCHAR(32) NOT NULL REFERENCES products(product_id),
    seller_id VARCHAR(32) NOT NULL REFERENCES sellers(seller_id),
    shipping_limit_date TIMESTAMP NOT NULL,
    price NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
    freight_value NUMERIC(12, 2) NOT NULL CHECK (freight_value >= 0),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE IF NOT EXISTS order_payments (
    order_id VARCHAR(32) NOT NULL REFERENCES orders(order_id),
    payment_sequential INTEGER NOT NULL,
    payment_type VARCHAR(30) NOT NULL,
    payment_installments INTEGER NOT NULL CHECK (payment_installments >= 0),
    payment_value NUMERIC(12, 2) NOT NULL CHECK (payment_value >= 0),
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE IF NOT EXISTS order_reviews (
    review_row_id BIGSERIAL PRIMARY KEY,
    review_id VARCHAR(32) NOT NULL,
    order_id VARCHAR(32) NOT NULL REFERENCES orders(order_id),
    review_score INTEGER NOT NULL CHECK (review_score BETWEEN 1 AND 5),
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP NOT NULL,
    review_answer_timestamp TIMESTAMP NOT NULL,
    UNIQUE (review_id, order_id)
);

CREATE TABLE IF NOT EXISTS geolocation (
    geolocation_row_id BIGSERIAL PRIMARY KEY,
    geolocation_zip_code_prefix INTEGER NOT NULL,
    geolocation_lat DOUBLE PRECISION NOT NULL,
    geolocation_lng DOUBLE PRECISION NOT NULL,
    geolocation_city TEXT NOT NULL,
    geolocation_state CHAR(2) NOT NULL
);

CREATE TABLE IF NOT EXISTS product_category_translation (
    product_category_name TEXT PRIMARY KEY,
    product_category_name_english TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_customers_unique_id ON customers(customer_unique_id);
CREATE INDEX IF NOT EXISTS idx_customers_state ON customers(customer_state);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_purchase ON orders(order_purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status);
CREATE INDEX IF NOT EXISTS idx_items_product ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_items_seller ON order_items(seller_id);
CREATE INDEX IF NOT EXISTS idx_reviews_order ON order_reviews(order_id);
CREATE INDEX IF NOT EXISTS idx_geo_zip ON geolocation(geolocation_zip_code_prefix);
