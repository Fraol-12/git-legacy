"""
cache.py — Caching utilities for GitHub API responses and analysis results.

Two layers:
  1. In-memory: st.cache_data (per Streamlit session, TTL=1hr)
  2. Disk:      joblib.Memory (persists across restarts, TTL=24hr)

Usage:
    from core.cache import cached_fetch_all, cached_analyze_and_score
"""

import hashlib
import logging
import os
import time

import joblib

from config import CACHE_TTL_SECONDS, DISK_CACHE_DIR

logger = logging.getLogger(__name__)

# ─── Disk cache setup ─────────────────────────────────────────────────────────
os.makedirs(DISK_CACHE_DIR, exist_ok=True)
_memory = joblib.Memory(DISK_CACHE_DIR, verbose=0)

DISK_CACHE_TTL = 86400  # 24 hours in seconds


def _disk_cache_key(username: str) -> str:
    return hashlib.md5(username.lower().encode()).hexdigest()


def get_cached_result(username: str) -> dict | None:
    """
    Check disk cache for a full analysis result.
    Returns the cached dict if fresh, else None.
    """
    key = _disk_cache_key(username)
    cache_file = os.path.join(DISK_CACHE_DIR, f"{key}.joblib")
    if not os.path.exists(cache_file):
        return None
    try:
        cached = joblib.load(cache_file)
        age = time.time() - cached.get("_cached_at", 0)
        if age < DISK_CACHE_TTL:
            logger.info(f"Disk cache hit for {username} (age: {age:.0f}s)")
            return cached.get("data")
        else:
            logger.info(f"Disk cache expired for {username}")
            os.remove(cache_file)
            return None
    except Exception as exc:
        logger.warning(f"Disk cache read error for {username}: {exc}")
        return None


def set_cached_result(username: str, data: dict) -> None:
    """Write a full analysis result to disk cache."""
    key = _disk_cache_key(username)
    cache_file = os.path.join(DISK_CACHE_DIR, f"{key}.joblib")
    try:
        joblib.dump({"data": data, "_cached_at": time.time()}, cache_file)
        logger.info(f"Disk cache written for {username}")
    except Exception as exc:
        logger.warning(f"Disk cache write error for {username}: {exc}")


def clear_cache(username: str) -> bool:
    """Remove disk cache entry for a username. Returns True if removed."""
    key = _disk_cache_key(username)
    cache_file = os.path.join(DISK_CACHE_DIR, f"{key}.joblib")
    if os.path.exists(cache_file):
        os.remove(cache_file)
        logger.info(f"Disk cache cleared for {username}")
        return True
    return False
