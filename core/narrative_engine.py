"""
narrative_engine.py — Generate three 2040 futures using OpenAI.

Input:  score_report dict from scorer.py + metrics dict from analyzer.py
Output: futures dict { utopia, dystopia, unexpected } each with title + narrative

Strategy:
  - Single API call with structured JSON prompt
  - Request response_format=json_object for reliable parsing
  - Retry once on JSON parse failure
  - Cache by hash of score_report to avoid redundant calls
"""

import json
import logging
import hashlib

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from config import (
    OPENAI_MODEL,
    OPENAI_MAX_TOKENS,
    OPENAI_TEMPERATURE,
    NARRATIVE_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)

# Fallback futures shown when OpenAI is unavailable
_FALLBACK_FUTURES = {
    "utopia": {
        "title": "The Signal in the Noise",
        "narrative": (
            "By 2040, your consistent commits have compounded into something "
            "remarkable. The habits you built — small, daily, deliberate — "
            "became the foundation of systems used by millions. Your open-source "
            "work, once a side project, is now infrastructure. You didn't chase "
            "fame; you chased craft. And craft, it turns out, has a very long "
            "memory. Colleagues still reference your early repositories as "
            "examples of clarity. You mentor the next generation not with "
            "lectures, but with pull requests — each one a lesson in thinking "
            "carefully before committing. The butterfly effect of your early "
            "habits rippled outward in ways you never predicted."
        ),
    },
    "dystopia": {
        "title": "The Abandoned Repository",
        "narrative": (
            "By 2040, the repositories sit untouched, their last commits "
            "timestamped years ago. The burst of activity that once defined "
            "your GitHub profile faded as quickly as it arrived. Projects "
            "were started with enthusiasm and abandoned at the first sign of "
            "friction. The collaborative opportunities you ignored — the PRs "
            "left unreviewed, the issues left unanswered — slowly closed doors "
            "you didn't know were open. In a world where your digital footprint "
            "is your resume, the gaps speak louder than the code. You are "
            "technically capable, but the record shows a pattern of "
            "incompletion that is hard to argue against."
        ),
    },
    "unexpected": {
        "title": "The Accidental Archivist",
        "narrative": (
            "Nobody predicted that your eclectic collection of repositories — "
            "spanning twelve languages, three abandoned frameworks, and one "
            "inexplicable Fortran experiment — would become historically "
            "significant. By 2040, software archaeologists study your GitHub "
            "profile as a time capsule of the 2020s developer experience. "
            "Your inconsistency, once a liability, became a kind of "
            "documentation. The half-finished projects tell the story of "
            "an era when developers were figuring it out in public, "
            "unafraid to be wrong. You didn't build a legacy on purpose. "
            "You built it by showing up, imperfectly, and leaving the receipts."
        ),
    },
}


class NarrativeEngine:
    """Generates three 2040 futures using OpenAI GPT."""

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self._cache: dict[str, dict] = {}  # in-process cache keyed by score hash

    def _cache_key(self, score_report: dict) -> str:
        """Deterministic cache key from score report."""
        payload = json.dumps(score_report, sort_keys=True, default=str)
        return hashlib.md5(payload.encode()).hexdigest()

    def _build_prompt(self, score_report: dict, metrics: dict) -> str:
        """Fill the prompt template with score and metric values."""
        dims = score_report.get("dimensions", {})
        return NARRATIVE_PROMPT_TEMPLATE.format(
            username=metrics.get("username", "unknown"),
            account_age_years=metrics.get("account_age_years", 0),
            overall_score=score_report.get("overall_score", 0),
            tendency=score_report.get("tendency", "Unexpected"),
            consistency=dims.get("consistency", 0),
            collaboration=dims.get("collaboration", 0),
            depth=dims.get("depth", 0),
            breadth=dims.get("breadth", 0),
            momentum=dims.get("momentum", 0),
            openness=dims.get("openness", 0),
            top_languages=metrics.get("top_languages", "N/A"),
            most_active_period=metrics.get("most_active_period", "N/A"),
        )

    def _call_openai(self, prompt: str) -> dict:
        """Make the OpenAI API call and parse JSON response."""
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=OPENAI_MAX_TOKENS,
            temperature=OPENAI_TEMPERATURE,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a futurist storyteller. "
                        "Always respond with valid JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        raw_content = response.choices[0].message.content
        return json.loads(raw_content)

    def generate(
        self,
        score_report: dict,
        metrics: dict,
    ) -> tuple[dict, bool]:
        """
        Generate three 2040 futures.

        Returns:
            (futures_dict, is_fallback)
            futures_dict keys: 'utopia', 'dystopia', 'unexpected'
            Each value: {'title': str, 'narrative': str}
            is_fallback: True if OpenAI failed and we used fallback text
        """
        cache_key = self._cache_key(score_report)
        if cache_key in self._cache:
            logger.info("Narrative cache hit.")
            return self._cache[cache_key], False

        prompt = self._build_prompt(score_report, metrics)

        # Attempt 1
        try:
            futures = self._call_openai(prompt)
            self._validate_futures(futures)
            self._cache[cache_key] = futures
            logger.info("Narratives generated successfully.")
            return futures, False
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning(f"OpenAI response parse error (attempt 1): {exc}. Retrying...")

        # Attempt 2 (retry)
        try:
            futures = self._call_openai(prompt)
            self._validate_futures(futures)
            self._cache[cache_key] = futures
            logger.info("Narratives generated on retry.")
            return futures, False
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.error(f"OpenAI response parse error (attempt 2): {exc}. Using fallback.")
        except (APIError, APITimeoutError, RateLimitError) as exc:
            logger.error(f"OpenAI API error: {exc}. Using fallback.")
        except Exception as exc:
            logger.error(f"Unexpected error in narrative engine: {exc}. Using fallback.")

        return _FALLBACK_FUTURES, True

    @staticmethod
    def _validate_futures(futures: dict) -> None:
        """Raise ValueError if the response structure is invalid."""
        required_keys = {"utopia", "dystopia", "unexpected"}
        if not required_keys.issubset(futures.keys()):
            raise ValueError(
                f"Missing future keys. Got: {list(futures.keys())}"
            )
        for key in required_keys:
            if "title" not in futures[key] or "narrative" not in futures[key]:
                raise ValueError(f"Future '{key}' missing title or narrative.")
