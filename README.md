<div align="center">

# Project 3NITY
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

</div>

---
# Project 3nity

Project 3nity is an autonomous Anti-Money Laundering (AML) engine designed to detect distributed financial crime, Authorized Push Payment (APP) fraud, and offshore shell networks.

Traditional AML tools track the money and fail when funds are fractured across thousands of accounts. 3nity abandons financial tracking and instead triangulates three non-financial signals: operator behavior, network topology, and corporate substance.

## The Three Engines

3nity operates via three distinct evaluation models that fuse into a single risk score.

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

## Technology Stack

The MVP architecture is built on a lightweight, Python-centric web stack designed for rapid deployment and sub-second inference.

### Core Infrastructure

- **Backend Framework:** FastAPI (Python)
- **Primary Database:** PostgreSQL (via SQLAlchemy or Prisma)
- **Task Queue:** Celery + Redis (for asynchronous Mirage engine lookups)

### Machine Learning & Data Processing

- **Data Manipulation:** Pandas, NumPy
- **Graph Processing:** NetworkX (in-memory topology analysis)
- **Anomaly Detection:** Scikit-learn

## System Architecture

1. **Ingestion:** Transaction and telemetry payloads are received via FastAPI endpoints.
2. **Synchronous Scoring:** The Gait and Tempo models evaluate the payload in-memory using Scikit-learn and NetworkX.
3. **Asynchronous Verification:** The Mirage engine queues external background lookups via Celery to verify corporate substance without blocking the main thread.
4. **Fusion:** A weighted decision matrix compiles the `Gait_Score`, `Tempo_Score`, and `Mirage_Score` into a final 0-100 Risk Index.
5. **Action:** Transactions crossing the risk threshold are flagged for compliance review.

## Local Setup and Installation

### Prerequisites

- Python 3.10+
- PostgreSQL
- Redis (for Celery workers)

### Installation Steps

1. Clone the repository:

```bash
   git clone https://github.com/your-org/project-3nity.git
   cd project-3nity
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
DATABASE_URL=postgresql://user:password@localhost/3nity_db
REDIS_URL=redis://localhost:6379/0


5. Run database migrations:

```bash
   alembic upgrade head
```

6. Start the Celery worker (in a separate terminal):

```bash
   celery -A core.tasks worker --loglevel=info
```

7. Start the FastAPI server:

```bash
   uvicorn main:app --reload --port 8000
```

## API Endpoints

- `POST /api/v1/analyze` — Submit a transaction payload containing telemetry and recipient data for synchronous Gait and Tempo scoring.
- `GET /api/v1/network/{entity_id}` — Retrieve the local transaction graph topology for a specific entity.
- `GET /api/v1/substance/{entity_id}` — Check the async status of a Mirage corporate substance audit.

## License

Proprietary and Confidential. All rights reserved.
