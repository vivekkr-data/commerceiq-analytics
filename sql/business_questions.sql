-- 16. Installment behavior by payment type.
SELECT payment_type, payment_installments, COUNT(*) AS payments, AVG(payment_value) AS average_payment
FROM order_payments GROUP BY payment_type, payment_installments
ORDER BY payment_type, payment_installments;

-- 17. Average delivery time for delivered orders.
SELECT AVG(EXTRACT(EPOCH FROM (order_delivered_customer_date - order_purchase_timestamp)) / 86400.0)
       AS average_delivery_days
FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL;

-- 18. Late-delivery rate.
SELECT AVG(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1.0 ELSE 0.0 END)
       AS late_delivery_rate
FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL;

-- 19. Late deliveries by customer state.
SELECT c.customer_state,
       COUNT(*) AS delivered_orders,
       AVG(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1.0 ELSE 0.0 END)
           AS late_delivery_rate
FROM orders o JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
GROUP BY c.customer_state ORDER BY late_delivery_rate DESC;

-- 20. Review-score distribution using raw review rows.
SELECT review_score, COUNT(*) AS reviews FROM order_reviews GROUP BY review_score ORDER BY review_score;

-- 21. Delivery timing versus most recent review score (association only).
WITH latest_review AS (
    SELECT DISTINCT ON (order_id) order_id, review_score
    FROM order_reviews ORDER BY order_id, review_answer_timestamp DESC, review_id DESC
)
SELECT CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 'Late'
            ELSE 'On time or early' END AS delivery_status,
       COUNT(*) AS orders, AVG(lr.review_score) AS average_review
FROM orders o JOIN latest_review lr ON lr.order_id = o.order_id
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
GROUP BY 1;

-- 22. Freight-to-merchandise ratio.
SELECT SUM(oi.freight_value) / NULLIF(SUM(oi.price), 0) AS freight_to_merchandise_ratio
FROM order_items oi JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered';

-- 23. High-value customers by historical delivered spend.
SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS orders, SUM(oi.price) AS historical_spend
FROM customers c JOIN orders o ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_unique_id ORDER BY historical_spend DESC LIMIT 100;

-- 24. Seller scorecard at seller-order grain.
WITH seller_order AS (
    SELECT oi.seller_id, oi.order_id, SUM(oi.price) AS revenue, SUM(oi.freight_value) AS freight
    FROM order_items oi GROUP BY oi.seller_id, oi.order_id
), latest_review AS (
    SELECT DISTINCT ON (order_id) order_id, review_score
    FROM order_reviews ORDER BY order_id, review_answer_timestamp DESC, review_id DESC
)
SELECT so.seller_id, COUNT(*) AS orders, SUM(so.revenue) AS revenue,
       AVG(lr.review_score) AS average_review,
       AVG(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1.0 ELSE 0.0 END)
           AS late_delivery_rate
FROM seller_order so JOIN orders o ON o.order_id = so.order_id
LEFT JOIN latest_review lr ON lr.order_id = so.order_id
WHERE o.order_status = 'delivered'
GROUP BY so.seller_id ORDER BY revenue DESC;

-- 25. Canceled and unavailable orders by month.
SELECT DATE_TRUNC('month', order_purchase_timestamp) AS month, order_status, COUNT(*) AS orders
FROM orders WHERE order_status IN ('canceled', 'unavailable')
GROUP BY 1, 2 ORDER BY 1, 2;

-- 26. Category revenue concentration and cumulative share.
WITH category_revenue AS (
    SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category,
           SUM(oi.price) AS revenue
    FROM order_items oi JOIN orders o ON o.order_id = oi.order_id
    JOIN products p ON p.product_id = oi.product_id
    LEFT JOIN product_category_translation t ON t.product_category_name = p.product_category_name
    WHERE o.order_status = 'delivered' GROUP BY 1
)
SELECT category, revenue, revenue / SUM(revenue) OVER () AS share,
       SUM(revenue) OVER (ORDER BY revenue DESC) / SUM(revenue) OVER () AS cumulative_share
FROM category_revenue ORDER BY revenue DESC;

-- 27. Product and category diversity by customer.
SELECT c.customer_unique_id, COUNT(DISTINCT oi.product_id) AS products,
       COUNT(DISTINCT COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown')) AS categories
FROM customers c JOIN orders o ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products p ON p.product_id = oi.product_id
LEFT JOIN product_category_translation t ON t.product_category_name = p.product_category_name
WHERE o.order_status = 'delivered' GROUP BY c.customer_unique_id;

-- 28. Rank categories within each year by revenue.
WITH category_year AS (
    SELECT EXTRACT(YEAR FROM o.order_purchase_timestamp) AS year,
           COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category,
           SUM(oi.price) AS revenue
    FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
    JOIN products p ON p.product_id = oi.product_id
    LEFT JOIN product_category_translation t ON t.product_category_name = p.product_category_name
    WHERE o.order_status = 'delivered' GROUP BY 1, 2
)
SELECT year, category, revenue, DENSE_RANK() OVER (PARTITION BY year ORDER BY revenue DESC) AS revenue_rank
FROM category_year ORDER BY year, revenue_rank;

-- 29. Customer purchase-frequency distribution.
WITH frequency AS (
    SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS orders
    FROM customers c JOIN orders o ON o.customer_id = c.customer_id
    GROUP BY c.customer_unique_id
)
SELECT orders, COUNT(*) AS customers FROM frequency GROUP BY orders ORDER BY orders;

-- 30. Acquisition cohort activity counts.
WITH customer_months AS (
    SELECT DISTINCT c.customer_unique_id,
           DATE_TRUNC('month', o.order_purchase_timestamp) AS order_month
    FROM customers c JOIN orders o ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
), cohorts AS (
    SELECT customer_unique_id, MIN(order_month) AS cohort_month FROM customer_months GROUP BY 1
)
SELECT co.cohort_month, cm.order_month,
       (EXTRACT(YEAR FROM cm.order_month) - EXTRACT(YEAR FROM co.cohort_month)) * 12
       + EXTRACT(MONTH FROM cm.order_month) - EXTRACT(MONTH FROM co.cohort_month) AS cohort_index,
       COUNT(DISTINCT cm.customer_unique_id) AS active_customers
FROM customer_months cm JOIN cohorts co USING (customer_unique_id)
GROUP BY 1, 2, 3 ORDER BY 1, 2;
