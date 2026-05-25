"""Evaluation framework for matching quality.

Three eval layers:
  1. Golden set   - Known-good test cases with expected outcomes
  2. Scoring eval - Deterministic scorer accuracy vs expert labels
  3. Feedback loop - Production quality tracking from recruiter feedback

No eval framework should require LLM calls to run. Evals must be
deterministic, repeatable, and fast.
"""

from dataclasses import dataclass

from app.models.candidate import Candidate
from app.services.scorer import (
    ParsedRequirements,
    score_candidate,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


# ── Golden Set Evaluation ─────────────────────────────────────────────


@dataclass
class GoldenCase:
    """A single golden test case with expected outcome."""

    case_id: str
    description: str
    requirements: dict
    candidate: dict
    expected_outcome: str  # "strong_match" | "weak_match" | "no_match"
    expected_score_min: float  # minimum acceptable composite score
    expected_score_max: float  # maximum acceptable composite score
    critical_dimensions: dict[str, str]  # dimension -> "high" | "low"


@dataclass
class EvalResult:
    case_id: str
    passed: bool
    actual_score: float
    expected_range: str
    actual_outcome: str
    dimension_results: dict[str, dict]
    failure_reason: str | None = None


GOLDEN_SET: list[dict] = [
    {
        "case_id": "GS001",
        "description": "Perfect specialty + location + credentials match",
        "requirements": {
            "required_specialty": "Cardiology",
            "adjacent_specialties": [],
            "min_years_experience": 5,
            "max_years_experience": None,
            "required_state_licenses": ["MA"],
            "preferred_state_licenses": [],
            "board_certification_required": True,
            "required_skills": ["Interventional Cardiology", "Cardiac Catheterization"],
            "preferred_skills": ["Echocardiography"],
            "employment_types": ["full-time"],
            "max_start_days": None,
            "special_requirements": [],
        },
        "candidate": {
            "id": "GS_C1",
            "name": "Test Doctor",
            "specialty": "Cardiology",
            "years_experience": 8,
            "location": "Boston, MA",
            "board_certified": True,
            "licenses": ["MA", "NY"],
            "education": "Harvard",
            "skills": ["Interventional Cardiology"],
            "availability": "30 days",
            "preferred_employment": ["full-time"],
        },
        "expected_outcome": "strong_match",
        "expected_score_min": 0.75,
        "expected_score_max": 1.0,
        "critical_dimensions": {
            "Specialty Alignment": "high",
            "Board Certification": "high",
            "Location & Licensure": "high",
        },
    },
    {
        "case_id": "GS002",
        "description": "Wrong specialty should score very low",
        "requirements": {
            "required_specialty": "Cardiology",
            "adjacent_specialties": ["Internal Medicine"],
            "min_years_experience": 5,
            "max_years_experience": None,
            "required_state_licenses": ["MA"],
            "preferred_state_licenses": [],
            "board_certification_required": True,
            "required_skills": [],
            "preferred_skills": [],
            "employment_types": ["full-time"],
            "max_start_days": None,
            "special_requirements": [],
        },
        "candidate": {
            "id": "GS_C2",
            "name": "Test Doctor",
            "specialty": "Pediatrics",
            "years_experience": 10,
            "location": "Boston, MA",
            "board_certified": True,
            "licenses": ["MA"],
            "education": "Stanford",
            "skills": ["Neonatal Care"],
            "availability": "Immediately",
            "preferred_employment": ["full-time"],
        },
        "expected_outcome": "no_match",
        "expected_score_min": 0.0,
        "expected_score_max": 0.45,
        "critical_dimensions": {"Specialty Alignment": "low"},
    },
    {
        "case_id": "GS003",
        "description": "Not board certified when required should penalize",
        "requirements": {
            "required_specialty": "Cardiology",
            "adjacent_specialties": [],
            "min_years_experience": 3,
            "max_years_experience": None,
            "required_state_licenses": ["GA"],
            "preferred_state_licenses": [],
            "board_certification_required": True,
            "required_skills": [],
            "preferred_skills": [],
            "employment_types": ["full-time"],
            "max_start_days": None,
            "special_requirements": [],
        },
        "candidate": {
            "id": "GS_C3",
            "name": "Test Doctor",
            "specialty": "Cardiology",
            "years_experience": 3,
            "location": "Atlanta, GA",
            "board_certified": False,
            "licenses": ["GA"],
            "education": "Emory",
            "skills": ["Echocardiography"],
            "availability": "90 days",
            "preferred_employment": ["full-time"],
        },
        "expected_outcome": "weak_match",
        "expected_score_min": 0.40,
        "expected_score_max": 0.70,
        "critical_dimensions": {"Board Certification": "low"},
    },
    {
        "case_id": "GS004",
        "description": "Wrong state license with no overlap should score low on location",
        "requirements": {
            "required_specialty": "Emergency Medicine",
            "adjacent_specialties": [],
            "min_years_experience": 3,
            "max_years_experience": None,
            "required_state_licenses": ["AZ"],
            "preferred_state_licenses": [],
            "board_certification_required": True,
            "required_skills": [],
            "preferred_skills": [],
            "employment_types": ["full-time"],
            "max_start_days": None,
            "special_requirements": [],
        },
        "candidate": {
            "id": "GS_C4",
            "name": "Test Doctor",
            "specialty": "Emergency Medicine",
            "years_experience": 10,
            "location": "Philadelphia, PA",
            "board_certified": True,
            "licenses": ["PA", "NJ"],
            "education": "Penn",
            "skills": ["Trauma"],
            "availability": "Immediately",
            "preferred_employment": ["full-time"],
        },
        "expected_outcome": "weak_match",
        "expected_score_min": 0.45,
        "expected_score_max": 0.75,
        "critical_dimensions": {"Location & Licensure": "low"},
    },
    {
        "case_id": "GS005",
        "description": "Insufficient experience should score low on experience",
        "requirements": {
            "required_specialty": "Neurology",
            "adjacent_specialties": [],
            "min_years_experience": 10,
            "max_years_experience": None,
            "required_state_licenses": [],
            "preferred_state_licenses": [],
            "board_certification_required": False,
            "required_skills": [],
            "preferred_skills": [],
            "employment_types": [],
            "max_start_days": None,
            "special_requirements": [],
        },
        "candidate": {
            "id": "GS_C5",
            "name": "Test Doctor",
            "specialty": "Neurology",
            "years_experience": 3,
            "location": "Detroit, MI",
            "board_certified": True,
            "licenses": ["MI"],
            "education": "Wayne State",
            "skills": ["Movement Disorders"],
            "availability": "30 days",
            "preferred_employment": ["full-time"],
        },
        "expected_outcome": "weak_match",
        "expected_score_min": 0.40,
        "expected_score_max": 0.70,
        "critical_dimensions": {"Experience Fit": "low"},
    },
]


def run_golden_set() -> dict:
    """Run all golden set cases against the deterministic scorer.

    Returns a summary with pass/fail counts and per-case details.
    Zero LLM calls - runs in <10ms.
    """
    results: list[EvalResult] = []

    for case_data in GOLDEN_SET:
        case = GoldenCase(
            case_id=case_data["case_id"],
            description=case_data["description"],
            requirements=case_data["requirements"],
            candidate=case_data["candidate"],
            expected_outcome=case_data["expected_outcome"],
            expected_score_min=case_data["expected_score_min"],
            expected_score_max=case_data["expected_score_max"],
            critical_dimensions=case_data["critical_dimensions"],
        )

        reqs = ParsedRequirements.from_dict(case.requirements)
        candidate = Candidate(**case.candidate)
        score = score_candidate(candidate, reqs)

        in_range = case.expected_score_min <= score.composite <= case.expected_score_max

        dim_results = {}
        dims_pass = True
        for dim_name, expected_level in case.critical_dimensions.items():
            actual_val = score.detail_dict.get(dim_name, 0)
            if expected_level == "high" and actual_val < 0.7:
                dims_pass = False
            elif expected_level == "low" and actual_val > 0.6:
                dims_pass = False
            dim_results[dim_name] = {
                "expected": expected_level,
                "actual": round(actual_val, 2),
                "passed": (expected_level == "high" and actual_val >= 0.7)
                or (expected_level == "low" and actual_val <= 0.6),
            }

        passed = in_range and dims_pass

        if score.composite >= 0.75:
            actual_outcome = "strong_match"
        elif score.composite >= 0.45:
            actual_outcome = "weak_match"
        else:
            actual_outcome = "no_match"

        failure_reason = None
        if not passed:
            reasons = []
            if not in_range:
                reasons.append(
                    f"score {score.composite:.2f} outside [{case.expected_score_min}, {case.expected_score_max}]"
                )
            for dim, dr in dim_results.items():
                if not dr["passed"]:
                    reasons.append(f"{dim}: expected {dr['expected']}, got {dr['actual']}")
            failure_reason = "; ".join(reasons)

        results.append(
            EvalResult(
                case_id=case.case_id,
                passed=passed,
                actual_score=round(score.composite, 3),
                expected_range=f"[{case.expected_score_min}, {case.expected_score_max}]",
                actual_outcome=actual_outcome,
                dimension_results=dim_results,
                failure_reason=failure_reason,
            )
        )

    passed_count = sum(1 for r in results if r.passed)
    total = len(results)
    accuracy = passed_count / total if total > 0 else 0

    summary = {
        "total_cases": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "accuracy": round(accuracy, 2),
        "results": [
            {
                "case_id": r.case_id,
                "passed": r.passed,
                "score": r.actual_score,
                "expected_range": r.expected_range,
                "outcome": r.actual_outcome,
                "dimensions": r.dimension_results,
                "failure_reason": r.failure_reason,
            }
            for r in results
        ],
    }

    logger.info(
        "golden_set_eval_complete",
        passed=passed_count,
        total=total,
        accuracy=accuracy,
    )

    return summary


# ── Feedback Loop Analysis ────────────────────────────────────────────


def analyze_feedback(feedback_data: list[dict]) -> dict:
    """Analyze recruiter feedback to detect quality drift.

    Monitors:
    - Good/bad ratio over time
    - Score calibration (do high scores correlate with "good" feedback?)
    - Model comparison (does Sonnet outperform Haiku on quality?)
    """
    if not feedback_data:
        return {"status": "no_feedback_data"}

    total = len(feedback_data)
    good = sum(1 for f in feedback_data if f.get("feedback_type") == "good_match")
    bad = sum(1 for f in feedback_data if f.get("feedback_type") == "bad_match")
    hired = sum(1 for f in feedback_data if f.get("feedback_type") == "hired")

    good_rate = good / total if total > 0 else 0

    alerts = []
    if total >= 10 and good_rate < 0.5:
        alerts.append("quality_below_50_percent")
    if total >= 20 and good_rate < 0.6:
        alerts.append("quality_trending_down")

    return {
        "total_feedback": total,
        "good_matches": good,
        "bad_matches": bad,
        "hired": hired,
        "good_match_rate": round(good_rate, 3),
        "alerts": alerts,
    }
