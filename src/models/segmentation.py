"""RFM customer segmentation with data-driven K selection."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from src.config import RANDOM_STATE


RFM_COLUMNS = ["recency", "frequency", "monetary"]


def create_rfm_features(customer_features: pd.DataFrame) -> pd.DataFrame:
    rfm = customer_features.loc[
        customer_features["delivered_orders"].gt(0),
        ["customer_unique_id", *RFM_COLUMNS],
    ].copy()
    rfm["recency"] = rfm["recency"].clip(lower=0)
    rfm[["frequency", "monetary"]] = rfm[["frequency", "monetary"]].clip(lower=0)
    return rfm


def _segment_names(cluster_count: int) -> list[str]:
    names = {
        2: ["Low Engagement", "High Value"],
        3: ["At Risk", "Regular", "Champions"],
        4: ["Low Engagement", "At Risk", "Loyal", "Champions"],
        5: ["Low Engagement", "At Risk", "Regular", "Loyal", "Champions"],
        6: ["Dormant", "Low Engagement", "At Risk", "Regular", "Loyal", "Champions"],
    }
    return names[cluster_count]


@threadpool_limits.wrap(limits=1)
def train_segmentation(
    customer_features: pd.DataFrame,
    model_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    rfm = create_rfm_features(customer_features)
    transformed = np.log1p(rfm[RFM_COLUMNS])
    scaler = StandardScaler()
    scaled = scaler.fit_transform(transformed)

    evaluations: list[dict[str, float | int | bool]] = []
    fitted: dict[int, KMeans] = {}
    for cluster_count in range(2, 7):
        model = KMeans(n_clusters=cluster_count, n_init=10, random_state=RANDOM_STATE)
        labels = model.fit_predict(scaled)
        silhouette = silhouette_score(
            scaled,
            labels,
            sample_size=min(12_000, len(rfm)),
            random_state=RANDOM_STATE,
        )
        evaluations.append(
            {
                "model": "KMeans",
                "clusters": cluster_count,
                "inertia": float(model.inertia_),
                "silhouette": float(silhouette),
            }
        )
        fitted[cluster_count] = model

    evaluation = pd.DataFrame(evaluations)
    selected_k = int(evaluation.sort_values(["silhouette", "clusters"], ascending=[False, True]).iloc[0]["clusters"])
    evaluation["selected"] = evaluation["clusters"].eq(selected_k)
    selected_model = fitted[selected_k]
    rfm["cluster"] = selected_model.labels_

    profiles = (
        rfm.groupby("cluster", as_index=False)
        .agg(
            customers=("customer_unique_id", "nunique"),
            recency=("recency", "mean"),
            frequency=("frequency", "mean"),
            monetary=("monetary", "mean"),
        )
    )
    profile_scaled = StandardScaler().fit_transform(
        profiles[["recency", "frequency", "monetary"]]
    )
    profiles["value_score"] = -profile_scaled[:, 0] + profile_scaled[:, 1] + profile_scaled[:, 2]
    ordered_clusters = profiles.sort_values("value_score")["cluster"].tolist()
    label_map = dict(zip(ordered_clusters, _segment_names(selected_k)))
    rfm["segment"] = rfm["cluster"].map(label_map)
    profiles["segment"] = profiles["cluster"].map(label_map)
    profiles = profiles.sort_values("value_score", ascending=False)

    segments = customer_features.merge(
        rfm[["customer_unique_id", "cluster", "segment"]],
        on="customer_unique_id", how="left", validate="1:1",
    )
    segments["segment"] = segments["segment"].fillna("No Delivered Purchase")
    bundle = {
        "scaler": scaler,
        "model": selected_model,
        "features": RFM_COLUMNS,
        "label_map": label_map,
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path)
    metadata = {
        "selected_k": selected_k,
        "silhouette": float(evaluation.loc[evaluation["selected"], "silhouette"].iloc[0]),
        "customers_segmented": int(len(rfm)),
    }
    return segments, profiles, evaluation, metadata
