"""
config.py — Central configuration: constants, scoring weights, prompt templates.
"""

# ─── GitHub API ───────────────────────────────────────────────────────────────
GITHUB_API_BASE = "https://api.github.com"
GITHUB_EVENTS_PAGES = 3        # 3 × 100 = 300 events max
GITHUB_REPOS_PER_PAGE = 100
GITHUB_REQUEST_TIMEOUT = 10    # seconds

# ─── Scoring Weights (must sum to 1.0) ───────────────────────────────────────
SCORE_WEIGHTS = {
    "consistency":   0.20,
    "collaboration": 0.20,
    "depth":         0.20,
    "breadth":       0.15,
    "momentum":      0.15,
    "openness":      0.10,
}

# ─── Tendency Thresholds ─────────────────────────────────────────────────────
UTOPIA_THRESHOLD   = 70   # overall_score >= this → Utopia-leaning
DYSTOPIA_THRESHOLD = 40   # overall_score <= this → Dystopia-leaning
# Between 40–70 → Unexpected-leaning

# ─── Cache ───────────────────────────────────────────────────────────────────
CACHE_TTL_SECONDS  = 3600   # 1 hour for in-memory (st.cache_data)
DISK_CACHE_DIR     = ".cache/git_legacy"

# ─── OpenAI ──────────────────────────────────────────────────────────────────
OPENAI_MODEL       = "gpt-4o-mini"
OPENAI_MAX_TOKENS  = 1200
OPENAI_TEMPERATURE = 0.85   # Slightly creative but not chaotic

# ─── Prompt Template ─────────────────────────────────────────────────────────
NARRATIVE_PROMPT_TEMPLATE = """
You are a futurist storyteller writing in 2040.
A developer's GitHub behavioral profile has been analyzed and scored.

Developer: {username}
Account age: {account_age_years:.1f} years
Overall legacy score: {overall_score:.0f}/100
Tendency: {tendency}

Behavioral Dimensions (0–100):
- Consistency (commit regularity):    {consistency:.0f}
- Collaboration (PRs, forks, issues): {collaboration:.0f}
- Depth (stars, repo maturity):       {depth:.0f}
- Breadth (language diversity):       {breadth:.0f}
- Momentum (recent vs historical):    {momentum:.0f}
- Openness (public work, licenses):   {openness:.0f}

Top languages: {top_languages}
Most active period: {most_active_period}

Generate exactly three 2040 futures for this developer.
Each future must be 150–180 words, vivid, specific, and grounded in the scores above.
The Utopia should feel earned. The Dystopia should feel like a cautionary tale.
The Unexpected should be genuinely surprising but logically connected to the data.

Respond ONLY with valid JSON in this exact structure:
{{
  "utopia": {{
    "title": "A short evocative title (max 8 words)",
    "narrative": "150–180 word story set in 2040..."
  }},
  "dystopia": {{
    "title": "A short evocative title (max 8 words)",
    "narrative": "150–180 word story set in 2040..."
  }},
  "unexpected": {{
    "title": "A short evocative title (max 8 words)",
    "narrative": "150–180 word story set in 2040..."
  }}
}}
""".strip()

# ─── Username Validation ──────────────────────────────────────────────────────
GITHUB_USERNAME_REGEX = r"^[a-zA-Z0-9\-]{1,39}$"

# ─── UI ──────────────────────────────────────────────────────────────────────
APP_TITLE       = "Git-Legacy: The Butterfly Effect"
APP_SUBTITLE    = "Your GitHub habits. Three possible 2040 futures."
APP_ICON        = "🦋"
