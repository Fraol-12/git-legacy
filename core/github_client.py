"""
github_client.py — All GitHub REST API interactions.

Responsibilities:
  - Authenticate requests (PAT or unauthenticated)
  - Fetch user profile, repositories, and events
  - Handle pagination for events (up to 3 pages)
  - Expose rate-limit status to callers
  - Raise typed exceptions for clean error handling upstream
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from config import (
    GITHUB_API_BASE,
    GITHUB_EVENTS_PAGES,
    GITHUB_REPOS_PER_PAGE,
    GITHUB_REQUEST_TIMEOUT,
)
from utils.utils import retry

logger = logging.getLogger(__name__)


# ─── Custom Exceptions ────────────────────────────────────────────────────────

class GitHubUserNotFoundError(Exception):
    """Raised when the GitHub username does not exist (404)."""


class GitHubRateLimitError(Exception):
    """Raised when the GitHub API rate limit is exceeded (403/429)."""
    def __init__(self, reset_timestamp: int | None = None):
        self.reset_timestamp = reset_timestamp
        super().__init__("GitHub API rate limit exceeded.")


class GitHubAuthError(Exception):
    """Raised when the provided token is invalid (401)."""


class GitHubAPIError(Exception):
    """Generic GitHub API error for unexpected status codes."""


# ─── Client ──────────────────────────────────────────────────────────────────

class GitHubClient:
    """
    Thin wrapper around the GitHub REST API v3.

    Usage:
        client = GitHubClient(token="ghp_...")
        data = client.fetch_all("octocat")
    """

    def __init__(self, token: str | None = None):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    # ── Internal request helper ───────────────────────────────────────────────

    @retry(max_attempts=2, delay=1.5, exceptions=(requests.Timeout, requests.ConnectionError))
    def _get(self, path: str, params: dict | None = None) -> requests.Response:
        """
        Make a GET request to the GitHub API.
        Raises typed exceptions for known error codes.
        """
        url = f"{GITHUB_API_BASE}{path}"
        response = self.session.get(url, params=params, timeout=GITHUB_REQUEST_TIMEOUT)

        if response.status_code == 200:
            return response
        elif response.status_code == 404:
            raise GitHubUserNotFoundError(f"User not found: {path}")
        elif response.status_code == 401:
            raise GitHubAuthError("Invalid or expired GitHub token.")
        elif response.status_code in (403, 429):
            reset_ts = response.headers.get("X-RateLimit-Reset")
            raise GitHubRateLimitError(
                reset_timestamp=int(reset_ts) if reset_ts else None
            )
        else:
            raise GitHubAPIError(
                f"GitHub API returned {response.status_code} for {url}"
            )

    def _get_json(self, path: str, params: dict | None = None) -> dict | list:
        return self._get(path, params).json()

    # ── Rate-limit info ───────────────────────────────────────────────────────

    def get_rate_limit_status(self) -> dict:
        """
        Return current rate-limit info.
        Returns dict with keys: limit, remaining, reset_timestamp.
        """
        try:
            data = self._get_json("/rate_limit")
            core = data.get("resources", {}).get("core", {})
            return {
                "limit": core.get("limit", 0),
                "remaining": core.get("remaining", 0),
                "reset_timestamp": core.get("reset", 0),
            }
        except Exception:
            return {"limit": 0, "remaining": 0, "reset_timestamp": 0}

    # ── Public fetch methods ──────────────────────────────────────────────────

    def fetch_profile(self, username: str) -> dict:
        """Fetch the public user profile."""
        logger.info(f"Fetching profile for: {username}")
        return self._get_json(f"/users/{username}")

    def fetch_repos(self, username: str) -> list[dict]:
        """Fetch up to GITHUB_REPOS_PER_PAGE public repositories, sorted by last updated."""
        logger.info(f"Fetching repos for: {username}")
        return self._get_json(
            f"/users/{username}/repos",
            params={
                "per_page": GITHUB_REPOS_PER_PAGE,
                "sort": "updated",
                "type": "owner",
            },
        )

    def fetch_events(self, username: str) -> list[dict]:
        """
        Fetch up to GITHUB_EVENTS_PAGES × 100 public events.
        Pages are fetched sequentially (GitHub events API doesn't support parallel paging).
        """
        logger.info(f"Fetching events for: {username} ({GITHUB_EVENTS_PAGES} pages)")
        all_events: list[dict] = []
        for page in range(1, GITHUB_EVENTS_PAGES + 1):
            try:
                page_events = self._get_json(
                    f"/users/{username}/events/public",
                    params={"per_page": 100, "page": page},
                )
                if not page_events:
                    break  # No more events
                all_events.extend(page_events)
            except GitHubAPIError as exc:
                logger.warning(f"Events page {page} failed: {exc}. Stopping pagination.")
                break
        return all_events

    # ── Aggregate fetch (repos + events in parallel) ──────────────────────────

    def fetch_all(self, username: str) -> dict:
        """
        Fetch profile, repos, and events for a username.
        Repos and events are fetched concurrently for speed.

        Returns:
            {
                "profile": {...},
                "repos":   [...],
                "events":  [...],
                "rate_limit": {...},
            }

        Raises:
            GitHubUserNotFoundError, GitHubRateLimitError, GitHubAuthError,
            GitHubAPIError, requests.Timeout
        """
        # Profile must come first to validate the user exists
        profile = self.fetch_profile(username)

        # Fetch repos and events concurrently
        results = {}
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_repos   = executor.submit(self.fetch_repos, username)
            future_events  = executor.submit(self.fetch_events, username)

            for future in as_completed([future_repos, future_events]):
                if future is future_repos:
                    results["repos"] = future.result()
                else:
                    results["events"] = future.result()

        rate_limit = self.get_rate_limit_status()

        logger.info(
            f"Fetched {len(results['repos'])} repos, "
            f"{len(results['events'])} events for {username}. "
            f"Rate limit remaining: {rate_limit['remaining']}"
        )

        return {
            "profile":    profile,
            "repos":      results.get("repos", []),
            "events":     results.get("events", []),
            "rate_limit": rate_limit,
        }
