import asyncio
import json
import logging
import math
import datetime
import urllib.request
import urllib.error
from typing import Optional
from urllib.parse import urlparse, quote

logger = logging.getLogger(__name__)

RDAP_TIMEOUT_SECONDS = 10.0
GEOCODE_TIMEOUT_SECONDS = 8.0
PLACES_TIMEOUT_SECONDS = 8.0
TRANCO_TIMEOUT_SECONDS = 8.0

# Tight radius (meters): we want "same building / same mailbox", which is
# the actual shell-company signal — not "same neighborhood", which would
# just count unrelated foot traffic and wash out the signal entirely.
COLOCATION_SEARCH_RADIUS_METERS = 50


def _fetch_rdap_sync(domain: str) -> dict:
    """Blocking RDAP GET, run inside a worker thread via asyncio.to_thread
    so the async caller doesn't block the event loop. Uses stdlib urllib
    instead of httpx deliberately: this is the ONE dependency this project
    doesn't need to take on, since a single JSON GET doesn't need httpx's
    feature set, and pulling it in drags in `anyio`, which can land you in
    a pip resolution conflict against whatever anyio version FastAPI's
    Starlette dependency happens to require at build time.
    """
    url = f"https://rdap.org/domain/{quote(domain, safe='')}"
    req = urllib.request.Request(url, headers={"Accept": "application/rdap+json"})
    with urllib.request.urlopen(req, timeout=RDAP_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


async def fetch_domain_data(domain: str) -> dict:
    """Uses modern RDAP (HTTPS) to avoid classic WHOIS's Port 43 blocks.

    Returns {"age_days": None} on ANY failure (network error, missing
    registration event, bad date, etc). This is important: a genuine
    domain age of 0 (registered today) is a real and highly meaningful
    result, and must never be conflated with "the lookup failed" the
    way a sentinel like 0 or -1 would.
    """
    try:
        data = await asyncio.to_thread(_fetch_rdap_sync, domain)

        # Find the 'registration' event in the JSON data
        events = data.get("events", [])
        creation_date_str = None
        for event in events:
            if event.get("eventAction") == "registration":
                creation_date_str = event.get("eventDate")
                break

        if creation_date_str:
            # RDAP always returns strict ISO-8601 dates (e.g. 2004-04-09T12:00:00Z)
            creation_date = datetime.datetime.fromisoformat(creation_date_str.replace('Z', '+00:00'))
            now = datetime.datetime.now(datetime.timezone.utc)
            age_days = (now - creation_date).days
            return {"age_days": max(0, age_days)}

        logger.warning(f"RDAP lookup for {domain} returned no registration event.")
        return {"age_days": None}
    except (urllib.error.URLError, TimeoutError) as e:
        logger.error(f"RDAP lookup failed for {domain}: {e}")
        return {"age_days": None}
    except Exception as e:
        logger.error(f"RDAP lookup failed for {domain}: {e}")
        return {"age_days": None}


async def fetch_ip_intelligence(domain: str) -> dict:
    """PLACEHOLDER — this does NOT perform real IP/ASN intelligence.

    It always reports is_datacenter_ip=True. Left as-is rather than
    dressed up as a working check: almost any live domain resolves to
    *some* IP, so treating "resolves at all" as "commercial IP" gives
    false confidence. Before trusting `has_commercial_ip` for real
    scoring decisions, wire this up to a genuine ASN/IP-intelligence
    provider (config.py already has a placeholder OSINT_API_KEY for
    exactly this — e.g. Shodan, IPinfo, or similar).
    """
    await asyncio.sleep(0.1)
    logger.warning(
        "fetch_ip_intelligence is a placeholder and always returns True — "
        "has_commercial_ip is not currently a reliable signal."
    )
    return {"is_datacenter_ip": True}


def _geocode_address_sync(address: str, api_key: str) -> Optional[tuple]:
    """Turns a free-text address into (lat, lng) via Google's Geocoding
    API. Returns None if the address can't be resolved."""
    url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?address={quote(address)}&key={quote(api_key)}"
    )
    with urllib.request.urlopen(url, timeout=GEOCODE_TIMEOUT_SECONDS) as response:
        data = json.loads(response.read().decode("utf-8"))

    if data.get("status") != "OK" or not data.get("results"):
        return None
    loc = data["results"][0]["geometry"]["location"]
    return (loc["lat"], loc["lng"])


def _nearby_places_count_sync(lat: float, lng: float, api_key: str) -> int:
    """Counts places Google Places (New) knows about within a tight
    radius of the given point — used as a proxy for how many businesses
    are registered at the same address as the submitted company."""
    url = "https://places.googleapis.com/v1/places:searchNearby"
    body = json.dumps({
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": COLOCATION_SEARCH_RADIUS_METERS,
            }
        }
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            # Minimal field mask — we only need a count, not full place
            # details, which keeps each request as cheap as possible.
            "X-Goog-FieldMask": "places.id",
        },
    )
    with urllib.request.urlopen(req, timeout=PLACES_TIMEOUT_SECONDS) as response:
        data = json.loads(response.read().decode("utf-8"))
    return len(data.get("places", []))


async def fetch_colocation_density(address: str, api_key: str) -> Optional[int]:
    """Real co-location density: how many businesses Google Places
    reports within ~50m of the submitted registered_address. This is
    the actual shell-company signal (many unrelated companies sharing
    one mailbox/address) that the old code faked with random.randint().

    Returns None — meaning "couldn't determine, fall back to simulated
    data" — if no api_key is configured, the address can't be geocoded,
    or the request fails for any reason. A real result of 0 or 1 (this
    address has almost no co-located businesses) is a meaningful,
    legitimate value and must never be treated as a failure.
    """
    if not api_key:
        return None
    if not address:
        return None
    try:
        coords = await asyncio.to_thread(_geocode_address_sync, address, api_key)
        if coords is None:
            logger.warning(f"Could not geocode registered_address: {address!r}")
            return None
        lat, lng = coords
        return await asyncio.to_thread(_nearby_places_count_sync, lat, lng, api_key)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        logger.error(f"Co-location density lookup failed for {address!r}: {e}")
        return None
    except Exception as e:
        logger.error(f"Co-location density lookup failed for {address!r}: {e}")
        return None


def _fetch_tranco_rank_sync(domain: str) -> Optional[int]:
    url = f"https://tranco-list.eu/api/ranks/domain/{quote(domain, safe='')}"
    with urllib.request.urlopen(url, timeout=TRANCO_TIMEOUT_SECONDS) as response:
        data = json.loads(response.read().decode("utf-8"))
    ranks = data.get("ranks", [])
    if not ranks:
        return None
    # Most recent entry — Tranco returns the list in chronological order.
    return ranks[-1].get("rank")


async def fetch_traffic_score(domain: str) -> Optional[float]:
    """Real traffic proxy via the free Tranco top-1M domain ranking — no
    API key required at all. Maps rank 1 -> ~1.0 and rank 1,000,000 ->
    ~0.0 on a log scale (traffic differences are log-distributed, not
    linear — rank 100 vs 1,000 matters far more than rank 900,000 vs
    901,000).

    Returns None if the domain isn't in Tranco's top 1M at all, or the
    request fails — which is completely normal for the overwhelming
    majority of small, real, legitimate businesses too. Callers should
    treat this as "no signal, fall back to simulated data", NOT as
    evidence the company is a shell — being outside the top 1M sites on
    the internet says almost nothing on its own.
    """
    try:
        rank = await asyncio.to_thread(_fetch_tranco_rank_sync, domain)
        if not rank or rank <= 0:
            return None
        score = 1.0 - min(1.0, math.log10(rank) / 6.0)
        return max(0.0, min(1.0, score))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        logger.error(f"Tranco rank lookup failed for {domain}: {e}")
        return None
    except Exception as e:
        logger.error(f"Tranco rank lookup failed for {domain}: {e}")
        return None


async def gather_digital_exhaust(domain_url: str) -> dict:
    """Fetches all digital footprint data concurrently."""
    domain = urlparse(str(domain_url)).hostname or str(domain_url).strip("/")
    if domain.startswith("www."):
        domain = domain[4:]

    domain_task = fetch_domain_data(domain)
    ip_task = fetch_ip_intelligence(domain)

    domain_result, ip_result = await asyncio.gather(domain_task, ip_task)

    return {
        "domain_age_days": domain_result.get("age_days"),
        "has_commercial_ip": ip_result.get("is_datacenter_ip", False)
    }