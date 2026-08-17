# Development Guide

This project follows a few data-design and validation rules to keep its results reproducible and its business metrics consistent.

## Data modelling standards

- Keep the order, customer, item, payment, review, and seller-order grains explicit.
- Aggregate order items, payments, and reviews to order level before joining them.
- Use `customer_unique_id` for repeat-purchase, RFM, customer-value, and retention analysis.
- Define delivered merchandise revenue as `SUM(order_items.price)`. Treat freight and payments as separate measures.

## Machine-learning standards

- Use only information available at purchase or approval time for delivery-risk features.
- Do not use delivery outcomes or review fields as predictors of delivery risk.
- Fit preprocessing steps on training data only.
- Preserve chronological order for time-series validation.

## Application boundary

The Streamlit application reads compact artifacts from `data/processed/dashboard/`. It does not run the ETL pipeline or train models during application startup.

## Verification

After a material pipeline change, run:

```bash
python run_pipeline.py
python -m pytest -q
streamlit run app/app.py --server.headless true
```

Before committing, confirm that raw source CSV files, local environment files, and Streamlit secrets remain untracked.
