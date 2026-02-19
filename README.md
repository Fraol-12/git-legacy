# 🦋 Git-Legacy: The Butterfly Effect

> Your GitHub habits. Three possible 2040 futures.

Git-Legacy is an AI-powered behavioral modeling engine that analyzes a developer's public GitHub activity, scores their behavioral patterns across six dimensions, and uses OpenAI to generate three vivid 2040 futures: **Utopia**, **Dystopia**, and **Unexpected**.

Every commit is a butterfly effect. Where will yours lead by 2040?

---

## ✨ Features

- **GitHub Behavioral Analysis** — Fetches profile, repositories, and events via the GitHub REST API
- **Six-Dimension Scoring** — Deterministic scoring across Consistency, Collaboration, Depth, Breadth, Momentum, and Openness (0–100 each)
- **AI-Generated Futures** — Three vivid 2040 narratives powered by GPT-4o-mini
- **Beautiful Dark UI** — Custom-styled Streamlit interface with glassmorphism cards and gradient accents
- **Smart Caching** — Two-layer cache (in-memory + disk) to minimize API calls
- **Graceful Fallbacks** — Works without an OpenAI key (shows illustrative fallback narratives)
- **Rate Limit Awareness** — Monitors GitHub API limits and warns before exhaustion

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | [Streamlit](https://streamlit.io/) + Custom CSS |
| GitHub API | [requests](https://docs.python-requests.org/) + REST v3 |
| AI Narratives | [OpenAI](https://platform.openai.com/) (GPT-4o-mini) |
| Caching | `st.cache_data` (in-memory) + `joblib` (disk) |
| Language | Python 3.10+ |

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/git-legacy.git
cd git-legacy
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### 5. Run the app

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## 🔑 Configuration

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Optional | Enables AI-generated narratives. Without it, fallback stories are shown. |
| `GITHUB_TOKEN` | Optional | A GitHub PAT raises rate limits from 60 to 5,000 req/hr. |

You can set these in:
- `.env` file (for local development)
- `.streamlit/secrets.toml` (for Streamlit Cloud deployment)

---

## 🏗️ Architecture

```
git-legacy/
├── app.py                  # Streamlit entry point
├── config.py               # Constants, weights, prompt templates
├── requirements.txt        # Dependencies
├── .env.example            # Template for local secrets
│
├── core/
│   ├── github_client.py    # GitHub REST API calls + error handling
│   ├── analyzer.py         # Raw API data → behavioral metrics
│   ├── scorer.py           # Metrics → 6-dimension scores (0–100)
│   ├── narrative_engine.py # Scores → AI-generated 2040 futures
│   └── cache.py            # Two-layer caching (memory + disk)
│
├── ui/
│   ├── components.py       # Reusable Streamlit UI components
│   └── styles.css          # Custom dark theme CSS
│
├── utils/
│   └── utils.py            # Helpers: retry decorator, date math, validators
│
└── tests/
    ├── test_analyzer.py    # Unit tests for data analysis
    ├── test_scorer.py      # Unit tests for scoring engine
    └── fixtures/           # Mock API response data
```

### Data Flow

```
User enters GitHub username
        │
        ▼
github_client.py ──── GitHub REST API ────▶ raw JSON
        │
        ▼
analyzer.py ──── Extract behavioral signals ────▶ metrics dict
        │
        ▼
scorer.py ──── Score 6 dimensions ────▶ score_report dict
        │
        ▼
narrative_engine.py ──── OpenAI GPT ────▶ 3 future narratives
        │
        ▼
app.py ──── Render score breakdown + narrative cards
```

---

## 📊 Scoring Model

Six behavioral dimensions, each scored 0–100:

| Dimension | What It Measures | Weight |
|---|---|---|
| **Consistency** | Commit regularity, active days, streaks | 20% |
| **Collaboration** | PRs, issues, forks, community engagement | 20% |
| **Depth** | Stars received, repo maturity, project impact | 20% |
| **Breadth** | Language diversity, event variety, repo count | 15% |
| **Momentum** | Recent activity vs. historical average | 15% |
| **Openness** | License usage, profile completeness | 10% |

**Tendency Classification:**
- Score ≥ 70 → **Utopia**-leaning
- Score ≤ 40 → **Dystopia**-leaning
- 40 < Score < 70 → **Unexpected**-leaning

All scoring is deterministic and explainable — no ML, no black boxes.

---

## 🧪 Running Tests

```bash
python -m pytest tests/ -v
```

---

## 🌐 Deployment

### Streamlit Community Cloud (Recommended)

1. Push your repo to GitHub
2. Connect at [share.streamlit.io](https://share.streamlit.io)
3. Set `OPENAI_API_KEY` in the Streamlit Secrets UI
4. Set entry point to `app.py`
5. Deploy — live URL in ~2 minutes

---

## 📝 License

This project is open source. See individual file headers for details.

---

## 🙏 Acknowledgments

- [GitHub REST API](https://docs.github.com/en/rest) for public developer data
- [OpenAI](https://openai.com/) for narrative generation
- [Streamlit](https://streamlit.io/) for the beautiful web framework

---

*Built with ❤️ for the hackathon. Every commit is a butterfly effect.*
