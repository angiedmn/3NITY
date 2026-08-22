"""
vector_store.py
----------------
PostgreSQL + pgvector storage for gait session vectors. Lets you ask:
"Has another account typed with this exact cadence in the last 30 days?"
via a fast cosine-similarity query, which is a strong bot-swarm signal
(many different account_ids sharing near-identical kinematics).

Requires:
  - A running Postgres instance with the pgvector extension installed
    (CREATE EXTENSION IF NOT EXISTS vector;)
  - Connection details supplied via environment variables (see below)

Set these before running:
    GAIT_DB_HOST, GAIT_DB_PORT, GAIT_DB_NAME, GAIT_DB_USER, GAIT_DB_PASSWORD
"""

import os
from typing import Optional

import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector

from features import FEATURE_COLUMNS

VECTOR_DIM = len(FEATURE_COLUMNS)

DB_CONFIG = {
    "host": os.environ.get("GAIT_DB_HOST", "localhost"),
    "port": os.environ.get("GAIT_DB_PORT", "5432"),
    "dbname": os.environ.get("GAIT_DB_NAME", "gait_engine"),
    "user": os.environ.get("GAIT_DB_USER", "postgres"),
    "password": os.environ.get("GAIT_DB_PASSWORD", "postgres"),
}


def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    register_vector(conn)
    return conn


def init_db() -> None:
    """Create the extension and table if they don't exist yet."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS gait_sessions (
                    id SERIAL PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    embedding VECTOR({VECTOR_DIM}) NOT NULL,
                    gait_score FLOAT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS gait_sessions_embedding_idx
                ON gait_sessions USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
                """
            )
        conn.commit()
    finally:
        conn.close()


def upsert_session_vector(account_id: str, vector: np.ndarray, gait_score: float) -> None:
    """Insert a new session vector (kept as an append-only log, not a true upsert,
    since each login/transaction is its own session)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO gait_sessions (account_id, embedding, gait_score) "
                "VALUES (%s, %s, %s)",
                (account_id, vector.tolist(), float(gait_score)),
            )
        conn.commit()
    finally:
        conn.close()


def find_nearest_session(
    vector: np.ndarray, exclude_account_id: Optional[str] = None, lookback_days: int = 30
) -> Optional[dict]:
    """
    Cosine-similarity search: find the most similar prior session vector
    within the lookback window, excluding the querying account itself.
    A very high similarity across DIFFERENT account_ids is a strong
    'shared bot script' signal.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = """
                SELECT account_id, 1 - (embedding <=> %s::vector) AS similarity
                FROM gait_sessions
                WHERE created_at > now() - (%s || ' days')::interval
            """
            params = [vector.tolist(), lookback_days]
            if exclude_account_id:
                query += " AND account_id != %s"
                params.append(exclude_account_id)
            query += " ORDER BY embedding <=> %s::vector LIMIT 1"
            params.append(vector.tolist())

            cur.execute(query, params)
            row = cur.fetchone()
            if row is None:
                return None
            return {"account_id": row[0], "similarity": float(row[1])}
    finally:
        conn.close()


def bulk_load_sessions(df) -> None:
    """Bulk-load a DataFrame of already-scored sessions (from train_model.py)
    into pgvector, e.g. for backfilling historical data."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            rows = [
                (row["account_id"], row[FEATURE_COLUMNS].tolist(), row["Gait_Score"])
                for _, row in df.iterrows()
            ]
            execute_values(
                cur,
                "INSERT INTO gait_sessions (account_id, embedding, gait_score) VALUES %s",
                rows,
                template="(%s, %s, %s)",
            )
        conn.commit()
    finally:
        conn.close()