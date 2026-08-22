"""
features.py
------------
Turns raw telemetry rows into the numeric feature matrix IsolationForest
expects, and handles scaling so no single feature (e.g. dwell_time_sec
in seconds vs keystroke_interval in ms) dominates distance calculations.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import joblib

FEATURE_COLUMNS = [
    "clipboard_paste_count",
    "app_switch_count",
    "keystroke_interval_mean_ms",
    "keystroke_interval_std_ms",
    "session_dwell_time_sec",
    "touch_pressure_var",
    "gyro_tilt_var",
    "flight_time_mean_ms",
    "mouse_curve_index",
    "time_of_day_risk",
]


def extract_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """Pull just the numeric feature columns, in a fixed order."""
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected feature columns: {missing}")
    return df[FEATURE_COLUMNS].to_numpy(dtype=float)


def fit_scaler(X: np.ndarray) -> StandardScaler:
    scaler = StandardScaler()
    scaler.fit(X)
    return scaler


def save_scaler(scaler: StandardScaler, path: str = "gait_scaler.joblib") -> None:
    joblib.dump(scaler, path)


def load_scaler(path: str = "gait_scaler.joblib") -> StandardScaler:
    return joblib.load(path)


def vectorize_single_session(payload: dict, scaler: StandardScaler) -> np.ndarray:
    """
    Turn a single incoming telemetry payload (e.g. from the FastAPI
    ingestion endpoint) into a scaled feature vector ready for
    model.decision_function() / model.predict().
    """
    row = np.array([[payload.get(col, 0.0) for col in FEATURE_COLUMNS]], dtype=float)
    return scaler.transform(row)