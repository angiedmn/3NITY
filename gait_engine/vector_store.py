import os
from typing import Optional

import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
from features import FEATURE_COLUMNS
from typing import Optional, Dict, Any
VECTOR_DIM = len(FEATURE_COLUMNS) #config
DB_CONFIG = { #connection details
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

#integrating postgresql w/ pgvector
def init_db() -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS gait_sessions (
                    id SERIAL PRIMARY KEY, account_id TEXT NOT NULL,
                    embedding VECTOR({VECTOR_DIM}) NOT NULL,gait_score FLOAT NOT NULL,
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

#append a new session vector to the database
def upsert_session_vector(account_id: str, vector: np.ndarray, gait_score: float) -> None:
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
    #use cosine similarity
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

#delets data older than 30 days (retention days)
def prune_stale_sessions(retention_days: int = 30) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM gait_sessions WHERE created_at < now() - (%s || ' days')::interval",
                (retention_days,)
            )
        conn.commit()
    finally:
        conn.close()
        import os


DB_URL = os.environ.get("SUPABASE_DB_URL")

def get_connection():
    if not DB_URL:
        raise ValueError("SUPABASE_DB_URL environment variable is missing.")
    conn = psycopg2.connect(DB_URL)
    register_vector(conn)
    return conn

def check_gait_baseline(account_id: str, vector: np.ndarray, lookback_days: int = 30) -> Optional[float]:
    """
    Compares the incoming telemetry against the account's historical baseline.
    Returns cosine similarity (1.0 = identical, 0.0 = completely different).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = """
                SELECT 1 - (embedding <=> %s::vector) AS similarity
                FROM gait_sessions
                WHERE account_id = %s AND created_at > now() - (%s || ' days')::interval
                ORDER BY embedding <=> %s::vector LIMIT 1
            """
            cur.execute(query, (vector.tolist(), account_id, lookback_days, vector.tolist()))
            row = cur.fetchone()
            return float(row[0]) if row else None
    finally:
        conn.close()

def save_gait_session(account_id: str, vector: np.ndarray) -> None:
    """Inserts a new telemetry session vector into Supabase."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO gait_sessions (account_id, embedding) VALUES (%s, %s::vector)",
                (account_id, vector.tolist())
            )
            conn.commit()
    finally:
        conn.close()