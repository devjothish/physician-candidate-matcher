"""Golden set evaluation tests for matching accuracy.

These tests call the real Claude API and validate that scores fall within
expected ranges. They are expensive to run and should be gated behind
a pytest marker or CI flag.

Run with: pytest tests/evaluation/ -v --run-evaluation
"""

import json
import os
from pathlib import Path

import pytest

# Skip all evaluation tests unless --run-evaluation flag is passed
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_EVALUATION") != "1",
    reason="Evaluation tests require RUN_EVALUATION=1 (they call Claude API)",
)


GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"


@pytest.fixture(scope="module")
def golden_set() -> dict:
    """Load the golden test set."""
    with open(GOLDEN_SET_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def claude_service():
    """Create a real ClaudeService for evaluation."""
    from app.services.claude import ClaudeService

    return ClaudeService(request_id="evaluation-test")


def _run_match(claude_service, job_data: dict, candidate_data: dict) -> dict:
    """Run a single candidate match through Claude and return parsed scores."""
    from app.config import get_settings
    from app.core.prompts import MATCHING_SYSTEM_PROMPT, MATCHING_USER_PROMPT

    settings = get_settings()

    job_json = json.dumps(job_data, indent=2)
    candidate_json = json.dumps(candidate_data, indent=2)

    user_prompt = MATCHING_USER_PROMPT.format(
        job_json=job_json,
        candidate_json=candidate_json,
    )

    return claude_service.complete(
        system_prompt=MATCHING_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=settings.default_model,
        max_tokens=2048,
        prompt_type="evaluation",
    )


class TestGoldenSetAccuracy:
    """Validate matching accuracy against golden test cases."""

    def test_golden_set_loads(self, golden_set: dict) -> None:
        """Golden set should load and contain expected structure."""
        assert "test_cases" in golden_set
        assert len(golden_set["test_cases"]) == 10

    @pytest.mark.parametrize(
        "case_index",
        range(10),
        ids=[
            "perfect_cardiology",
            "wrong_specialty",
            "adjacent_specialty",
            "location_mismatch",
            "board_eligible",
            "overqualified",
            "perfect_psychiatry",
            "partial_skills",
            "availability_mismatch",
            "locum_tenens",
        ],
    )
    def test_golden_case(
        self, golden_set: dict, claude_service, case_index: int
    ) -> None:
        """Each golden case should produce scores within expected ranges."""
        case = golden_set["test_cases"][case_index]
        expected = case["expected"]

        result = _run_match(
            claude_service,
            job_data=case["job"],
            candidate_data=case["candidate"],
        )

        overall = result.get("overall_score", 0)
        scores_by_cat = {
            s["category"]: s["score"] for s in result.get("scores", [])
        }

        # Check overall score range
        if "overall_score_min" in expected:
            assert overall >= expected["overall_score_min"], (
                f"[{case['id']}] Overall {overall} < min {expected['overall_score_min']}"
            )
        if "overall_score_max" in expected:
            assert overall <= expected["overall_score_max"], (
                f"[{case['id']}] Overall {overall} > max {expected['overall_score_max']}"
            )

        # Check category-specific scores
        for cat in ["specialty", "location", "credentials", "availability"]:
            score_key = f"{cat}_score_min"
            if score_key in expected:
                cat_score = scores_by_cat.get(f"{cat}_match", 0)
                assert cat_score >= expected[score_key], (
                    f"[{case['id']}] {cat} score {cat_score} < min {expected[score_key]}"
                )

            max_key = f"{cat}_score_max"
            if max_key in expected:
                cat_score = scores_by_cat.get(f"{cat}_match", 1.0)
                assert cat_score <= expected[max_key], (
                    f"[{case['id']}] {cat} score {cat_score} > max {expected[max_key]}"
                )

        # Check gaps presence
        gaps = result.get("gaps", [])
        if expected.get("must_have_gaps"):
            assert len(gaps) > 0, (
                f"[{case['id']}] Expected gaps but got none"
            )

    def test_ranking_order(self, golden_set: dict, claude_service) -> None:
        """Perfect match should rank higher than wrong specialty."""
        perfect = golden_set["test_cases"][0]  # Perfect cardiology
        wrong = golden_set["test_cases"][1]  # Wrong specialty

        perfect_result = _run_match(
            claude_service, perfect["job"], perfect["candidate"]
        )
        wrong_result = _run_match(
            claude_service, wrong["job"], wrong["candidate"]
        )

        assert perfect_result["overall_score"] > wrong_result["overall_score"], (
            f"Perfect match ({perfect_result['overall_score']}) should score "
            f"higher than wrong specialty ({wrong_result['overall_score']})"
        )
