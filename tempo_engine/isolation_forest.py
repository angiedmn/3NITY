import pandas as pd
from sklearn.ensemble import IsolationForest
from dtw_features import FEATURE_GROUP_A, FEATURE_GROUP_B

def run_isolation_forest(final_features, contamination=0.02, random_state=42):
    feature_cols = FEATURE_GROUP_A + FEATURE_GROUP_B


    X = final_features[feature_cols].values

    model = IsolationForest(contamination=contamination, random_state=random_state, n_estimators=200)
    model.fit(X)

    # decision_function: higher = more normal, lower/negative = more anomalous
    # we flip sign so higher = more anomalous, matching "Tempo anomaly score" framing
    raw_scores = model.decision_function(X)
    scored = final_features.copy()
    scored["tempo_anomaly_score"] = -raw_scores
    scored["tempo_is_anomaly"] = model.predict(X) == -1  # sklearn: -1 = anomaly, 1 = normal

    return scored

def evaluate_against_known_labels(scored_features, laundering_account_ids):
    scored_features = scored_features.copy()
    scored_features["is_known_laundering"] = scored_features.apply(
        lambda r: (r["account"], r["bank"]) in laundering_account_ids, axis=1
    )
    return scored_features

