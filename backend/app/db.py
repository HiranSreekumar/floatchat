"""
PostgreSQL storage for ingested ARGO profiles.
No LLM involvement anywhere in this file.
"""
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from .config import DATABASE_URL

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    profile_id   TEXT PRIMARY KEY,
    platform_id  TEXT NOT NULL,
    lat          DOUBLE PRECISION NOT NULL,
    lon          DOUBLE PRECISION NOT NULL,
    profile_date DATE NOT NULL,
    source       TEXT DEFAULT 'argo',
    is_synthetic BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS measurements (
    id           BIGSERIAL PRIMARY KEY,
    profile_id   TEXT NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    pressure     DOUBLE PRECISION,
    temperature  DOUBLE PRECISION,
    salinity     DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_profiles_latlon ON profiles(lat, lon);
CREATE INDEX IF NOT EXISTS idx_profiles_date ON profiles(profile_date);
CREATE INDEX IF NOT EXISTS idx_measurements_profile ON measurements(profile_id);
"""


def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def upsert_profile(conn, profile_id, platform_id, lat, lon, profile_date, source="argo", is_synthetic=False):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO profiles (profile_id, platform_id, lat, lon, profile_date, source, is_synthetic)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (profile_id) DO UPDATE SET
                 platform_id = EXCLUDED.platform_id, lat = EXCLUDED.lat, lon = EXCLUDED.lon,
                 profile_date = EXCLUDED.profile_date, source = EXCLUDED.source""",
            (profile_id, platform_id, lat, lon, profile_date, source, is_synthetic),
        )


def insert_measurements(conn, profile_id, levels):
    if not levels:
        return
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO measurements (profile_id, pressure, temperature, salinity) VALUES %s",
            [(profile_id, p, t, s) for (p, t, s) in levels],
        )


def execute(conn, sql, params):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def row_counts():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) c FROM profiles")
            p = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) c FROM measurements")
            m = cur.fetchone()["c"]
    return {"profiles": p, "measurements": m}
