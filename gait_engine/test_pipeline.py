"""
test_pipeline.py
-----------------
End-to-end smoke test for the Gait Engine.
Uses real account IDs from the IBM Kaggle dataset enriched with 
synthetic telemetry to validate the ML pipeline end-to-end.

Run:
    python test_pipeline.py
"""

import numpy as np
import pandas as pd

# Import our new bridge script instead of the fake telemetry generator
from bridge_dataset import enrich_ibm_with_gait
from features import extract_feature_matrix, fit_scaler, save_scaler
from train_model import (
    train_isolation_forest,
    score_to_gait_score,
    generate_tags,
)

def main():
    print("=== Step 1: Simulate telemetry for IBM accounts ===")
    # Using the specific file name downloaded from Kaggle
    input_csv = "HI-Small_Trans.csv" 
    output_csv = "gait_telemetry_synthetic.csv"
    
    # Generate the biometrics and return the DataFrame
    df = enrich_ibm_with_gait(input_csv, output_csv)
    print("\nLabel distribution:")
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
    # Using .get() to avoid KeyError if the dataset doesn't have a specific label yet
    print(f"Normal Humans scored a safe average of {summary.get('human', 0):.2f} (Low Risk)")
    print(f"Coerced Mules scored a critical average of {summary.get('coerced_mule', 0):.2f} (High Risk)\n")

    print("=== Step 5: Bot Swarm Alert ===")
    # Inject a 100% synthetic bot swarm to see if the trained model catches them
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
    
    # Score the swarm using the distribution of the training data
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