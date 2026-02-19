"""
analyzer.py — Transform raw GitHub API data into structured behavioral metrics.

Input:  raw dict from GitHubClient.fetch_all()
Output: metrics dict consumed by scorer.py

All values are raw counts/ratios — no scoring here.
"""

import logging
from collections import Counter
from datetime import datetime, timezone

from utils.utils import days_since, years_since, safe_divide

logger = logging.getLogger(__name__)


def analyze(raw_data: dict) -> dict:
    """
    Extract behavioral signals from raw GitHub API data.

    Args:
        raw_data: dict with keys 'profile', 'repos', 'events'

    Returns:
        metrics dict with all signals needed by scorer.py
    """
    profile = raw_data.get("profile", {})
    repos   = raw_data.get("repos", [])
    events  = raw_data.get("events", [])

    metrics = {}
    metrics.update(_profile_metrics(profile))
    metrics.update(_repo_metrics(repos))
    metrics.update(_event_metrics(events))
    metrics.update(_derived_metrics(metrics))

    logger.debug(f"Extracted metrics: {metrics}")
    return metrics


# ─── Profile Signals ──────────────────────────────────────────────────────────

def _profile_metrics(profile: dict) -> dict:
    return {
        "username":          profile.get("login", "unknown"),
        "account_age_days":  days_since(profile.get("created_at")),
        "account_age_years": years_since(profile.get("created_at")),
        "public_repos":      profile.get("public_repos", 0),
        "followers":         profile.get("followers", 0),
        "following":         profile.get("following", 0),
        "has_blog":          bool(profile.get("blog")),
        "has_bio":           bool(profile.get("bio")),
        "hireable":          bool(profile.get("hireable")),
    }


# ─── Repository Signals ───────────────────────────────────────────────────────

def _repo_metrics(repos: list[dict]) -> dict:
    if not repos:
        return {
            "total_repos":          0,
            "total_stars":          0,
            "total_forks_received": 0,
            "total_watchers":       0,
            "avg_repo_age_days":    0.0,
            "languages":            [],
            "top_languages":        "N/A",
            "has_license_ratio":    0.0,
            "forked_ratio":         0.0,
            "original_repo_count":  0,
            "language_count":       0,
        }

    total_stars          = sum(r.get("stargazers_count", 0) for r in repos)
    total_forks_received = sum(r.get("forks_count", 0) for r in repos)
    total_watchers       = sum(r.get("watchers_count", 0) for r in repos)

    # Language diversity
    lang_counter = Counter(
        r["language"] for r in repos if r.get("language")
    )
    languages    = [lang for lang, _ in lang_counter.most_common()]
    top_languages = ", ".join(languages[:5]) if languages else "N/A"

    # Repo age
    ages = [days_since(r.get("created_at")) for r in repos if r.get("created_at")]
    avg_repo_age_days = sum(ages) / len(ages) if ages else 0.0

    # License usage
    licensed_count = sum(1 for r in repos if r.get("license"))
    has_license_ratio = safe_divide(licensed_count, len(repos))

    # Forked repos vs original
    forked_repos = [r for r in repos if r.get("fork")]
    forked_ratio = safe_divide(len(forked_repos), len(repos))
    original_repo_count = len(repos) - len(forked_repos)

    return {
        "total_repos":          len(repos),
        "total_stars":          total_stars,
        "total_forks_received": total_forks_received,
        "total_watchers":       total_watchers,
        "avg_repo_age_days":    avg_repo_age_days,
        "languages":            languages,
        "top_languages":        top_languages,
        "has_license_ratio":    has_license_ratio,
        "forked_ratio":         forked_ratio,
        "original_repo_count":  original_repo_count,
        "language_count":       len(lang_counter),
    }


# ─── Event Signals ────────────────────────────────────────────────────────────

def _event_metrics(events: list[dict]) -> dict:
    if not events:
        return {
            "total_events":          0,
            "push_events":           0,
            "pr_events":             0,
            "issue_events":          0,
            "fork_events":           0,
            "watch_events":          0,
            "commit_count_90d":      0,
            "active_days_90d":       0,
            "events_last_30d":       0,
            "events_30_90d":         0,
            "most_active_period":    "N/A",
            "event_type_diversity":  0,
        }

    now = datetime.now(timezone.utc)

    # Categorize events
    push_events  = [e for e in events if e.get("type") == "PushEvent"]
    pr_events    = [e for e in events if e.get("type") in (
                        "PullRequestEvent", "PullRequestReviewEvent")]
    issue_events = [e for e in events if e.get("type") in (
                        "IssuesEvent", "IssueCommentEvent")]
    fork_events  = [e for e in events if e.get("type") == "ForkEvent"]
    watch_events = [e for e in events if e.get("type") == "WatchEvent"]

    # Commit count from push events (last 90 days)
    commit_count_90d = 0
    active_days_set  = set()
    events_last_30d  = 0
    events_30_90d    = 0

    for event in events:
        created_at = event.get("created_at", "")
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue

        age_days = (now - dt).total_seconds() / 86400

        if age_days <= 90:
            if event.get("type") == "PushEvent":
                commits = event.get("payload", {}).get("commits", [])
                commit_count_90d += len(commits)
                active_days_set.add(dt.date())

        if age_days <= 30:
            events_last_30d += 1
        elif age_days <= 90:
            events_30_90d += 1

    # Most active period heuristic
    if events_last_30d > events_30_90d:
        most_active_period = "Last 30 days (currently active)"
    elif events_30_90d > 0:
        most_active_period = "30–90 days ago"
    else:
        most_active_period = "More than 90 days ago"

    event_types = set(e.get("type") for e in events if e.get("type"))

    return {
        "total_events":         len(events),
        "push_events":          len(push_events),
        "pr_events":            len(pr_events),
        "issue_events":         len(issue_events),
        "fork_events":          len(fork_events),
        "watch_events":         len(watch_events),
        "commit_count_90d":     commit_count_90d,
        "active_days_90d":      len(active_days_set),
        "events_last_30d":      events_last_30d,
        "events_30_90d":        events_30_90d,
        "most_active_period":   most_active_period,
        "event_type_diversity": len(event_types),
    }


# ─── Derived Signals ──────────────────────────────────────────────────────────

def _derived_metrics(m: dict) -> dict:
    """Compute cross-signal derived metrics."""
    # Collaboration signal: PRs + issues + forks of others
    collaboration_raw = (
        m.get("pr_events", 0) * 3 +      # PRs weighted higher
        m.get("issue_events", 0) * 2 +
        m.get("fork_events", 0)
    )

    # Momentum: recent vs historical event rate
    recent_rate   = m.get("events_last_30d", 0)
    historic_rate = safe_divide(m.get("events_30_90d", 0), 2)  # per 30d equivalent
    momentum_ratio = safe_divide(recent_rate, max(historic_rate, 1))

    return {
        "collaboration_raw": collaboration_raw,
        "momentum_ratio":    momentum_ratio,
    }
