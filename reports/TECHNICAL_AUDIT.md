# CommerceIQ Analytics — Final Technical Audit

Audit date: 2026-08-17

## Data

- All nine supplied files detected; every row count matches the reference bundle.
- Required schemas and verified keys pass.
- Order-level output: 99,441 unique orders.
- Customer-level output: 96,096 unique `customer_unique_id` rows.
- ZIP summary: 19,015 unique prefixes.
- Item-price and payment totals reconcile before/after aggregation.
- Review and geolocation non-uniqueness are handled explicitly.
- Product category translation uses English, Portuguese fallback, then `Unknown`.
- Purchase dates parse from 2016-09-04 through 2018-10-17.
- September (16 all-status orders) and October 2018 (4) are marked partial for forecasting.

## Analytics

- Delivered merchandise revenue excludes freight and amount paid.
- AOV uses delivered merchandise revenue / distinct delivered orders.
- Repeat rate uses `customer_unique_id`.
- Freight, delivery, review, cancellation, and late-rate definitions match Python, SQL, dashboard, and documentation.

## Database

- PostgreSQL schema defines verified natural/composite keys, review/geolocation surrogate keys, foreign keys, and focused indexes.
- Thirty business queries are present.
- PostgreSQL was not installed/configured in the audit environment, so the optional live database load was not executed. Local Parquet operation is complete and unaffected.

## Machine Learning

- Delivery target and prediction-time feature list pass leakage assertions.
- Preprocessing is fitted inside Scikit-learn pipelines.
- Delivery evaluation uses a chronological holdout and a dummy baseline.
- Retention uses explicit observation/prediction windows and reports sparse-class limitations.
- Forecasting uses chronological validation and excludes the incomplete tail.
- Persisted delivery, segmentation, retention, and forecast artifacts reload successfully.

## Dashboard

- Streamlit starts successfully on `app/app.py`.
- All ten pages were navigated in a live browser session with no tracebacks.
- KPI cards, predictive pages, navigation, filters, charts, model loading, empty states, and downloads were reviewed.
- A visual pass corrected package shadowing, duplicate callable route names, clipped KPI cards, and raw feature labels.

## Code and Tests

- No hard-coded local absolute paths, secrets, TODOs, or incorrect source-currency symbols found.
- Four notebook files are valid JSON; every code cell compiles and has no stored output.
- Final Pytest result: **40 passed, 0 failed**.
- Remaining warnings are third-party Joblib/NumPy deprecation warnings during model reload tests.
