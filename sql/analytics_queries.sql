-- 01. Total delivered merchandise revenue.
SELECT SUM(oi.price) AS merchandise_revenue
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered';

-- 02. Total delivered orders.
SELECT COUNT(*) AS delivered_orders FROM orders WHERE order_status = 'delivered';

-- 03. Unique delivered customers using the durable customer identity.
SELECT COUNT(DISTINCT c.customer_unique_id) AS unique_customers
FROM orders o JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered';

-- 04. Average order value from a safe order-item aggregate.
WITH order_revenue AS (
    SELECT oi.order_id, SUM(oi.price) AS merchandise_revenue
    FROM order_items oi JOIN orders o ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered' GROUP BY oi.order_id
)
SELECT AVG(merchandise_revenue) AS average_order_value FROM order_revenue;

-- 05. Monthly delivered merchandise revenue.
SELECT DATE_TRUNC('month', o.order_purchase_timestamp) AS month,
       SUM(oi.price) AS merchandise_revenue
FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY 1 ORDER BY 1;

-- 06. Monthly delivered order count.
SELECT DATE_TRUNC('month', order_purchase_timestamp) AS month, COUNT(*) AS orders
FROM orders WHERE order_status = 'delivered' GROUP BY 1 ORDER BY 1;

-- 07. Month-over-month revenue growth.
WITH monthly AS (
    SELECT DATE_TRUNC('month', o.order_purchase_timestamp) AS month,
           SUM(oi.price) AS revenue
    FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered' GROUP BY 1
), compared AS (
    SELECT month, revenue, LAG(revenue) OVER (ORDER BY month) AS previous_revenue FROM monthly
)
SELECT month, revenue,
       (revenue - previous_revenue) / NULLIF(previous_revenue, 0) AS revenue_growth
FROM compared ORDER BY month;

-- 08. Top categories by delivered merchandise revenue.
SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category,
       SUM(oi.price) AS merchandise_revenue
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
LEFT JOIN product_category_translation t ON t.product_category_name = p.product_category_name
WHERE o.order_status = 'delivered'
GROUP BY 1 ORDER BY 2 DESC LIMIT 15;

-- 09. Top categories by distinct delivered order count.
SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category,
       COUNT(DISTINCT oi.order_id) AS orders
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
LEFT JOIN product_category_translation t ON t.product_category_name = p.product_category_name
WHERE o.order_status = 'delivered'
GROUP BY 1 ORDER BY 2 DESC LIMIT 15;

-- 10. Top sellers by delivered merchandise revenue.
SELECT oi.seller_id, COUNT(DISTINCT oi.order_id) AS orders, SUM(oi.price) AS merchandise_revenue
FROM order_items oi JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY oi.seller_id ORDER BY merchandise_revenue DESC LIMIT 20;

-- 11. Highest-rated categories with at least 100 reviewed orders.
WITH latest_review AS (
    SELECT DISTINCT ON (order_id) order_id, review_score
    FROM order_reviews ORDER BY order_id, review_answer_timestamp DESC, review_id DESC
), category_order AS (
    SELECT DISTINCT oi.order_id,
           COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category
    FROM order_items oi JOIN products p ON p.product_id = oi.product_id
    LEFT JOIN product_category_translation t ON t.product_category_name = p.product_category_name
)
SELECT co.category, COUNT(*) AS reviewed_orders, AVG(lr.review_score) AS average_review
FROM category_order co JOIN latest_review lr ON lr.order_id = co.order_id
GROUP BY co.category HAVING COUNT(*) >= 100 ORDER BY average_review DESC;

-- 12. Customers by state.
SELECT customer_state, COUNT(DISTINCT customer_unique_id) AS customers
FROM customers GROUP BY customer_state ORDER BY customers DESC;

-- 13. Delivered merchandise revenue by customer state.
SELECT c.customer_state, SUM(oi.price) AS merchandise_revenue
FROM customers c JOIN orders o ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state ORDER BY merchandise_revenue DESC;

-- 14. Repeat-customer rate based on customer_unique_id.
WITH customer_orders AS (
    SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS orders
    FROM customers c JOIN orders o ON o.customer_id = c.customer_id
    GROUP BY c.customer_unique_id
)
SELECT AVG(CASE WHEN orders > 1 THEN 1.0 ELSE 0.0 END) AS repeat_customer_rate
FROM customer_orders;

-- 15. Payment method distribution without joining to item rows.
SELECT payment_type, COUNT(*) AS payment_records, SUM(payment_value) AS amount_paid
FROM order_payments GROUP BY payment_type ORDER BY payment_records DESC;
