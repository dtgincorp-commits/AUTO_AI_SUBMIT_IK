"""
Persistent cache for expensive OEM inventory fetches (residential-proxy /
WAF-unlocked calls to Tesla, BMW, Toyota, etc.).

These fetches are slow (15-40s) and costly, so they must NOT run inline on
every user search. Instead the source reads from this SQLite cache and only
hits the proxy on a miss (or when a background refresher warms it). Keyed by
(source, model, zip, radius); rows carry a timestamp so callers enforce a TTL.

SQLite chosen over st.cache_data alone because it survives process restarts
and is shared across Streamlit sessions — a warm cache from one user (or a
scheduled warmer) serves everyone until the TTL lapses.
"""
import os
import json
import time
import sqlite3
import threading

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", ".oem_cache.db")
_LOCK = threading.Lock()


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB_PATH, timeout=10)
    c.execute(
        "CREATE TABLE IF NOT EXISTS oem_cache ("
        "source TEXT, model TEXT, zip TEXT, radius INTEGER, "
        "payload TEXT, ts REAL, "
        "PRIMARY KEY (source, model, zip, radius))"
    )
    return c


def cache_get(source: str, model: str, zip_code: str, radius: int, ttl: float):
    """Return cached records list if present and younger than ttl, else None."""
    key = (source, model or "", zip_code or "", int(radius or 0))
    with _LOCK:
        c = _conn()
        try:
            row = c.execute(
                "SELECT payload, ts FROM oem_cache "
                "WHERE source=? AND model=? AND zip=? AND radius=?", key
            ).fetchone()
        finally:
            c.close()
    if not row:
        return None
    payload, ts = row
    if time.time() - ts > ttl:
        return None
    try:
        return json.loads(payload)
    except Exception:
        return None


def cache_put(source: str, model: str, zip_code: str, radius: int, records: list) -> None:
    """Store records (a JSON-serializable list) under the key, stamped now."""
    key = (source, model or "", zip_code or "", int(radius or 0))
    with _LOCK:
        c = _conn()
        try:
            c.execute(
                "INSERT OR REPLACE INTO oem_cache "
                "(source, model, zip, radius, payload, ts) VALUES (?,?,?,?,?,?)",
                (*key, json.dumps(records), time.time()),
            )
            c.commit()
        finally:
            c.close()


def cache_age(source: str, model: str, zip_code: str, radius: int):
    """Seconds since the cached row was written, or None if absent (diagnostics)."""
    key = (source, model or "", zip_code or "", int(radius or 0))
    with _LOCK:
        c = _conn()
        try:
            row = c.execute(
                "SELECT ts FROM oem_cache "
                "WHERE source=? AND model=? AND zip=? AND radius=?", key
            ).fetchone()
        finally:
            c.close()
    return (time.time() - row[0]) if row else None
