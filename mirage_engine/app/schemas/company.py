from pydantic import BaseModel, Field, HttpUrl
from typing import List

class CompanyPayload(BaseModel):
    company_name: str
    registration_number: str
    registered_address: str
    domain_name: HttpUrl
    jurisdiction_code: str
    # --- Financial Tracking Fields ---
    # ge=0.0 added: a negative amount would flip the sign of the derived
    # fx_variance_percentage calculation in worker.py and could let a
    # malformed/adversarial payload dodge the "Irregular FX Variance" flag.
    amount_paid_usd: float = Field(default=0.0, ge=0.0, description="Amount sent to entity")
    amount_received_usd: float = Field(default=0.0, ge=0.0, description="Amount received post-FX conversion")

class MirageFeatures(BaseModel):
    co_location_density: int = Field(default=1, ge=1)
    domain_age_days: int = Field(default=0, ge=0)
    has_commercial_ip: bool = Field(default=True)
    local_traffic_score: float = Field(default=0.0, ge=0.0, le=1.0)
    fatf_risk_score: float = Field(default=0.0, ge=0.0, le=10.0)
    # Internal FX Variance calculation. Deliberately left unbounded: with
    # both amount fields now non-negative this can still legitimately go
    # negative (received > paid) or as high as 1.0 (nothing received), and
    # clamping it here risks rejecting real, if unusual, payloads outright.
    # Clip defensively at the call site if a hard ceiling is ever needed.
    fx_variance_percentage: float = Field(default=0.0)

class RealityIndexResult(BaseModel):
    company_name: str
    reality_index: float = Field(..., ge=0.0, le=100.0)
    risk_tier: str
    is_shell_suspected: bool
    flags: List[str] = Field(default_factory=list)