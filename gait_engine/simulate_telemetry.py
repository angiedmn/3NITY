import numpy as np
import pandas as pd

def build_gait_dataset(account_ids: pd.Series, bot_ratio: float = 0.06, mule_ratio: float = 0.04) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    
    n_total = len(account_ids)
    n_bots = int(n_total * bot_ratio)
    n_mules = int(n_total * mule_ratio)
    
    # Create a shuffled list of labels
    labels = ["bot"] * n_bots + ["coerced_mule"] * n_mules + ["human"] * (n_total - n_bots - n_mules)
    rng.shuffle(labels)

    for account_id, label in zip(account_ids, labels):
        if label == "human":
            row = {
                "account_id": account_id,
                "label": "human",
                "clipboard_paste_count": max(0, int(rng.normal(0.5, 0.5))),
                "app_switch_count": max(0, int(rng.normal(1, 1))),
                "keystroke_interval_mean_ms": rng.normal(150, 30),
                "keystroke_interval_std_ms": max(10, rng.normal(40, 15)),
                "session_dwell_time_sec": max(10, rng.normal(45, 15)),
                "touch_pressure_var": max(0.01, rng.normal(0.2, 0.05)),
                "gyro_tilt_var": max(0.01, rng.normal(0.3, 0.1)),
                "flight_time_mean_ms": max(20, rng.normal(120, 20)),
                "mouse_curve_index": max(0.5, rng.normal(1.5, 0.2)),
                "time_of_day_risk": rng.uniform(0.0, 0.3),
            }
            
        elif label == "bot":
            row = {
                "account_id": account_id,
                "label": "bot",
                "clipboard_paste_count": rng.choice([1, 2]),
                "app_switch_count": 0,
                "keystroke_interval_mean_ms": max(10, rng.normal(40, 2)),
                "keystroke_interval_std_ms": max(0, rng.normal(1, 0.5)),
                "session_dwell_time_sec": max(0.5, rng.normal(2.0, 0.5)),
                "touch_pressure_var": max(0, rng.normal(0.01, 0.005)),
                "gyro_tilt_var": max(0, rng.normal(0.05, 0.01)),
                "flight_time_mean_ms": max(1.0, rng.normal(5.0, 1.0)),
                "mouse_curve_index": 0.0,
                "time_of_day_risk": rng.uniform(0.8, 1.0),
            }
            
        else: # coerced_mule
            row = {
                "account_id": account_id,
                "label": "coerced_mule",
                "clipboard_paste_count": max(2, int(rng.normal(4, 1))),
                "app_switch_count": max(3, int(rng.normal(6, 2))),
                "keystroke_interval_mean_ms": rng.normal(350, 80),
                "keystroke_interval_std_ms": max(50, rng.normal(150, 40)),
                "session_dwell_time_sec": max(120, rng.normal(300, 100)),
                "touch_pressure_var": max(0.1, rng.normal(0.6, 0.15)),
                "gyro_tilt_var": max(0.1, rng.normal(0.8, 0.2)),
                "flight_time_mean_ms": max(100, rng.normal(300, 50)),
                "mouse_curve_index": max(1.0, rng.normal(2.5, 0.5)),
                "time_of_day_risk": rng.uniform(0.2, 0.8),
            }
            
        rows.append(row)

    return pd.DataFrame(rows)