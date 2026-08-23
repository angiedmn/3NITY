import pytest
from app.schemas.company import CompanyPayload, MirageFeatures
from app.engine.scoring import score_company_substance

def test_low_risk_usa_company():
    """Test that a clean USA company passes as Low Risk."""
    payload = CompanyPayload(
        company_name="Safe Tech LLC",
        registration_number="US-12345",
        registered_address="123 Silicon Valley, CA",
        domain_name="https://safetech.com",
        jurisdiction_code="USA",
        amount_paid_usd=1000.0,
        amount_received_usd=990.0  # Normal 1% FX variance
    )
    
    features = MirageFeatures(
        co_location_density=1,
        domain_age_days=3000,
        has_commercial_ip=True,
        local_traffic_score=0.95,
        fatf_risk_score=1.6,  # Low risk USA score
        fx_variance_percentage=0.01
    )
    
    result = score_company_substance(payload, features)
    
    assert result["risk_tier"] == "Low", "Expected Low Risk but got something else!"
    assert result["is_shell_suspected"] is False
    assert result["reality_index"] > 80.0

def test_high_risk_sanctioned_company():
    """Test that a sketchy PRK (North Korea) company with huge value loss is flagged as High Risk."""
    payload = CompanyPayload(
        company_name="Shady Exports Ltd",
        registration_number="PRK-999",
        registered_address="Unknown",
        domain_name="https://shady-exports-new.com",
        jurisdiction_code="PRK",
        amount_paid_usd=100000.0,
        amount_received_usd=60000.0  # Massive 40% value loss (laundering)
    )
    
    features = MirageFeatures(
        co_location_density=5000, # Thousands of companies at one address
        domain_age_days=4,        # Domain created 4 days ago
        has_commercial_ip=False,
        local_traffic_score=0.01,
        fatf_risk_score=10.0,     # Maximum FATF risk
        fx_variance_percentage=0.40
    )
    
    result = score_company_substance(payload, features)
    
    assert result["risk_tier"] == "High", "Expected High Risk for sanctioned country!"
    assert result["is_shell_suspected"] is True
    assert result["reality_index"] < 40.0
    # Ensure our human-readable FX flag successfully triggered
    assert any("Irregular FX Variance" in flag for flag in result["flags"])