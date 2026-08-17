# CommerceIQ Analytics — Data Dictionary

## Identity and Grain Rules

| Concept | Definition |
|---|---|
| `customer_id` | Order-level customer record used to join `customers` to `orders`; not a durable person identifier. |
| `customer_unique_id` | Durable customer identifier used for unique customers, repeat behavior, RFM, historical value, segmentation, and retention. |
| Order-level grain | Exactly one row per `order_id`. |
| Customer-level grain | Exactly one row per `customer_unique_id`. |
| Order-item grain | One row per `order_id + order_item_id`. |
| Payment grain | One row per `order_id + payment_sequential`. |
| Seller-order grain | One row per `seller_id + order_id` before seller KPIs. |
| Monthly-sales grain | One row per calendar purchase month. |

## Raw Source Tables

### Customers

Key: `customer_id`. Important columns: `customer_unique_id`, ZIP prefix, city, state. No missing cells in the supplied 99,441 rows.

### Orders

Key: `order_id`. `customer_id` is a foreign key to customers. Timestamp columns describe purchase, approval, carrier handoff, actual delivery, and estimated delivery. Missing delivery timestamps are legitimate for canceled, unavailable, or incomplete orders.

### Order Items

Composite key: `order_id + order_item_id`. `price` is merchandise value; `freight_value` is freight. `shipping_limit_date` is preserved as a source field, including the observed 2020 outlier.

### Order Payments

Composite key: `order_id + payment_sequential`. Multiple rows may fund one order. `payment_value` is amount paid and must not be used as merchandise revenue. Two zero-installment and nine zero-value source rows are retained and documented rather than silently deleted.

### Order Reviews

`review_id` is not unique and `order_id` is not unique. The supplied data has 1,603 rows participating in repeated `review_id` values and 1,098 rows participating in repeated order-review relationships. The raw SQL table uses a surrogate row key and a verified unique relationship constraint. Order analytics use the most recent review by answer timestamp plus an average score and review count.

### Products

Key: `product_id`. Source spellings such as `product_name_lenght` and `product_description_lenght` remain unchanged for lineage. `product_category` is an engineered readable field. Nonpositive product dimensions/weight are treated as missing in the cleaned analytical layer.

### Sellers

Key: `seller_id`. Contains seller ZIP prefix, city, and state.

### Geolocation

Raw grain: repeated coordinate observation, not ZIP. There are 1,000,163 rows and 19,015 ZIP prefixes. The analytical ZIP summary uses median coordinates after excluding 31 observations outside a broad Brazil bounding box; city and state are selected by most common occurrence.

### Product Category Translation

Key: `product_category_name`. Translation logic uses English when present, Portuguese as fallback, and `Unknown` only when the original category is missing.

## Analytical Tables

### `order_items_order_level`

One row per order with `item_count`, `unique_product_count`, `unique_seller_count`, `merchandise_revenue`, and `total_freight_value`.

### `payments_order_level`

One row per order with total payment value, record count, payment-type count, maximum installments, and dominant payment type (largest payment value).

### `reviews_order_level`

One row per order with average review score, review count, and most recent valid review fields.

### `order_level`

One row per order. Combines safe aggregates with customer, primary category/seller context, representative coordinates, date features, delivery features, and separated value measures.

### `customer_level` / `customer_features`

One row per `customer_unique_id`, including total and delivered orders, delivered merchandise spend, items, AOV, first/last purchase, recency, tenure, reviews, delivery performance, product/category diversity, repeat indicator, and state/city.

### Category and seller summaries

Category metrics use delivered item rows and category-order review aggregation. Seller metrics are first aggregated to `seller_id + order_id` so multi-item seller orders are not overweighted.

## Engineered Features

### Order features

- `merchandise_revenue`: sum of item price.
- `total_freight_value`: sum of item freight.
- `gross_order_value`: merchandise plus freight.
- `total_payment_value`: sum of payment values after order aggregation.
- Counts for items, products, sellers, payment records, and review records.
- Purchase year, month, weekday, hour, and month period.
- `delivery_days`: actual customer delivery minus purchase timestamp.
- `delivery_delay_days`: actual delivery minus estimated delivery.
- `late_delivery`: 1 only when a delivered order arrived after its estimate.
- `distance_km`: Haversine distance between representative customer and primary seller ZIP coordinates.
- `estimated_delivery_days`: estimated date minus purchase time; available before outcome.

### Customer features

`total_orders`, `delivered_orders`, `total_spend`, `total_items`, `average_order_value`, `recency`, `frequency`, `monetary`, purchase dates, tenure, review/delivery averages, late rate, diversity, repeat indicator, and average freight.

## KPI Definitions

| KPI | Canonical definition |
|---|---|
| Total Merchandise Revenue | Sum of order-item price for delivered orders. |
| Total Delivered Orders | Distinct delivered `order_id`. |
| Unique Customers | Distinct delivered `customer_unique_id`. |
| Average Order Value | Delivered merchandise revenue / delivered orders. |
| Items Sold | Delivered order item count. |
| Average Review Score | Mean order-level average review score for delivered orders. |
| Average Delivery Days | Mean purchase-to-customer-delivery days for delivered orders. |
| Late Delivery Rate | Mean `late_delivery` for delivered orders with valid dates. |
| Repeat Customer Rate | Share of all `customer_unique_id` values with more than one order identity. |
| Cancellation Rate | Share of all orders with status canceled or unavailable. |
| Freight Value | Sum of item freight; never included silently in merchandise revenue. |
| Gross Order Value | Merchandise revenue plus freight. |
| Amount Paid | Sum of payment value after payment records are aggregated to order. |

## Model Targets

### Late delivery

For delivered orders with valid dates: 1 when `order_delivered_customer_date > order_estimated_delivery_date`, else 0. Delivery outcome, delivery duration, delay, and review fields are forbidden model inputs.

### Future purchase

Among customers observed through 2018-02-28: 1 when the same `customer_unique_id` purchases between 2018-03-01 and 2018-08-31, otherwise 0. This is not a native churn label.

### Forecast target

Monthly delivered merchandise revenue through the last complete month, August 2018. September and October are marked partial using all-order counts and excluded from training/evaluation.
