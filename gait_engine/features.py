import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import joblib

FEATURE_COLUMNS = [
    "clipboard_paste_count", "app_switch_count",
    "keystroke_interval_mean_ms", "keystroke_interval_std_ms",
    "session_dwell_time_sec", "touch_pressure_var",
    "gyro_tilt_var", "flight_time_mean_ms",
    "mouse_curve_index", "time_of_day_risk",
]

SAFE_BASELINES = {
    "clipboard_paste_count": 0.0,
    "app_switch_count": 0.0,
    "keystroke_interval_mean_ms": 150.0, # Normal human speed
    "keystroke_interval_std_ms": 40.0,
    "session_dwell_time_sec": 60.0,
    "touch_pressure_var": 0.03,
    "gyro_tilt_var": 0.03,
    "flight_time_mean_ms": 80.0,
    "mouse_curve_index": 1.5, # Safe human curve, won't trigger the bot tag
    "time_of_day_risk": 0.2
}

#pull numeric feature columns
def extract_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected feature columns: {missing}")
    return df[FEATURE_COLUMNS].to_numpy(dtype=float)

#mathematically squash all the data down to a proportional scale
def fit_scaler(X: np.ndarray) -> StandardScaler:
    scaler = StandardScaler()
    scaler.fit(X)
    return scaler

#save exact mathematical scaling formula to your hard drive (gait_scaler.joblib)
def save_scaler(scaler: StandardScaler, path: str = "gait_scaler.joblib") -> None:
    joblib.dump(scaler, path)
def load_scaler(path: str = "gait_scaler.joblib") -> StandardScaler:
    return joblib.load(path)

#to scale a single session's features
def vectorize_single_session(payload: dict, scaler: StandardScaler) -> np.ndarray:
    row = np.array([[payload.get(col, SAFE_BASELINES[col]) for col in FEATURE_COLUMNS]], dtype=float)
    return scaler.transform(row)