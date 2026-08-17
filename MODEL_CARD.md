# CommerceIQ Analytics — Model Card

## Delivery Risk Model

### Objective

Estimate the probability that a delivered-order-like case will arrive after the promised date. Output is **Estimated Late Delivery Risk**, never a deterministic delivery claim.

### Target

`late_delivery = 1` when actual customer delivery is later than estimated delivery, otherwise 0. Only delivered orders with valid actual and estimated dates are used.

### Features

Purchase month, weekday and hour; customer and primary seller state; primary category; item/product/seller counts; merchandise, freight, gross and payment values; installments and dominant payment type; estimated delivery window; approximate distance; average product weight.

Forbidden outcome information includes actual delivery timestamps, delivery duration/delay, target value, and reviews. Preprocessing is fitted inside each Scikit-learn Pipeline on training data only.

### Split

Chronological 80/20 split: 77,176 training orders and 19,294 test orders. Test begins 2018-05-26. Late-delivery prevalence is 8.82% in training and 5.29% in test.

### Algorithms

Dummy prior baseline, class-weighted Logistic Regression, class-weighted Decision Tree, and class-weighted Random Forest.

### Selected Model and Metrics

Decision Tree, selected by F1 with PR-AUC tie-breaking.

| Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---:|---:|---:|---:|---:|---:|
| 0.767 | 0.104 | 0.448 | 0.169 | 0.688 | 0.121 |

Confusion matrix: TN 14,347; FP 3,926; FN 564; TP 457.

### Limitations

Precision is modest because late deliveries are rare and operational variables are missing. Probability calibration was not independently validated. Primary seller/category simplify multi-seller/category orders. Distance uses representative ZIP coordinates. The model supports ranking and education, not automated customer promises.

## Retention / Future-Purchase Model

### Objective and Target

Assess whether a temporal repeat-purchase model is statistically useful. Olist has no native churn label. Customers observed through 2018-02-28 are positive only when they purchase during 2018-03-01 to 2018-08-31.

### Data and Class Balance

55,525 observation customers: 654 positive (1.18%) and 54,871 negative. Features contain only pre-cutoff orders, spend, items, AOV, recency, tenure, freight, reviews, and late rate.

### Metrics

Logistic Regression with stratified customer holdout: precision 0.017, recall 0.561, F1 0.032, ROC-AUC 0.614, PR-AUC 0.032.

### Limitations

The target is sparse, precision is low, and a single cutoff cannot demonstrate stability. Scores are exploratory ranking signals. The dashboard does not call customers churned and does not present this as a production retention system.

## Customer Segmentation

RFM values are log-transformed and standardized. K-Means candidates K=2 through K=6 are compared. K=2 achieved the highest Silhouette Score (0.706) and was selected. The two profiles are labelled High Value and Low Engagement from their observed RFM characteristics; names are interpretations, not ground truth.

## Sales Forecast

### Frequency and Completeness

Monthly delivered merchandise revenue. The raw purchase tail contains 16 orders in September 2018 and 4 in October 2018; both months are excluded as partial. The complete cutoff is August 2018.

### Split and Models

Training: September 2016 through April 2018. Validation: May through August 2018. Compared models: last-value naive, three-month moving average, seasonal naive, and linear trend plus seasonality.

### Selected Model and Metrics

Last Value Naive achieved the lowest validation RMSE: MAE R$ 41,682.46, RMSE R$ 62,797.90, MAPE 4.87%. A six-month future scenario is generated.

### Limitations

The history is short, early months may reflect marketplace ramp-up, and no promotions, macroeconomics, inventory, or acquisition data are available. Forecasts are scenarios, not guarantees.
