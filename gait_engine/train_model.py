import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

from features import (
    FEATURE_COLUMNS, extract_feature_matrix, fit_scaler, save_scaler,
)

#defines mathematical thresholds for bad behavior
TAG_RULES = {
    "HIGH_CLIPBOARD_USAGE": lambda row: row["clipboard_paste_count"] >= 3,
    "APP_SWITCH_SPIKE": lambda row: row["app_switch_count"] >= 4,
    "ROBOTIC_TIMING": lambda row: row["keystroke_interval_std_ms"] < 5,
    "INSTANT_CONFIRM": lambda row: row["session_dwell_time_sec"] < 5,
    "COGNITIVE_STRAIN_DETECTED": lambda row: (
        row["session_dwell_time_sec"] > 100 and row["app_switch_count"] >= 3
    ),
}

def generate_tags(row: pd.Series) -> list[str]:
    tags = [tag for tag, rule in TAG_RULES.items() if rule(row)]
    if row.get("flight_time_mean_ms", 100) < 10.0:
        tags.append("NON_HUMAN_FLIGHT_TIME")
    if row.get("mouse_curve_index", 1.0) < 0.1:
        tags.append("ROBOTIC_MOUSE_TRAJECTORY")
    if row.get("time_of_day_risk", 0.0) > 0.8:
        tags.append("HIGH_RISK_HOURS")
    return tags

def calculate_real_contamination(df: pd.DataFrame) -> float:
    """Dynamically calculates the actual proportion of illicit accounts."""
    if 'is_illicit' in df.columns:
        fraud_ratio = df['is_illicit'].mean()
        # Add a tiny buffer to account for undetected zero-day fraud
        return max(0.01, min(fraud_ratio + 0.01, 0.5))
    return 0.08

#unsuprvised model- isolation forest to detect anomalous sessions
def train_isolation_forest(
    X_scaled: np.ndarray, contamination: float = 0.08, seed: int = 42
) -> IsolationForest:
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(X_scaled) #matrix to build the detection trees
    return model

def score_to_gait_score(raw_scores: np.ndarray) -> np.ndarray: #-ve numbers to 0-1 range
    inverted = -raw_scores
    min_v, max_v = inverted.min(), inverted.max()
    if max_v - min_v < 1e-9:
        return np.zeros_like(inverted)
    return (inverted - min_v) / (max_v - min_v)

#loads telemetry file, scales it, pushes through isolation forest
def run_training_pipeline(
    telemetry_csv: str = "gait_telemetry_synthetic.csv",
    model_out: str = "gait_isolation_forest.joblib",
    scaler_out: str = "gait_scaler.joblib",
    scored_out: str = "gait_scored_accounts.csv",
) -> pd.DataFrame:
    df = pd.read_csv(telemetry_csv)

    X = extract_feature_matrix(df)
    scaler = fit_scaler(X)
    X_scaled = scaler.transform(X)
    dynamic_contamination = calculate_real_contamination(df)
    print(f"Auto-tuning model contamination to: {dynamic_contamination:.4f}")
    
    model = train_isolation_forest(X_scaled, contamination=dynamic_contamination)
    raw_scores = model.decision_function(X_scaled)
    df["Gait_Score"] = score_to_gait_score(raw_scores)
    df["is_anomaly_prediction"] = model.predict(X_scaled) == -1  # -1 = anomaly
    df["tags"] = df.apply(generate_tags, axis=1)

    joblib.dump(model, model_out)
    save_scaler(scaler, scaler_out)
    df.to_csv(scored_out, index=False)

    return df


def evaluate_against_ground_truth(df: pd.DataFrame) -> None:
    summary = df.groupby("label")["Gait_Score"].agg(["mean", "median", "count"])
    print("\nGait_Score by true label (sanity check on synthetic data):")
    print(summary)

if __name__ == "__main__":
    scored_df = run_training_pipeline()
    evaluate_against_ground_truth(scored_df)
    print("\nSample high-risk sessions:")
    print(
        scored_df.sort_values("Gait_Score", ascending=False)
        [["account_id", "label", "Gait_Score", "tags"]]
        .head(10)
        .to_string(index=False)
    )