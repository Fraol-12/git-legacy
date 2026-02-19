"""
utils.py — Shared helpers: retry decorator, date math, input validators.
"""

import re
import time
import logging
from datetime import datetime, timezone
from functools import wraps

from config import GITHUB_USERNAME_REGEX

logger = logging.getLogger(__name__)


# ─── Retry Decorator ─────────────────────────────────────────────────────────

def retry(max_attempts: int = 2, delay: float = 1.5, exceptions=(Exception,)):
    """
    Decorator: retry a function up to `max_attempts` times on specified exceptions.
    Uses exponential backoff: delay, delay*2, delay*4, ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        sleep_time = delay * (2 ** (attempt - 1))
                        logger.warning(
                            f"[retry] {func.__name__} attempt {attempt} failed: {exc}. "
                            f"Retrying in {sleep_time:.1f}s..."
                        )
                        time.sleep(sleep_time)
                    else:
                        logger.error(
                            f"[retry] {func.__name__} failed after {max_attempts} attempts."
                        )
            raise last_exc
        return wrapper
    return decorator


# ─── Date Helpers ─────────────────────────────────────────────────────────────

def parse_github_date(date_str: str | None) -> datetime | None:
    """Parse a GitHub ISO-8601 date string to a timezone-aware datetime."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def days_since(date_str: str | None) -> float:
    """Return the number of days between now and a GitHub date string."""
    dt = parse_github_date(date_str)
    if dt is None:
        return 0.0
    now = datetime.now(timezone.utc)
    return max((now - dt).total_seconds() / 86400, 0.0)


def years_since(date_str: str | None) -> float:
    """Return fractional years since a GitHub date string."""
    return days_since(date_str) / 365.25


# ─── Input Validation ────────────────────────────────────────────────────────

def validate_github_username(username: str) -> tuple[bool, str]:
    """
    Validate a GitHub username.
    Returns (is_valid: bool, error_message: str).
    """
    username = username.strip()
    if not username:
        return False, "Username cannot be empty."
    if not re.match(GITHUB_USERNAME_REGEX, username):
        return False, (
            "Invalid GitHub username. Must be 1–39 characters, "
            "letters, numbers, or hyphens only."
        )
    if username.startswith("-") or username.endswith("-"):
        return False, "GitHub username cannot start or end with a hyphen."
    return True, ""


# ─── Misc ────────────────────────────────────────────────────────────────────

def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp a value to [lo, hi]."""
    return max(lo, min(hi, value))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide safely, returning `default` when denominator is zero."""
    if denominator == 0:
        return default
    return numerator / denominator


def log_scale(value: float, scale: float = 10.0) -> float:
    """
    Map a raw count to a 0–100 score using logarithmic scaling.
    `scale` is the count that maps to ~100.
    """
    import math
    if value <= 0:
        return 0.0
    return clamp(math.log1p(value) / math.log1p(scale) * 100)
