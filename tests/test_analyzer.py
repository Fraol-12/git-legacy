"""
tests/test_analyzer.py — Unit tests for analyzer.py

Tests use mock GitHub API data (no network calls).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from core.analyzer import analyze


# ─── Mock data ────────────────────────────────────────────────────────────────

MOCK_PROFILE = {
    "login":        "testuser",
    "created_at":   "2020-01-01T00:00:00Z",
    "public_repos": 15,
    "followers":    42,
    "following":    20,
    "blog":         "https://testuser.dev",
    "bio":          "I write code.",
    "hireable":     True,
}

MOCK_REPOS = [
    {
        "name": f"repo-{i}",
        "language": ["Python", "JavaScript", "Go", "Rust"][i % 4],
        "stargazers_count": i * 5,
        "forks_count": i * 2,
        "watchers_count": i * 3,
        "created_at": "2021-06-01T00:00:00Z",
        "fork": i % 5 == 0,
        "license": {"key": "mit"} if i % 2 == 0 else None,
    }
    for i in range(10)
]

MOCK_EVENTS = [
    {
        "type": "PushEvent",
        "created_at": "2026-02-10T12:00:00Z",
        "payload": {"commits": [{"sha": "abc"}, {"sha": "def"}]},
    },
    {
        "type": "PullRequestEvent",
        "created_at": "2026-02-08T12:00:00Z",
        "payload": {},
    },
    {
        "type": "IssuesEvent",
        "created_at": "2026-01-20T12:00:00Z",
        "payload": {},
    },
    {
        "type": "ForkEvent",
        "created_at": "2026-01-15T12:00:00Z",
        "payload": {},
    },
]

MOCK_RAW = {
    "profile": MOCK_PROFILE,
    "repos":   MOCK_REPOS,
    "events":  MOCK_EVENTS,
}


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestAnalyzerStructure:
    def test_returns_dict(self):
        result = analyze(MOCK_RAW)
        assert isinstance(result, dict)

    def test_profile_fields_present(self):
        result = analyze(MOCK_RAW)
        assert result["username"] == "testuser"
        assert result["account_age_days"] > 0
        assert result["account_age_years"] > 0
        assert result["followers"] == 42
        assert result["has_blog"] is True
        assert result["has_bio"] is True

    def test_repo_fields_present(self):
        result = analyze(MOCK_RAW)
        assert result["total_repos"] == 10
        assert result["language_count"] == 4
        assert result["total_stars"] > 0
        assert "Python" in result["languages"]

    def test_event_fields_present(self):
        result = analyze(MOCK_RAW)
        assert result["total_events"] == 4
        assert result["push_events"] == 1
        assert result["pr_events"] == 1
        assert result["issue_events"] == 1
        assert result["fork_events"] == 1

    def test_derived_fields_present(self):
        result = analyze(MOCK_RAW)
        assert "collaboration_raw" in result
        assert "momentum_ratio" in result


class TestAnalyzerEdgeCases:
    def test_empty_repos(self):
        raw = {**MOCK_RAW, "repos": []}
        result = analyze(raw)
        assert result["total_repos"] == 0
        assert result["total_stars"] == 0
        assert result["language_count"] == 0

    def test_empty_events(self):
        raw = {**MOCK_RAW, "events": []}
        result = analyze(raw)
        assert result["total_events"] == 0
        assert result["commit_count_90d"] == 0

    def test_empty_profile(self):
        raw = {"profile": {}, "repos": [], "events": []}
        result = analyze(raw)
        assert result["username"] == "unknown"
        assert result["account_age_days"] == 0.0

    def test_no_crash_on_malformed_events(self):
        """Events with missing fields should not crash the analyzer."""
        bad_events = [
            {"type": "PushEvent"},                     # no created_at
            {"created_at": "2026-02-01T00:00:00Z"},   # no type
            {},                                         # completely empty
        ]
        raw = {**MOCK_RAW, "events": bad_events}
        result = analyze(raw)
        assert isinstance(result, dict)
