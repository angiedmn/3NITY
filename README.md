# Mirage — Shell Company Reality-Index Engine

Scores submitted companies for shell-company / financial-crime risk using
an XGBoost classifier trained on jurisdiction risk (FATF-style), domain
age, IP/hosting signals, address co-location density, and FX transfer
variance. Falls back to a rule-based heuristic if no trained model is
present.

## Stack

- **API**: FastAPI (`app.main:app`)
- **Async scoring**: Celery worker + Redis broker/backend
- **Model**: XGBoost, trained via `train_model.py`
- **OSINT**: WHOIS (primary) with an RDAP fallback for domain age;
  jurisdiction risk via a static FATF/Basel-style lookup table

## Setup

```bash
# 1. Train (or retrain) the classifier — writes app/engine/models/mirage_classifier.json
python train_model.py

# 2. Bring up Redis, the API, and the Celery worker
docker compose up --build
```

API will be available at `http://localhost:8000`.

## Running tests

```bash
pytest test_engine.py
```

## Known gaps / caveats

- **`app/main.py` isn't part of this file set.** `docker-compose.yml`
  points `uvicorn` at `app.main:app`; if that module doesn't exist yet in
  your repo, `api` will fail to start. Same goes for the package
  `__init__.py` files implied by the import paths (`app/schemas/`,
  `app/engine/`, `app/tasks/`).
- **`has_commercial_ip` is currently a weak signal.** The real hosting/IP
  intelligence check (`fetch_ip_intelligence` in `osint.py`) is an
  unimplemented placeholder that always returns `True`; the value
  actually fed into the model today comes from a plain DNS-resolves
  check, which most live domains pass regardless of hosting quality.
- **`simulate_10k.py` is an in-sample check**, not a held-out
  generalization test — it draws from the same synthetic distributions
  used in `train_model.py`. Validate against real labeled data before
  trusting its reported accuracy.