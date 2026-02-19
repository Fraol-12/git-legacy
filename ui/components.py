"""
ui/components.py — Reusable Streamlit UI components for Git-Legacy.
"""

import streamlit as st


def render_hero():
    """Render the hero header with title and subtitle."""
    st.markdown(
        """
        <div class="hero-header">
            <div class="hero-title">🦋 Git-Legacy</div>
            <div class="hero-subtitle">
                Your GitHub habits. Three possible 2040 futures.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_score_overview(score_report: dict):
    """Render the overall score card and dimension bars."""
    overall  = score_report["overall_score"]
    tendency = score_report["tendency"]
    dims     = score_report["dimensions"]

    tendency_class = f"tendency-{tendency.lower()}"
    tendency_emoji = {"Utopia": "✨", "Dystopia": "⚠️", "Unexpected": "🌀"}.get(tendency, "")

    st.markdown(
        f"""
        <div class="score-card">
            <div class="score-number">{overall:.0f}</div>
            <div class="score-label">Legacy Score / 100</div>
            <div class="tendency-badge {tendency_class}">
                {tendency_emoji} {tendency}-Leaning
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Behavioral Dimensions")
    for dim, value in dims.items():
        bar_width = f"{value:.1f}%"
        st.markdown(
            f"""
            <div class="dim-row">
                <div class="dim-label">{dim.capitalize()}</div>
                <div class="dim-bar-bg">
                    <div class="dim-bar-fill" style="width: {bar_width};"></div>
                </div>
                <div class="dim-value">{value:.0f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_future_card(future_type: str, future: dict):
    """Render a single future card (utopia / dystopia / unexpected)."""
    config = {
        "utopia":     {"icon": "🌿", "label": "Utopia 2040",     "css": "utopia"},
        "dystopia":   {"icon": "🔥", "label": "Dystopia 2040",   "css": "dystopia"},
        "unexpected": {"icon": "🌀", "label": "Unexpected 2040", "css": "unexpected"},
    }
    cfg = config.get(future_type, {"icon": "❓", "label": future_type, "css": "unexpected"})

    title     = future.get("title", "Untitled")
    narrative = future.get("narrative", "")

    st.markdown(
        f"""
        <div class="future-card future-card-{cfg['css']}">
            <div class="future-icon">{cfg['icon']}</div>
            <div class="future-type future-type-{cfg['css']}">{cfg['label']}</div>
            <div class="future-title">{title}</div>
            <div class="future-narrative">{narrative}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_futures(futures: dict, is_fallback: bool = False):
    """Render all three future cards side by side."""
    if is_fallback:
        st.markdown(
            """
            <div class="fallback-notice">
                ⚠️ OpenAI narrative generation unavailable — showing illustrative fallback stories.
            </div>
            """,
            unsafe_allow_html=True,
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        render_future_card("utopia",     futures.get("utopia", {}))
    with col2:
        render_future_card("dystopia",   futures.get("dystopia", {}))
    with col3:
        render_future_card("unexpected", futures.get("unexpected", {}))


def render_rate_limit_warning(rate_limit: dict):
    """Show a warning if GitHub rate limit is low."""
    remaining = rate_limit.get("remaining", 999)
    if remaining < 10:
        import datetime
        reset_ts = rate_limit.get("reset_timestamp", 0)
        reset_dt = datetime.datetime.fromtimestamp(reset_ts).strftime("%H:%M:%S") if reset_ts else "soon"
        st.markdown(
            f"""
            <div class="rate-limit-warning">
                ⚠️ GitHub rate limit nearly exhausted ({remaining} requests remaining).
                Resets at {reset_dt}. Add a GitHub PAT to avoid interruptions.
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_metrics_summary(metrics: dict):
    """Render a quick stats row below the score card."""
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Public Repos",    metrics.get("total_repos", 0))
    col2.metric("Total Stars ⭐",  metrics.get("total_stars", 0))
    col3.metric("Languages",       metrics.get("language_count", 0))
    col4.metric("Commits (90d)",   metrics.get("commit_count_90d", 0))
