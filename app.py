"""
app.py — Git-Legacy: The Butterfly Effect
Streamlit entry point.

Flow:
  1. Load CSS + render hero
  2. User inputs GitHub username (+ optional PAT)
  3. Fetch GitHub data (with disk cache)
  4. Analyze → Score → Generate narratives
  5. Display score overview + 3 future cards
"""

import os
import logging
import datetime

import streamlit as st
from dotenv import load_dotenv

# ─── Load secrets ─────────────────────────────────────────────────────────────
load_dotenv()  # local .env
try:
    OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
except Exception:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ─── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="Git-Legacy: The Butterfly Effect",
    page_icon="🦋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Imports (after set_page_config) ─────────────────────────────────────────
from config import APP_TITLE
from core.github_client import (
    GitHubClient,
    GitHubUserNotFoundError,
    GitHubRateLimitError,
    GitHubAuthError,
    GitHubAPIError,
)
from core.analyzer import analyze
from core.scorer import score
from core.narrative_engine import NarrativeEngine
from core.cache import get_cached_result, set_cached_result
from ui.components import (
    render_hero,
    render_score_overview,
    render_futures,
    render_rate_limit_warning,
    render_metrics_summary,
)
from utils.utils import validate_github_username

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─── Load CSS ─────────────────────────────────────────────────────────────────
def _load_css():
    css_path = os.path.join(os.path.dirname(__file__), "ui", "styles.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


_load_css()


# ─── Cached GitHub fetch (st.cache_data = in-memory, 1hr TTL) ────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_github_data(username: str, token: str | None) -> dict:
    client = GitHubClient(token=token or None)
    return client.fetch_all(username)


# ─── Main pipeline ────────────────────────────────────────────────────────────
def run_analysis(username: str, github_token: str | None) -> dict | None:
    """
    Full pipeline: fetch → analyze → score → narrative.
    Returns a result dict or None on error.
    """
    # 1. Check disk cache
    cached = get_cached_result(username)
    if cached:
        st.info("⚡ Loaded from cache (< 24h old). Results may not reflect very recent activity.")
        return cached

    # 2. Fetch GitHub data
    with st.spinner("🔍 Fetching GitHub data..."):
        try:
            raw_data = _fetch_github_data(username, github_token)
        except GitHubUserNotFoundError:
            st.error(f"❌ GitHub user **{username}** not found. Check the username and try again.")
            return None
        except GitHubRateLimitError as exc:
            reset_str = ""
            if exc.reset_timestamp:
                reset_dt = datetime.datetime.fromtimestamp(exc.reset_timestamp)
                reset_str = f" Rate limit resets at **{reset_dt.strftime('%H:%M:%S')}**."
            st.error(
                f"⏱️ GitHub API rate limit exceeded.{reset_str} "
                "Add a GitHub Personal Access Token (PAT) to increase your limit to 5,000 req/hr."
            )
            return None
        except GitHubAuthError:
            st.error("🔑 Invalid GitHub token. Please check your PAT and try again.")
            return None
        except GitHubAPIError as exc:
            st.error(f"⚠️ GitHub API error: {exc}")
            return None
        except Exception as exc:
            st.error(f"⚠️ Unexpected error fetching GitHub data: {exc}")
            logger.exception("Unexpected fetch error")
            return None

    # 3. Analyze
    with st.spinner("🧠 Analyzing behavioral patterns..."):
        metrics = analyze(raw_data)

    # 4. Score
    score_report = score(metrics)

    # 5. Generate narratives
    if not OPENAI_API_KEY:
        st.warning(
            "⚠️ No OpenAI API key configured. Showing illustrative fallback narratives. "
            "Set `OPENAI_API_KEY` in `.env` or Streamlit secrets for AI-generated stories."
        )
        from core.narrative_engine import _FALLBACK_FUTURES
        futures, is_fallback = _FALLBACK_FUTURES, True
    else:
        with st.spinner("✨ Generating your 2040 futures..."):
            engine = NarrativeEngine(api_key=OPENAI_API_KEY)
            futures, is_fallback = engine.generate(score_report, metrics)

    result = {
        "metrics":      metrics,
        "score_report": score_report,
        "futures":      futures,
        "is_fallback":  is_fallback,
        "rate_limit":   raw_data.get("rate_limit", {}),
    }

    # 6. Write to disk cache
    set_cached_result(username, result)

    return result


# ─── UI Layout ────────────────────────────────────────────────────────────────
render_hero()

st.markdown("---")

# Input form
with st.form("analysis_form", clear_on_submit=False):
    col_input, col_pat, col_btn = st.columns([3, 3, 1])

    with col_input:
        username_input = st.text_input(
            "GitHub Username",
            placeholder="e.g. torvalds",
            help="Enter any public GitHub username.",
        )

    with col_pat:
        pat_input = st.text_input(
            "GitHub PAT (optional but recommended)",
            type="password",
            placeholder="ghp_...",
            help=(
                "A Personal Access Token raises your rate limit from 60 to 5,000 req/hr. "
                "Generate one at github.com/settings/tokens (no scopes needed for public data)."
            ),
        )

    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)  # vertical align
        submitted = st.form_submit_button("Analyze 🦋", use_container_width=True)

# ─── Run on submit ────────────────────────────────────────────────────────────
if submitted:
    username = username_input.strip()
    is_valid, err_msg = validate_github_username(username)

    if not is_valid:
        st.error(f"❌ {err_msg}")
    else:
        result = run_analysis(username, pat_input.strip() or None)

        if result:
            metrics      = result["metrics"]
            score_report = result["score_report"]
            futures      = result["futures"]
            is_fallback  = result["is_fallback"]
            rate_limit   = result["rate_limit"]

            # Rate limit warning
            render_rate_limit_warning(rate_limit)

            st.markdown(f"## 📊 Legacy Analysis: `{username}`")

            # Score overview + dimension bars
            left_col, right_col = st.columns([1, 2])
            with left_col:
                render_score_overview(score_report)
            with right_col:
                render_metrics_summary(metrics)
                st.markdown(
                    f"**Top Languages:** {metrics.get('top_languages', 'N/A')}  \n"
                    f"**Most Active Period:** {metrics.get('most_active_period', 'N/A')}  \n"
                    f"**Account Age:** {metrics.get('account_age_years', 0):.1f} years"
                )

            st.markdown("---")
            st.markdown("## 🔮 Your 2040 Futures")
            render_futures(futures, is_fallback=is_fallback)

            st.markdown("---")
            st.caption(
                "Git-Legacy uses public GitHub data and deterministic behavioral scoring. "
                "Narratives are AI-generated for entertainment and reflection. "
                "Results cached for 24 hours."
            )

# ─── Empty state ──────────────────────────────────────────────────────────────
else:
    st.markdown(
        """
        <div style="text-align:center; padding: 3rem 1rem; color: #8888aa;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🦋</div>
            <div style="font-size: 1.1rem;">
                Enter a GitHub username above to discover your possible futures.
            </div>
            <div style="font-size: 0.85rem; margin-top: 0.5rem;">
                Every commit is a butterfly effect. Where will yours lead by 2040?
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
