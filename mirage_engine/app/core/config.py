import os

class Settings:
    # Redis configuration for Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Google Places API key — used to turn co_location_density from a
    # random number into a real check of how many businesses are
    # registered at the same address as the submitted company. Get one at
    # https://console.cloud.google.com/apis/credentials after enabling
    # "Places API (New)" and "Geocoding API" for your project.
    # If left empty, worker.py falls back to the old simulated value and
    # logs a warning — it will NOT silently pretend to be real.
    GOOGLE_PLACES_API_KEY: str = os.getenv("GOOGLE_PLACES_API_KEY", "")

    # Kept for backwards compatibility / other future OSINT providers
    # (e.g. Shodan, WHOIS XML) — not currently used by any code path.
    OSINT_API_KEY: str = os.getenv("OSINT_API_KEY", "dummy_key_for_now")

settings = Settings()