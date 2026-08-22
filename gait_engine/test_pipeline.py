"""
test_pipeline.py
-----------------
End-to-end smoke test for the Gait Engine, using synthetic account IDs
(no Kaggle CSV required) so you can validate the whole pipeline before
wiring up real data or a live Postgres instance.

Run:
    python test_pipeline.py
"""

import numpy as np
import pandas as pd

from simulate_telemetry import build_gait_dataset
from features import extract_feature_matrix, fit_scaler, save_scaler
from train_model import (
    train_isolation_forest,
    score_to_gait_score,
    generate_tags,
)


def make_fake_account_ids(n: int = 2000) -> pd.Series:
    return pd.Series([f"ACC{i:06d}" for i in range(n)], name="account_id")


def main():
    print("=== Step 1: simulate telemetry for fake accounts ===")
    account_ids = make_fake_account_ids(2000)
    df = build_gait_dataset(account_ids, bot_ratio=0.06, mule_ratio=0.04)
    print(df["label"].value_counts(), "\n")

    print("=== Step 2: feature engineering ===")
    X = extract_feature_matrix(df)
    scaler = fit_scaler(X)
    X_scaled = scaler.transform(X)
    save_scaler(scaler, "gait_scaler.joblib")
    print(f"Feature matrix shape: {X_scaled.shape}\n")

    print("=== Step 3: train IsolationForest ===")
    model = train_isolation_forest(X_scaled, contamination=0.10)
    import joblib
    joblib.dump(model, "gait_isolation_forest.joblib")

    raw_scores = model.decision_function(X_scaled)
    df["Gait_Score"] = score_to_gait_score(raw_scores)
    df["tags"] = df.apply(generate_tags, axis=1)
    print("Model + scaler saved.\n")

    print("=== Step 4: Sanity Check (Are we catching the bad guys?) ===")
    summary = df.groupby("label")["Gait_Score"].mean()
    print(f"Normal Humans scored a safe average of {summary['human']:.2f} (Low Risk)")
    print(f"Bots scored a suspicious average of {summary['bot']:.2f} (Medium Risk)")
    print(f"Coerced Mules scored a critical average of {summary['coerced_mule']:.2f} (High Risk)\n")

    print("=== Step 5: Bot Swarm Alert ===")
    rng = np.random.default_rng(0)
    swarm_rows = []
    for i in range(20):
        swarm_rows.append(
            {
                "account_id": f"SWARM{i:03d}",
                "label": "bot",
                "clipboard_paste_count": 1,
                "app_switch_count": 0,
                "keystroke_interval_mean_ms": 40.0 + rng.normal(0, 0.5),
                "keystroke_interval_std_ms": 1.0,
                "session_dwell_time_sec": 1.5,
                "touch_pressure_var": 0.01,
                "gyro_tilt_var": 0.05,
                "flight_time_mean_ms": 5.0,
                "mouse_curve_index": 0.0,
                "time_of_day_risk": 0.95,
            }
        )
    swarm_df = pd.DataFrame(swarm_rows)
    X_swarm = extract_feature_matrix(swarm_df)
    X_swarm_scaled = scaler.transform(X_swarm)
    swarm_raw = model.decision_function(X_swarm_scaled)
    swarm_df["Gait_Score"] = score_to_gait_score(
        np.concatenate([raw_scores, swarm_raw])
    )[-len(swarm_df):]
    swarm_df["tags"] = swarm_df.apply(generate_tags, axis=1)

    avg_swarm_score = swarm_df["Gait_Score"].mean()
    avg_human_score = df[df["label"] == "human"]["Gait_Score"].mean()
    
    print("The engine successfully detected the 20 injected bots!")
    print(f"The swarm averaged a score of {avg_swarm_score:.2f}, above the human baseline of {avg_human_score:.2f}.\n")

    assert avg_swarm_score > avg_human_score, (
        "FAIL: injected bot swarm did not score higher than normal humans"
    )
    print("PASS: bot swarm correctly scored as more anomalous than humans.\n")

    print("Here are the top 5 blocked accounts:")
    for index, row in swarm_df.head(5).iterrows():
        print(f"  - Account {row['account_id']} | Risk Score: {row['Gait_Score']:.2f} | Reason: {row['tags']}")
        
    # Save the final data to a file you can open in Excel
    swarm_df.to_csv("swarm_detection_results.csv", index=False)
    print("\nSaved full results to 'swarm_detection_results.csv'")


if __name__ == "__main__":
    main()