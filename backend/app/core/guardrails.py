"""Guardrails for input validation, output validation, and safety checks.

Three layers:
  1. Input guardrails  - sanitize before LLM sees it
  2. Output guardrails - validate LLM responses before returning to user
  3. Cost guardrails   - circuit breaker on spend
"""

import re
from dataclasses import dataclass

from app.models.candidate import Candidate
from app.models.match import CandidateMatch
from app.utils.logging import get_logger

logger = get_logger(__name__)


# ── Input Guardrails ──────────────────────────────────────────────────

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?prior",
    r"you\s+are\s+now\s+a",
    r"system\s*:\s*",
    r"<\s*/?system\s*>",
    r"ADMIN\s*OVERRIDE",
    r"forget\s+everything",
    r"new\s+instructions?\s*:",
]

_INJECTION_RE = re.compile("|".join(PROMPT_INJECTION_PATTERNS), re.IGNORECASE)

PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN with dashes
    r"\b[A-Z]\d{8}\b",  # passport
    r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # phone numbers
]

_PII_RE = re.compile("|".join(PII_PATTERNS))


@dataclass
class InputValidation:
    valid: bool
    sanitized_text: str
    warnings: list[str]


def validate_jd_input(text: str) -> InputValidation:
    """Sanitize job description text before sending to LLM."""
    warnings = []

    if _INJECTION_RE.search(text):
        warnings.append("prompt_injection_pattern_detected")
        logger.warning("guardrail_prompt_injection", text_preview=text[:100])
        text = _INJECTION_RE.sub("[REDACTED]", text)

    if _PII_RE.search(text):
        warnings.append("pii_pattern_detected")
        logger.warning("guardrail_pii_in_jd")
        text = _PII_RE.sub("[REDACTED]", text)

    if len(text) > 10000:
        warnings.append("jd_text_truncated")
        text = text[:10000]

    if len(text.strip()) < 20:
        return InputValidation(
            valid=False,
            sanitized_text=text,
            warnings=["jd_text_too_short"],
        )

    return InputValidation(valid=True, sanitized_text=text, warnings=warnings)


# ── Output Guardrails ─────────────────────────────────────────────────


@dataclass
class OutputValidation:
    valid: bool
    issues: list[str]


def validate_parsed_requirements(data: dict) -> OutputValidation:
    """Validate LLM-parsed JD requirements are structurally sound."""
    issues = []

    if not data.get("required_specialty"):
        issues.append("missing_required_specialty")

    min_yrs = data.get("min_years_experience")
    if min_yrs is not None and (not isinstance(min_yrs, int) or min_yrs < 0 or min_yrs > 50):
        issues.append(f"invalid_min_years: {min_yrs}")
        data["min_years_experience"] = max(0, min(50, int(min_yrs or 0)))

    skills = data.get("required_skills", [])
    if not isinstance(skills, list):
        issues.append("required_skills_not_list")
        data["required_skills"] = []

    if issues:
        logger.warning("guardrail_jd_parse_issues", issues=issues)

    return OutputValidation(valid=len(issues) == 0, issues=issues)


def validate_batch_assessment(
    assessments: list[dict],
    shortlist_ids: set[str],
) -> list[dict]:
    """Validate and clamp LLM batch assessment output."""
    validated = []

    for item in assessments:
        cid = item.get("candidate_id", "")
        if cid not in shortlist_ids:
            logger.warning("guardrail_unknown_candidate_in_assessment", candidate_id=cid)
            continue

        skills = item.get("skills_score", 0.5)
        if not isinstance(skills, int | float):
            skills = 0.5
        item["skills_score"] = max(0.0, min(1.0, float(skills)))

        if not isinstance(item.get("strengths"), list):
            item["strengths"] = []
        if not isinstance(item.get("gaps"), list):
            item["gaps"] = []

        if not item.get("summary"):
            item["summary"] = "Assessment completed."

        validated.append(item)

    if len(validated) < len(shortlist_ids):
        logger.warning(
            "guardrail_missing_assessments",
            expected=len(shortlist_ids),
            received=len(validated),
        )

    return validated


def validate_match_scores(matches: list[CandidateMatch]) -> list[str]:
    """Post-merge sanity checks on final match scores."""
    issues = []

    for m in matches:
        if m.overall_score < 0 or m.overall_score > 100:
            issues.append(f"{m.candidate_id}: score {m.overall_score} out of bounds")
            m.overall_score = max(0, min(100, m.overall_score))

        for s in m.scores:
            if s.score < 0 or s.score > 1:
                issues.append(f"{m.candidate_id}/{s.category}: score {s.score} out of bounds")
                s.score = max(0.0, min(1.0, s.score))

    if issues:
        logger.warning("guardrail_score_bounds_clamped", issues=issues)

    return issues


# ── Cost Guardrails ───────────────────────────────────────────────────

MAX_COST_PER_REQUEST_USD = 0.50
MAX_DAILY_COST_USD = 25.00


@dataclass
class CostCheck:
    allowed: bool
    reason: str


def check_request_cost(estimated_cost: float) -> CostCheck:
    """Pre-flight cost check before making LLM calls."""
    if estimated_cost > MAX_COST_PER_REQUEST_USD:
        logger.warning(
            "guardrail_cost_exceeded",
            estimated=estimated_cost,
            limit=MAX_COST_PER_REQUEST_USD,
        )
        return CostCheck(
            allowed=False,
            reason=f"Estimated cost ${estimated_cost:.4f} exceeds per-request limit ${MAX_COST_PER_REQUEST_USD}",
        )
    return CostCheck(allowed=True, reason="within_budget")


# ── Bias Guardrails ───────────────────────────────────────────────────


def check_scoring_bias(
    candidates: list[Candidate],
    matches: list[CandidateMatch],
) -> list[str]:
    """Detect potential scoring bias patterns."""
    warnings = []

    if len(matches) < 3:
        return warnings

    scores = [m.overall_score for m in matches]
    avg = sum(scores) / len(scores)

    if avg > 90:
        warnings.append("all_scores_suspiciously_high")
    if avg < 20:
        warnings.append("all_scores_suspiciously_low")

    score_range = max(scores) - min(scores)
    if score_range < 5 and len(matches) > 3:
        warnings.append("insufficient_score_differentiation")

    if warnings:
        logger.warning("guardrail_bias_check", warnings=warnings, avg_score=round(avg, 1))

    return warnings
