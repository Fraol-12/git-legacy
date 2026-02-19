"""
tests/test_scorer.py — Unit tests for scorer.py

Tests are deterministic: same input → same output, no API calls.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from core.scorer import score, _classify_tendency


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def make_metrics(**overrides) -> dict:
    """Return a baseline metrics dict with optional overrides."""
    base = {
        "username":           "testuser",
        "account_age_days":   730,
        "account_age_years":  2.0,
        "public_repos":       20,
        "followers":          50,
        "following":          30,
        "has_blog":           True,
        "has_bio":            True,
        "hireable":           False,
        "total_repos":        20,
        "total_stars":        100,
        "total_forks_received": 20,
        "total_watchers":     100,
        "avg_repo_age_days":  400,
        "languages":          ["Python", "JavaScript", "Go"],
        "top_languages":      "Python, JavaScript, Go",
        "has_license_ratio":  0.6,
        "forked_ratio":       0.2,
        "original_repo_count": 16,
        "language_count":     3,
        "total_events":       200,
        "push_events":        80,
        "pr_events":          15,
        "issue_events":       20,
        "fork_events":        10,
        "watch_events":       5,
        "commit_count_90d":   40,
        "active_days_90d":    30,
        "events_last_30d":    50,
        "events_30_90d":      80,
        "most_active_period": "Last 30 days (currently active)",
        "event_type_diversity": 5,
        "collaboration_raw":  100,
        "momentum_ratio":     1.2,
    }
    base.update(overrides)
    return base


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestScoreStructure:
    def test_returns_required_keys(self):
        result = score(make_metrics())
        assert "dimensions" in result
        assert "overall_score" in result
        assert "tendency" in result
        assert "weights" in result

    def test_all_dimensions_present(self):
        result = score(make_metrics())
        dims = result["dimensions"]
        expected = {"consistency", "collaboration", "depth", "breadth", "momentum", "openness"}
        assert set(dims.keys()) == expected

    def test_scores_in_range(self):
        result = score(make_metrics())
        assert 0 <= result["overall_score"] <= 100
        for dim, val in result["dimensions"].items():
            assert 0 <= val <= 100, f"{dim} out of range: {val}"

    def test_weights_sum_to_one(self):
        result = score(make_metrics())
        total = sum(result["weights"].values())
        assert abs(total - 1.0) < 1e-9


class TestTendencyClassification:
    def test_high_score_utopia(self):
        assert _classify_tendency(75) == "Utopia"
        assert _classify_tendency(100) == "Utopia"
        assert _classify_tendency(70) == "Utopia"

    def test_low_score_dystopia(self):
        assert _classify_tendency(30) == "Dystopia"
        assert _classify_tendency(0) == "Dystopia"
        assert _classify_tendency(40) == "Dystopia"

    def test_mid_score_unexpected(self):
        assert _classify_tendency(55) == "Unexpected"
        assert _classify_tendency(41) == "Unexpected"
        assert _classify_tendency(69) == "Unexpected"


class TestEdgeCases:
    def test_empty_profile(self):
        """A completely inactive user should score low but not crash."""
        empty = make_metrics(
            total_repos=0, total_stars=0, total_forks_received=0,
            commit_count_90d=0, active_days_90d=0, events_last_30d=0,
            events_30_90d=0, pr_events=0, issue_events=0, fork_events=0,
            followers=0, language_count=0, has_blog=False, has_bio=False,
            has_license_ratio=0.0, forked_ratio=0.0, momentum_ratio=0.0,
            event_type_diversity=0,
        )
        result = score(empty)
        assert result["overall_score"] == 0.0 or result["overall_score"] < 20
        assert result["tendency"] == "Dystopia"

    def test_superstar_profile(self):
        """A highly active user should score high."""
        superstar = make_metrics(
            total_repos=100, total_stars=5000, total_forks_received=1000,
            commit_count_90d=300, active_days_90d=85, events_last_30d=200,
            events_30_90d=100, pr_events=80, issue_events=100, fork_events=50,
            followers=5000, language_count=12, has_blog=True, has_bio=True,
            has_license_ratio=1.0, forked_ratio=0.3, momentum_ratio=2.5,
            event_type_diversity=8, original_repo_count=70,
            avg_repo_age_days=800,
        )
        result = score(superstar)
        assert result["overall_score"] > 60
        assert result["tendency"] in ("Utopia", "Unexpected")

    def test_deterministic(self):
        """Same input must always produce same output."""
        m = make_metrics()
        r1 = score(m)
        r2 = score(m)
        assert r1["overall_score"] == r2["overall_score"]
        assert r1["tendency"] == r2["tendency"]
