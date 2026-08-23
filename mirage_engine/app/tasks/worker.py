import asyncio
import random
import logging
import socket
import whois
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Optional
from urllib.parse import urlparse
from datetime import datetime, timezone
from app.tasks.celery_app import app as celery_app
from app.schemas.company import CompanyPayload, MirageFeatures
from app.engine.scoring import score_company_substance

# RDAP-based fallback lookup — used when classic WHOIS (port 43) fails,
# times out, or is blocked/rate-limited by the target registry. Uses only
# stdlib urllib under the hood (no httpx/anyio), to avoid pip dependency
# conflicts with FastAPI's own transitive dependencies. NOTE: adjust this
# import path to match where osint.py actually lives in your project
# (e.g. `app.services.osint`).
from app.services.osint import (
    fetch_domain_data as fetch_rdap_domain_data,
    fetch_colocation_density,
    fetch_traffic_score,
)
# NOTE: adjust this import path to match wherever config.py actually lives
# in your project (e.g. `app.config` vs a different location).
from app.core.config import settings

logger = logging.getLogger(__name__)

WHOIS_TIMEOUT_SECONDS = 8
DNS_TIMEOUT_SECONDS = 5

# python-whois has no reliable built-in timeout across versions, and some
# registries simply never respond. Running the blocking call in a small
# thread pool lets us enforce a hard timeout instead of hanging a Celery
# worker indefinitely.
# NOTE: if this worker's Celery pool is ever switched from the default
# "prefork" (separate processes) to a threaded/eventlet/gevent pool,
# socket.setdefaulttimeout() below becomes a *process-wide* global and
# can race across concurrently-running tasks. Under prefork (the
# default, and what this project uses) each task runs in its own OS
# process, so this is safe as written.
_whois_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="whois-lookup")

# --- THE RISK ORACLE ---
# A representative map of ISO-3166 Alpha-3 codes to FATF/Basel risk scores (0.0 - 10.0)
JURISDICTION_RISK_MAP = {
    # --- LOW RISK (1.0 - 2.9) ---
    "AND": 1.5, "AUS": 1.4, "AUT": 1.3, "BEL": 1.5, "CAN": 1.4, "CHE": 1.1,
    "CHL": 2.5, "CZE": 2.1, "DEU": 1.6, "DNK": 1.2, "ESP": 1.8, "EST": 1.2,
    "FIN": 1.1, "FRA": 1.7, "GBR": 1.5, "IRL": 1.4, "ISL": 1.3, "ISR": 2.2,
    "ITA": 2.0, "JPN": 1.5, "KOR": 1.8, "LIE": 1.2, "LTU": 1.6, "LUX": 1.4,
    "LVA": 1.9, "MCO": 1.8, "NLD": 1.6, "NOR": 1.2, "NZL": 1.1, "PRT": 1.9,
    "SGP": 1.3, "SMR": 1.5, "SVK": 2.1, "SVN": 1.7, "SWE": 1.1, "USA": 1.6,
    "URY": 2.6,

    # --- MEDIUM RISK (3.0 - 5.9) ---
    "ALB": 4.5, "ARG": 4.2, "ARM": 4.1, "ATG": 5.0, "BHS": 4.8, "BHR": 3.5,
    "BLZ": 5.2, "BMU": 3.8, "BOL": 5.5, "BRA": 4.6, "BRB": 4.5, "BRN": 4.1,
    "BWA": 3.9, "COL": 4.7, "CPV": 4.2, "CRI": 4.1, "CYP": 3.5, "DMA": 4.9,
    "DOM": 5.1, "ECU": 5.0, "FJI": 4.5, "GEO": 3.8, "GHA": 5.2, "GRC": 3.1,
    "GRD": 4.7, "GTM": 5.4, "GUY": 5.2, "HND": 5.6, "HRV": 3.2, "HUN": 3.4,
    "IDN": 4.8, "IND": 4.5, "JAM": 5.5, "JOR": 4.9, "KAZ": 5.1, "KEN": 5.4,
    "KNA": 4.8, "KWT": 4.1, "LCA": 4.5, "LKA": 5.0, "MAR": 4.8, "MDV": 4.2,
    "MEX": 5.1, "MKD": 4.5, "MLT": 3.5, "MNG": 4.7, "MUS": 3.8, "MYS": 4.1,
    "NAM": 4.8, "OMN": 4.0, "PER": 4.8, "PHL": 5.2, "POL": 3.2, "PRY": 5.5,
    "QAT": 3.9, "ROU": 3.6, "RWA": 4.5, "SAU": 4.2, "SEN": 5.5, "SLV": 5.2,
    "SRB": 4.7, "SYC": 4.1, "THA": 4.9, "TTO": 4.8, "TUN": 5.1, "TUR": 5.6,
    "TWN": 3.1, "VCT": 4.6, "VNM": 5.4, "ZAF": 5.3, "ZMB": 5.5,
    # NOTE: CHN and ARE were previously absent from this map entirely —
    # both are major economies/financial hubs, so every company registered
    # there was silently falling through to the "unknown jurisdiction"
    # default instead of a real score. These two placeholder values are
    # illustrative only; validate against real FATF/Basel AML Index data
    # before relying on them.
    "CHN": 5.3, "ARE": 5.8, "HKG": 4.4,

    # --- HIGH RISK & SECRECY JURISDICTIONS (6.0 - 8.9) ---
    "AFG": 8.5, "AGO": 7.2, "AZE": 6.1, "BDI": 7.8, "BEN": 6.5, "BFA": 7.5,
    "BGD": 6.2, "BGR": 6.0, "BIH": 6.1, "BLR": 8.5, "BVI": 8.9, "CAF": 8.2,
    "CIV": 6.8, "CMR": 7.5, "COD": 8.6, "COG": 7.5, "COM": 7.0, "CUB": 7.5,
    "CYM": 8.5, "DJI": 6.8, "DZA": 6.5, "EGY": 6.2, "ERI": 8.1, "ETH": 6.9,
    "GAB": 6.7, "GIN": 7.1, "GMB": 6.9, "GNB": 7.4, "GNQ": 7.8, "HTI": 8.4,
    "IRQ": 8.2, "KGZ": 6.5, "KHM": 7.5, "LAO": 7.1, "LBN": 7.9, "LBR": 7.2,
    "LBY": 8.5, "LSO": 6.2, "MDA": 6.4, "MDG": 6.8, "MHL": 8.2, "MLI": 8.0,
    "MMR": 8.8, "MOZ": 7.5, "MRT": 6.9, "MWI": 6.5, "NER": 7.4, "NGA": 7.6,
    "NIC": 7.5, "NPL": 6.2, "PAK": 7.2, "PAN": 7.8, "PNG": 7.1, "RUS": 8.7,
    "SDN": 8.6, "SLE": 6.8, "SOM": 8.9, "SSD": 8.7, "SUR": 6.5, "SWZ": 6.5,
    "SYR": 8.9, "TCD": 7.8, "TGO": 6.9, "TJK": 7.2, "TKM": 8.1, "TZA": 7.3,
    "UGA": 7.1, "UKR": 6.8, "UZB": 6.4, "VEN": 8.5, "VUT": 7.5, "YEM": 8.8,
    "ZWE": 7.6,

    # --- EXTREME RISK / SANCTIONED (9.0 - 10.0) ---
    "IRN": 9.8, "PRK": 10.0
}

# Applied when jurisdiction_code isn't in the map above. An unrecognized
# or outright fabricated jurisdiction code is itself a red flag for a
# tool whose job is catching shells — so this now defaults into the
# "high risk" bucket (was 6.5 / "medium"). This is a policy call, not a
# clear-cut bug fix — revert to 6.5 if "unknown" should stay neutral.
DEFAULT_UNKNOWN_JURISDICTION_RISK = 7.5


def _extract_hostname(url) -> Optional[str]:
    """Pulls a bare hostname out of a URL, correctly handling scheme,
    userinfo, port, path, and query — unlike naive
    `.replace("www.", "").split(":")[0]`, which mishandles URLs like
    `http://user:pass@host.com` (would return "user") or anything with
    a path/query attached."""
    hostname = urlparse(str(url)).hostname
    if not hostname:
        return None
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname


def _whois_lookup_sync(domain: str):
    return whois.whois(domain)


def get_real_domain_age(url) -> Optional[int]:
    """Looks up domain registration age via classic WHOIS.

    Returns the age in days, or None if the lookup failed, timed out,
    or returned no usable creation date. Returning None — instead of a
    sentinel like -1 or 0 — matters: a domain that is genuinely 0 days
    old is a real and highly important signal (a very common shell-
    company trait) and must never be treated the same as "we couldn't
    find out."
    """
    domain = _extract_hostname(url)
    if not domain:
        return None

    try:
        future = _whois_executor.submit(_whois_lookup_sync, domain)
        domain_info = future.result(timeout=WHOIS_TIMEOUT_SECONDS)

        creation_date = domain_info.creation_date
        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        if isinstance(creation_date, datetime):
            # WHOIS registries are inconsistent: some return naive datetimes,
            # others return timezone-aware ones. Normalize to UTC-aware on
            # both sides before subtracting, or Python raises "can't
            # subtract offset-naive and offset-aware datetimes".
            if creation_date.tzinfo is None:
                creation_date = creation_date.replace(tzinfo=timezone.utc)
            else:
                creation_date = creation_date.astimezone(timezone.utc)

            age = max(0, (datetime.now(timezone.utc) - creation_date).days)
            logger.info(f"WHOIS SUCCESS: {domain} is {age} days old.")
            return age

        logger.warning(f"WHOIS returned no usable creation date for {domain}.")
        return None

    except FutureTimeoutError:
        logger.warning(f"WHOIS lookup timed out after {WHOIS_TIMEOUT_SECONDS}s for {domain}.")
        return None
    except Exception as e:
        logger.warning(f"WHOIS lookup failed for {domain}: {e}")
        return None


def get_domain_age_with_fallback(url) -> Optional[int]:
    """WHOIS first; if that fails for any reason, fall back to RDAP
    (osint.py), which uses plain HTTPS and isn't subject to the same
    port-43 blocking/rate-limiting that classic WHOIS is."""
    age = get_real_domain_age(url)
    if age is not None:
        return age

    domain = _extract_hostname(url)
    if not domain:
        return None

    try:
        rdap_result = asyncio.run(fetch_rdap_domain_data(domain))
        age = rdap_result.get("age_days")
        if age is not None:
            logger.info(f"RDAP fallback SUCCESS: {domain} is {age} days old.")
        return age
    except Exception as e:
        logger.warning(f"RDAP fallback failed for {domain}: {e}")
        return None


def check_real_dns_resolution(url) -> Optional[bool]:
    """Checks if the domain actually resolves to a real IP address.

    Returns None (not False) if the check itself couldn't complete —
    e.g. a local resolver timeout — which is a different situation from
    a confirmed NXDOMAIN and shouldn't be scored the same way.
    """
    domain = _extract_hostname(url)
    if not domain:
        return None

    try:
        socket.setdefaulttimeout(DNS_TIMEOUT_SECONDS)
        socket.gethostbyname(domain)
        return True
    except socket.gaierror:
        return False
    except socket.error as e:
        logger.warning(f"DNS resolution check failed for {domain}: {e}")
        return None
    finally:
        socket.setdefaulttimeout(None)


@celery_app.task(name="app.tasks.worker.audit_company_task")
def audit_company_task(payload_dict: dict):
    payload = CompanyPayload(**payload_dict)

    # 1. CALCULATE FX VARIANCE
    fx_variance = 0.0
    if payload.amount_paid_usd > 0:
        fx_variance = (payload.amount_paid_usd - payload.amount_received_usd) / payload.amount_paid_usd

    # 2. DYNAMIC FATF SCORING (defaults to a high-risk score if the country is unknown/fake)
    country_code = payload.jurisdiction_code.upper()
    fatf_score = JURISDICTION_RISK_MAP.get(country_code, DEFAULT_UNKNOWN_JURISDICTION_RISK)

    # 3. REAL OSINT GATHERING — each signal is resolved independently.
    # A failed WHOIS lookup must not discard an unrelated, successful DNS check
    # (and vice versa) — they used to be incorrectly coupled together.
    real_domain_age = get_domain_age_with_fallback(payload.domain_name)
    real_has_dns = check_real_dns_resolution(payload.domain_name)

    # Real co-location density (Google Places) and traffic score (Tranco).
    # Both were previously ALWAYS random.randint()/random.uniform() in
    # every code path — never based on the registered_address or
    # domain_name actually submitted, despite registered_address being
    # collected for exactly this purpose. Both now attempt a real lookup
    # first and only fall back to simulation if that lookup can't
    # complete (missing API key, geocoding failure, network error, or
    # a domain outside Tranco's top 1M).
    domain_hostname = _extract_hostname(payload.domain_name)
    real_colocation_density = asyncio.run(
        fetch_colocation_density(payload.registered_address, settings.GOOGLE_PLACES_API_KEY)
    )
    real_traffic_score = (
        asyncio.run(fetch_traffic_score(domain_hostname)) if domain_hostname else None
    )
    if not settings.GOOGLE_PLACES_API_KEY:
        logger.info(
            "GOOGLE_PLACES_API_KEY not configured — co_location_density will "
            "use simulated data instead of a real address lookup."
        )

    # 4. BLEND REAL OSINT WITH SIMULATION (for hackathon safety/fallback).
    # Fallback is only used when the corresponding real lookup is None
    # (genuinely failed) — never when it's a real 0/False value, which
    # is meaningful data in its own right.
    if fatf_score < 4.0:
        sim_density = random.randint(1, 50)
        fallback_age = random.randint(365, 5000)
        fallback_dns = random.random() > 0.05
        sim_traffic = random.uniform(0.5, 1.0)
    elif fatf_score < 7.0:
        sim_density = random.randint(10, 500)
        fallback_age = random.randint(90, 1000)
        fallback_dns = random.random() > 0.40
        sim_traffic = random.uniform(0.2, 0.7)
    else:
        sim_density = random.randint(500, 4000)
        fallback_age = random.randint(5, 300)
        fallback_dns = random.random() > 0.85
        sim_traffic = random.uniform(0.01, 0.3)

    final_domain_age = real_domain_age if real_domain_age is not None else fallback_age
    # NOTE: this only confirms the domain resolves via DNS, not that it sits on
    # genuinely "commercial" infrastructure (see fetch_ip_intelligence's
    # docstring in osint.py) — treat it as a weak signal until a real
    # IP/ASN-intelligence check is wired in.
    final_comm_ip = real_has_dns if real_has_dns is not None else fallback_dns
    final_density = real_colocation_density if real_colocation_density is not None else sim_density
    final_traffic = real_traffic_score if real_traffic_score is not None else sim_traffic

    # 5. BUILD THE FEATURE VECTOR
    features = MirageFeatures(
        co_location_density=final_density,
        domain_age_days=final_domain_age,
        has_commercial_ip=final_comm_ip,
        local_traffic_score=final_traffic,
        fatf_risk_score=fatf_score,
        fx_variance_percentage=fx_variance
    )

    # 6. SCORE IT
    return score_company_substance(payload, features)