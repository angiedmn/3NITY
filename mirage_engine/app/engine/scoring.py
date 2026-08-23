import logging
import numpy as np
from pathlib import Path
from xgboost import XGBClassifier
from app.schemas.company import CompanyPayload, MirageFeatures, RealityIndexResult

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "models" / "mirage_classifier.json"
try:
    # n_jobs=1: forces single-threaded prediction. XGBoost's compiled
    # predictor spawns OpenMP threads at predict time, and inside
    # resource-constrained Docker containers thread creation can fail in
    # a way that segfaults the worker process (signal 11) instead of
    # raising a catchable Python exception — this is a well-documented
    # class of issue (see dmlc/xgboost#10869 and similar). Forcing
    # single-threaded inference avoids that code path entirely; for a
    # single-row prediction like this one there's no meaningful
    # performance cost to losing parallelism.
    clf = XGBClassifier(n_jobs=1)
    clf.load_model(str(MODEL_PATH))
    MODEL_LOADED = True
    logger.info("ML Model loaded successfully.")
except Exception:
    logger.warning("ML Model not found or failed to load! Falling back to heuristics.")
    MODEL_LOADED = False

def calculate_heuristic_fallback(features: MirageFeatures) -> float:
    score = 100.0
    if features.co_location_density > 1000: score -= 40
    elif features.co_location_density > 100: score -= 20
    if features.fatf_risk_score > 7.0: score -= 25
    elif features.fatf_risk_score > 4.0: score -= 10
    if features.domain_age_days < 180: score -= 20
    if not features.has_commercial_ip: score -= 10
    
    # Flag highly irregular currency variance in EITHER direction: a loss
    # (under-payment) and a gain (over-payment / round-tripping) are both
    # classic trade-based money-laundering patterns. The old `> 0.10` check
    # only ever caught the loss direction.
    if abs(features.fx_variance_percentage) > 0.10: score -= 15
    return max(0.0, score)

def score_company_substance(payload: CompanyPayload, features: MirageFeatures) -> dict:
    logger.info(f"Scoring substance for {payload.company_name}...")

    flags = []
    if features.co_location_density > 1000: flags.append("Extremely High Address Co-Location Density")
    if features.fatf_risk_score > 7.0: flags.append("High-Risk Secrecy Jurisdiction")
    if features.domain_age_days < 180: flags.append("Domain Registration is less than 6 months old")
    if not features.has_commercial_ip: flags.append("No Enterprise/Commercial IP block detected")
    
    # --- Flag human-readable FX Variance (either direction) ---
    if abs(features.fx_variance_percentage) > 0.10:
        direction = "loss" if features.fx_variance_percentage > 0 else "gain"
        variance_str = f"{abs(features.fx_variance_percentage) * 100:.1f}%"
        flags.append(f"Irregular FX Variance ({variance_str} value {direction}) - Potential Value Transfer or Hidden Fees")

    # --- Funds received with no corresponding recorded payment ---
    # worker.py's fx_variance calculation is guarded by `amount_paid_usd > 0`,
    # so a payload with amount_paid_usd == 0 but amount_received_usd > 0
    # (money appearing from nowhere) always computes fx_variance == 0.0 and
    # would otherwise pass through with no flag at all despite being a
    # meaningfully suspicious pattern.
    if payload.amount_paid_usd == 0 and payload.amount_received_usd > 0:
        flags.append("Received funds with no recorded corresponding payment")

    if MODEL_LOADED:
        feature_vector = np.array([[
            features.co_location_density,
            features.domain_age_days,
            int(features.has_commercial_ip),
            features.local_traffic_score,
            features.fatf_risk_score,
            features.fx_variance_percentage
        ]])
        
        prob = clf.predict_proba(feature_vector)[0]
        reality_index = float(prob[1] * 100)
    else:
        reality_index = calculate_heuristic_fallback(features)

    if reality_index < 40.0: risk_tier = "High"
    elif reality_index < 70.0: risk_tier = "Medium"
    else: risk_tier = "Low"

    result = RealityIndexResult(
        company_name=payload.company_name,
        reality_index=reality_index,
        risk_tier=risk_tier,
        is_shell_suspected=(reality_index < 40.0),
        flags=flags
    )
    
    return result.model_dump()