# CommerceIQ Development Notes

- Keep the order, customer, item, payment, review, and seller-order grains explicit.
- Never join raw order items, payments, and reviews before aggregating each to order level.
- Use `customer_unique_id` for repeat purchasing, RFM, customer value, and retention analysis.
- Delivered merchandise revenue is `SUM(order_items.price)`; freight and payments are separate measures.
- Delivery-risk features must be available at purchase or approval time. Do not add delivery outcome or review columns.
- Fit preprocessing only on training data, and keep time-series validation chronological.
- The Streamlit application reads compact files from `data/processed/dashboard/` and must not trigger ETL or model training.
- Run `python run_pipeline.py`, `pytest`, and a Streamlit startup check after material pipeline changes.
