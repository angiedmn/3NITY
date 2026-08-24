<div align="center">

# Project Trinity
### Autonomous Multi-Layered Intelligence Against Distributed Financial Crime

![Last Commit](https://img.shields.io/github/last-commit/angiedmn/3NITY?style=flat-square&color=yellow)
![Top Language](https://img.shields.io/github/languages/top/angiedmn/3NITY?style=flat-square&color=blue)
![Languages](https://img.shields.io/github/languages/count/angiedmn/3NITY?style=flat-square&color=green)
![License](https://img.shields.io/badge/license-Proprietary-blue?style=flat-square)

<br/>

**Built with the tools and technologies:**

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

</div>

---

## Overview

Project Trinity is an autonomous Anti-Money Laundering (AML) engine designed to detect distributed financial crime, Authorized Push Payment (APP) fraud, and offshore shell networks.

Traditional AML tools track the money and fail when funds are fractured across thousands of accounts. Trinity abandons financial tracking and instead triangulates three non-financial signals: operator behavior, network topology, and corporate substance.

---

## The Three Engines

Trinity operates via three distinct evaluation models that fuse into a single risk score.

### 1. Gait (Behavioral & Cognitive Strain Model)

Detects whether an account is operated by an automated bot swarm or a coerced human mule.

- **Focus:** Interaction telemetry (clipboard usage, app switching, session dwell time)
- **Algorithm:** Unsupervised anomaly detection (Isolation Forest) mapping telemetry against baseline human behavior

### 2. Tempo (Temporal Graph & Network Topology Model)

Detects the coordination rhythm and shape of transaction flows across accounts over time.

- **Focus:** Fan-In/Fan-Out "smurfing" patterns and "Hot Potato" pass-through velocity
- **Algorithm:** Directed graph traversal and time-window aggregations to identify structural funneling

### 3. Mirage (Corporate Substance Model)

Audits the physical and digital reality of the destination entity to catch offshore shell companies.

- **Focus:** Digital exhaust, commercial IP density, and shared nominee address tracking
- **Algorithm:** Asynchronous multi-criteria heuristic engine to generate a corporate "Reality Index"

---

## Local Setup and Installation

### Prerequisites

- Python 3.10+
- PostgreSQL (with `pgvector` extension enabled)
- Redis (for Celery workers)

### Installation Steps

1. Clone the repository:

```bash
   git clone https://github.com/angiedmn/3NITY.git
   cd 3NITY
```

2. Set up a virtual environment:

```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
   pip install -r requirements.txt
```

4. Configure environment variables. Create a `.env` file in the root directory:
DATABASE_URL=postgresql://user:password@localhost/trinity_db
REDIS_URL=redis://localhost:6379/0
GAIT_DB_HOST=localhost
GAIT_DB_PORT=5432
GAIT_DB_NAME=gait_engine
GAIT_DB_USER=postgres
GAIT_DB_PASSWORD=postgres


5. Train the local ML model. Download the IBM dataset to the folder and run the full pipeline:

```bash
   python test_pipeline.py
```

6. Start the FastAPI server:

```bash
   uvicorn api:app --reload --port 8000
```

### Running with Docker

Alternatively, spin up the full stack (API, PostgreSQL, Redis) with Docker Compose:

```bash
docker compose up --build
```

## API Endpoints

- `POST /api/v1/telemetry/gait` — Submit a transaction payload containing telemetry and recipient data for synchronous Gait scoring.
- `GET /health` — Verify system status and model readiness.

## License

Proprietary and Confidential. All rights reserved.
