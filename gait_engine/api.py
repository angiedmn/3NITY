from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import numpy as np

from features import FEATURE_COLUMNS, load_scaler, vectorize_single_session
from train_model import generate_tags
import joblib
import pandas as pd

import vector_store

class GaitTelemetryPayload(BaseModel):
    account_id: str
    clipboard_paste_count: float = Field(default=0.0, ge=0)
    app_switch_count: float = Field(default=0.0, ge=0)
    keystroke_interval_mean_ms: float = Field(default=150.0, ge=0) # Safe human baseline
    keystroke_interval_std_ms: float = Field(default=40.0, ge=0)
    session_dwell_time_sec: float = Field(default=60.0, ge=0)
    touch_pressure_var: float = Field(default=0.03, ge=0)
    gyro_tilt_var: float = Field(default=0.03, ge=0)
    flight_time_mean_ms: float = Field(default=80.0, ge=0)
    mouse_curve_index: float = Field(default=1.5, ge=0) # Safe mobile fallback
    time_of_day_risk: float = Field(default=0.2, ge=0)

class GaitScoreResponse(BaseModel):
    account_id: str
    Gait_Score: float
    tags: list[str]
    nearest_prior_session_account_id: Optional[str] = None
    nearest_prior_session_similarity: Optional[float] = None

_model = None
_scaler = None
_bounds= None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model, _scaler, _bounds
    _model = joblib.load("gait_isolation_forest.joblib")
    _scaler = load_scaler("gait_scaler.joblib")
    _bounds = joblib.load("gait_bounds.joblib")
    vector_store.init_db()
    yield


app = FastAPI(title="Gait Engine - Telemetry Ingestion", lifespan=lifespan)


def _score_to_gait_score(raw_score: float, ref_min: float, ref_max: float) -> float:
    """Same min-max normalization used at training time, applied to one point."""
    if ref_max - ref_min < 1e-9:
        return 0.0
    inverted = -raw_score
    return float(np.clip((inverted - ref_min) / (ref_max - ref_min), 0.0, 1.0))


@app.post("/api/v1/telemetry/gait", response_model=GaitScoreResponse)
async def ingest_gait_telemetry(payload: GaitTelemetryPayload):
    if _model is None or _scaler is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    row_dict = payload.model_dump(exclude={"account_id"})
    X_scaled = vectorize_single_session(row_dict, _scaler)

    raw_score = _model.decision_function(X_scaled)[0]
    # NOTE: ref_min/ref_max here should come from the training set's
    # score distribution (persist these alongside the model in
    # production instead of hardcoding placeholders).
    ref_min, ref_max = -0.15, 0.15
    gait_score = _score_to_gait_score(raw_score, ref_min, ref_max)

    tags = generate_tags(pd.Series(row_dict))

    # Store the vector for future cosine-similarity lookups
    vector_store.upsert_session_vector(
        account_id=payload.account_id,
        vector=X_scaled[0],
        gait_score=gait_score,
    )
    nearest = vector_store.find_nearest_session(
        vector=X_scaled[0], exclude_account_id=payload.account_id
    )

    return GaitScoreResponse(
        account_id=payload.account_id,
        Gait_Score=gait_score,
        tags=tags,
        nearest_prior_session_account_id=nearest["account_id"] if nearest else None,
        nearest_prior_session_similarity=nearest["similarity"] if nearest else None,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": _model is not None}