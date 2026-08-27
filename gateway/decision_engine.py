"""
gateway/decision_engine.py
--------------------------
Mathematical convergence model using an amplification factor for the 
3NITY anti-financial crime orchestrator.
"""

from typing import Any, Dict
from pydantic import BaseModel, Field

class EngineScores(BaseModel):
    gait_score: float = Field(..., ge=0.0, le=1.0, description="Independent biometric anomaly score")
    tempo_score: float = Field(..., ge=0.0, le=1.0, description="Independent velocity/smurfing score")
    reality_index: float = Field(..., ge=0.0, le=100.0, description="Independent corporate substance score")

def evaluate_3nity_session(scores: EngineScores) -> Dict[str, Any]:
    """
    Computes the normalized ML risk score using reality risk and an amplified 
    tempo-gait interaction, then applies strict regulatory business rules.
    """
    # 1. Calculate reality risk from the Mirage reality index
    reality_risk = (100.0 - scores.reality_index) / 100.0
    
    # 2. Mathematical convergence model using an amplification factor
    # Amplifies tempo risk based on biometric (gait) anomalies, capped at 1.0
    amplified_behavioral_score = min(1.0, scores.tempo_score * (1.0 + scores.gait_score))
    
    # Final normalized ML risk score
    normalized_ml_score = round(max(reality_risk, amplified_behavioral_score), 3)
    
    # 3. Business Rules Evaluation
    
    # Hard Block (Money Laundering / Ghost Shell): Score > 0.85
    if normalized_ml_score > 0.85:
        return {
            "verdict": "BLOCK",
            "action": "INSTANT_TERMINATION",
            "normalized_ml_score": normalized_ml_score,
            "is_money_laundering": True,
            "reason": f"High composite risk score ({normalized_ml_score:.2f}). Exceeds AML laundering threshold (Ghost Shell or Smurfing Burst)."
        }
        
    # Step-Up (Account Takeover): Gait score > 0.70 regardless of overall score
    if scores.gait_score > 0.70:
        return {
            "verdict": "STEP_UP_2FA",
            "action": "BIOMETRIC_REAUTH",
            "normalized_ml_score": normalized_ml_score,
            "is_money_laundering": False,
            "reason": f"Account Takeover (ATO) risk detected: Independent gait anomaly score ({scores.gait_score:.2f}) exceeds re-auth threshold."
        }
        
    # Allow (Golden Path): Default safe state
    return {
        "verdict": "ALLOW",
        "action": "EXECUTE_PAYMENT",
        "normalized_ml_score": normalized_ml_score,
        "is_money_laundering": False,
        "reason": f"Normalized ML score ({normalized_ml_score:.2f}) and behavioral metrics fall within clean operational bounds."
    }

from datetime import datetime

def generate_topology_report(transaction_id: str, sender_id: str, receiver_id: str, amount: float, decision: dict, telemetry: dict) -> str:
    """
    Generates a formal AML Topology & Compliance Report for regulatory authorities.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    report = f"""
======================================================================
              3NITY ANTI-FINANCIAL CRIME ORCHESTRATOR
               TOPOLOGY & SUSPICIOUS ACTIVITY REPORT
======================================================================
REPORT GENERATED: {timestamp}
TRANSACTION ID:   {transaction_id}
----------------------------------------------------------------------
1. TRANSACTION METADATA
----------------------------------------------------------------------
Sender Account:      {sender_id}
Receiver Account:    {receiver_id}
Transaction Amount:  ${amount:,.2f}

----------------------------------------------------------------------
2. INDEPENDENT ENGINE TELEMETRY (ISOLATED ANALYSIS)
----------------------------------------------------------------------
[A] GAIT ENGINE (Behavioral Biometrics)
    Anomaly Score:   {telemetry['gait_anomaly_score']} / 1.0
    Status:          {'HIGH RISK (Possible Bot/ATO)' if telemetry['gait_anomaly_score'] > 0.70 else 'NORMAL (Human Baseline'}

[B] TEMPO ENGINE (Ledger Velocity)
    Velocity Score:  {telemetry['tempo_velocity_score']} / 1.0
    Status:          {'HIGH RISK (Smurfing Burst)' if telemetry['tempo_velocity_score'] > 0.70 else 'NORMAL (Standard Cadence)'}

[C] MIRAGE ENGINE (Corporate Substance)
    Reality Index:   {telemetry['mirage_reality_index']} / 100.0
    Status:          {'HIGH RISK (Ghost Shell)' if telemetry['mirage_reality_index'] < 30 else 'NORMAL (Verified Entity)'}

----------------------------------------------------------------------
3. MATHEMATICAL CONVERGENCE & TYPOLOGY
----------------------------------------------------------------------
Calculated Reality Risk: {(100 - telemetry['mirage_reality_index']) / 100:.2f}
Calculated Amplification: {min(1.0, telemetry['tempo_velocity_score'] * (1 + telemetry['gait_anomaly_score'])):.2f}

NORMALIZED ML SCORE: {decision['ml_prediction_model']['normalized_ml_score']} / 1.0
AML THRESHOLD MET:   {str(decision['ml_prediction_model']['is_money_laundering_suspect']).upper()}

----------------------------------------------------------------------
4. REGULATORY VERDICT & ENFORCEMENT ACTION
----------------------------------------------------------------------
SYSTEM VERDICT:      {decision['verdict']}
ENFORCEMENT ACTION:  {decision['action_required']}
COMPLIANCE REASON:   {decision['compliance_reason']}
======================================================================
    """
    return report.strip()