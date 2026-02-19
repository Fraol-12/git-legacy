"""
scorer.py — Deterministic scoring of behavioral metrics across 6 dimensions.

Input:  metrics dict from analyzer.py
Output: score_report dict with per-dimension scores, overall score, and tendency

All math is transparent and explainable — no ML, no black boxes.
"""

import logging

from config import SCORE_WEIGHTS, UTOPIA_THRESHOLD, DYSTOPIA_THRESHOLD
from utils.utils import clamp, log_scale, safe_divide

logger = logging.getLogger(__name__)


def score(metrics: dict) -> dict:
    """
    Compute a score report from behavioral metrics.

    Returns:
        {
            "dimensions": {
                "consistency":   float (0–100),
                "collaboration": float (0–100),
                "depth":         float (0–100),
                "breadth":       float (0–100),
                "momentum":      float (0–100),
                "openness":      float (0–100),
            },
            "overall_score": float (0–100),
            "tendency":      str ("Utopia" | "Dystopia" | "Unexpected"),
            "weights":       dict,   # for UI display
        }
    """
    dimensions = {
        "consistency":   _score_consistency(metrics),
        "collaboration": _score_collaboration(metrics),
        "depth":         _score_depth(metrics),
        "breadth":       _score_breadth(metrics),
        "momentum":      _score_momentum(metrics),
        "openness":      _score_openness(metrics),
    }

    overall_score = sum(
        dimensions[dim] * weight
        for dim, weight in SCORE_WEIGHTS.items()
    )
    overall_score = clamp(overall_score)

    tendency = _classify_tendency(overall_score)

    logger.info(
        f"Score report — overall: {overall_score:.1f}, tendency: {tendency}, "
        f"dimensions: {dimensions}"
    )

    return {
        "dimensions":    dimensions,
        "overall_score": overall_score,
        "tendency":      tendency,
        "weights":       SCORE_WEIGHTS,
    }


# ─── Dimension Scorers ────────────────────────────────────────────────────────

def _score_consistency(m: dict) -> float:
    """
    How regularly does this developer commit?
    Signals: active_days_90d, commit_count_90d, account_age_days
    """
    active_days    = m.get("active_days_90d", 0)
    commit_count   = m.get("commit_count_90d", 0)
    account_age    = m.get("account_age_days", 1)

    # Active days out of 90 (capped at 90)
    active_ratio   = clamp(safe_divide(active_days, 90) * 100)

    # Commit frequency: log-scale, 50 commits/90d ≈ 100
    commit_score   = log_scale(commit_count, scale=50)

    # Longevity bonus: older accounts with activity score higher
    longevity_bonus = clamp(log_scale(account_age / 365, scale=5) * 0.2)

    return clamp(active_ratio * 0.5 + commit_score * 0.4 + longevity_bonus * 0.1)


def _score_collaboration(m: dict) -> float:
    """
    How much does this developer engage with others?
    Signals: pr_events, issue_events, fork_events, followers
    """
    pr_score      = log_scale(m.get("pr_events", 0), scale=20)
    issue_score   = log_scale(m.get("issue_events", 0), scale=30)
    fork_score    = log_scale(m.get("fork_events", 0), scale=10)
    follower_score = log_scale(m.get("followers", 0), scale=100)

    return clamp(
        pr_score      * 0.40 +
        issue_score   * 0.30 +
        fork_score    * 0.15 +
        follower_score * 0.15
    )


def _score_depth(m: dict) -> float:
    """
    How mature and impactful is this developer's work?
    Signals: total_stars, total_forks_received, avg_repo_age_days, original_repo_count
    """
    star_score    = log_scale(m.get("total_stars", 0), scale=200)
    fork_score    = log_scale(m.get("total_forks_received", 0), scale=50)
    age_score     = log_scale(m.get("avg_repo_age_days", 0) / 30, scale=24)  # months
    repo_score    = log_scale(m.get("original_repo_count", 0), scale=30)

    return clamp(
        star_score * 0.35 +
        fork_score * 0.25 +
        age_score  * 0.20 +
        repo_score * 0.20
    )


def _score_breadth(m: dict) -> float:
    """
    How diverse is this developer's technical range?
    Signals: language_count, event_type_diversity, total_repos
    """
    lang_score      = log_scale(m.get("language_count", 0), scale=10)
    diversity_score = log_scale(m.get("event_type_diversity", 0), scale=8)
    repo_breadth    = log_scale(m.get("total_repos", 0), scale=50)

    return clamp(
        lang_score      * 0.50 +
        diversity_score * 0.30 +
        repo_breadth    * 0.20
    )


def _score_momentum(m: dict) -> float:
    """
    Is this developer accelerating or decelerating?
    Signals: momentum_ratio, events_last_30d, events_30_90d
    """
    momentum_ratio  = m.get("momentum_ratio", 0.0)
    recent_activity = log_scale(m.get("events_last_30d", 0), scale=60)

    # momentum_ratio > 1 means accelerating, < 1 means slowing down
    # Map ratio to 0–100: ratio=2 → ~100, ratio=0.5 → ~50, ratio=0 → 0
    ratio_score = clamp(min(momentum_ratio, 3.0) / 3.0 * 100)

    return clamp(ratio_score * 0.60 + recent_activity * 0.40)


def _score_openness(m: dict) -> float:
    """
    How open and transparent is this developer's work?
    Signals: has_license_ratio, forked_ratio (inverse), has_blog, has_bio
    """
    license_score  = m.get("has_license_ratio", 0.0) * 100
    # Forking others' work is a sign of openness (engaging with community)
    fork_openness  = m.get("forked_ratio", 0.0) * 50   # max 50 pts
    profile_score  = (
        (25 if m.get("has_blog") else 0) +
        (25 if m.get("has_bio") else 0)
    )

    return clamp(
        license_score * 0.40 +
        fork_openness * 0.30 +
        profile_score * 0.30
    )


# ─── Tendency Classification ──────────────────────────────────────────────────

def _classify_tendency(overall_score: float) -> str:
    if overall_score >= UTOPIA_THRESHOLD:
        return "Utopia"
    elif overall_score <= DYSTOPIA_THRESHOLD:
        return "Dystopia"
    else:
        return "Unexpected"
