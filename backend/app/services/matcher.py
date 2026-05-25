"""Two-phase matching service.

Phase 1: Parse JD into structured requirements (1 LLM call)
Phase 2: Score ALL candidates deterministically (0 LLM calls, <1ms)
Phase 3: Batch-assess shortlist for skills + narrative (1 LLM call)

Total: 2 LLM calls, ~5s, ~$0.003 regardless of candidate pool size.
"""

import json
import time
import uuid

from app.config import get_settings
from app.core.guardrails import (
    check_scoring_bias,
    validate_batch_assessment,
    validate_jd_input,
    validate_match_scores,
    validate_parsed_requirements,
)
from app.core.observability import PhaseMetrics, RequestTrace
from app.core.prompts import (
    BATCH_ASSESSMENT_PROMPT,
    JD_PARSE_PROMPT,
    MATCHING_SYSTEM_PROMPT,
)
from app.db.repositories.candidates import CandidateRepository
from app.db.repositories.matches import MatchRepository
from app.models.candidate import Candidate
from app.models.job import JobDescription
from app.models.match import CandidateMatch, MatchResponse, MatchScore
from app.services.claude import ClaudeService, LLMResult
from app.services.scorer import (
    DeterministicScore,
    ParsedRequirements,
    score_all,
)
from app.utils.exceptions import MatchingError
from app.utils.logging import get_logger

logger = get_logger(__name__)

SHORTLIST_SIZE = 8
DETERMINISTIC_THRESHOLD = 0.25


class MatchingService:

    def __init__(self) -> None:
        self.settings = get_settings()
        self.candidate_repo = CandidateRepository()
        self.match_repo = MatchRepository()

    def match(
        self,
        job: JobDescription,
        limit: int = 10,
    ) -> MatchResponse:
        request_id = str(uuid.uuid4())
        trace = RequestTrace(request_id=request_id, job_title=job.title)

        logger.info(
            "match_started",
            request_id=request_id,
            job_title=job.title,
            specialty=job.specialty,
        )

        # Input guardrails
        input_check = validate_jd_input(job.requirements)
        if not input_check.valid:
            raise MatchingError(detail="Job description too short or invalid.")
        if input_check.warnings:
            for w in input_check.warnings:
                trace.add_warning(w)
        sanitized_requirements = input_check.sanitized_text

        claude = ClaudeService(request_id)
        model = self.settings.default_model

        # Phase 1: Parse JD → structured requirements (1 LLM call)
        phase1_start = time.time()
        job_for_parse = JobDescription(
            title=job.title,
            specialty=job.specialty,
            location=job.location,
            requirements=sanitized_requirements,
            preferred_experience_years=job.preferred_experience_years,
            employment_type=job.employment_type,
        )
        reqs, phase1_llm = self._parse_jd(claude, job_for_parse, model)
        phase1_ms = (time.time() - phase1_start) * 1000
        trace.add_phase(
            PhaseMetrics(
                name="jd_parse",
                latency_ms=phase1_ms,
                llm_calls=1,
                input_tokens=phase1_llm.input_tokens,
                output_tokens=phase1_llm.output_tokens,
                cost_usd=phase1_llm.cost_usd,
                items_in=1,
                items_out=1,
            )
        )

        # Output guardrail on parsed requirements
        import dataclasses

        req_validation = validate_parsed_requirements(dataclasses.asdict(reqs))
        if req_validation.issues:
            for issue in req_validation.issues:
                trace.add_warning(f"jd_parse:{issue}")

        # Fetch candidates
        candidates = self.candidate_repo.get_by_specialty(job.specialty, limit=self.settings.max_candidates_per_request)
        if not candidates:
            candidates = self.candidate_repo.get_all(limit=self.settings.max_candidates_per_request)
        if not candidates:
            raise MatchingError(detail="No candidates available.")

        # Phase 2: Deterministic scoring (0 LLM calls, <1ms)
        phase2_start = time.time()
        scored = score_all(candidates, reqs, threshold=DETERMINISTIC_THRESHOLD)
        phase2_ms = (time.time() - phase2_start) * 1000
        trace.add_phase(
            PhaseMetrics(
                name="deterministic_score",
                latency_ms=phase2_ms,
                llm_calls=0,
                items_in=len(candidates),
                items_out=len(scored),
            )
        )

        if not scored:
            raise MatchingError(detail="No candidates met the minimum scoring threshold.")

        # Phase 3: LLM assessment on shortlist only (1 LLM call)
        shortlist = scored[:SHORTLIST_SIZE]
        phase3_start = time.time()
        raw_assessments, phase3_llm = self._batch_assess(claude, reqs, shortlist, model)

        # Output guardrail on LLM assessments
        shortlist_ids = {ds.candidate.id for ds in shortlist}
        validated = validate_batch_assessment(list(raw_assessments.values()), shortlist_ids)
        assessments = {item["candidate_id"]: item for item in validated}

        phase3_ms = (time.time() - phase3_start) * 1000
        trace.add_phase(
            PhaseMetrics(
                name="llm_assessment",
                latency_ms=phase3_ms,
                llm_calls=1,
                input_tokens=phase3_llm.input_tokens if phase3_llm else 0,
                output_tokens=phase3_llm.output_tokens if phase3_llm else 0,
                cost_usd=phase3_llm.cost_usd if phase3_llm else 0,
                items_in=len(shortlist),
                items_out=len(assessments),
            )
        )

        # Merge deterministic scores + LLM assessments
        matches = self._merge_results(shortlist, assessments, reqs)
        matches.sort(key=lambda m: m.overall_score, reverse=True)
        for i, m in enumerate(matches, 1):
            m.rank = i

        # Score bounds guardrail
        score_issues = validate_match_scores(matches)
        if score_issues:
            for issue in score_issues:
                trace.add_warning(f"score_bounds:{issue}")

        # Bias detection guardrail
        bias_warnings = check_scoring_bias([ds.candidate for ds in shortlist], matches)
        for bw in bias_warnings:
            trace.add_warning(f"bias:{bw}")

        top_matches = matches[:limit]

        response = MatchResponse(
            job_title=job.title,
            total_candidates=len(candidates),
            matches=top_matches,
            processing_time_ms=round(trace.total_latency_ms, 1),
            model_used=model,
            tokens_used=trace.total_tokens,
            estimated_cost_usd=round(trace.total_cost_usd, 4),
            request_id=request_id,
        )

        self._save_matches(job, response, model, trace.total_latency_ms)

        # Emit full request trace
        trace.emit()

        return response

    def _parse_jd(
        self,
        claude: ClaudeService,
        job: JobDescription,
        model: str,
    ) -> tuple[ParsedRequirements, LLMResult]:
        prompt = JD_PARSE_PROMPT.format(
            jd_text=job.requirements,
            title=job.title,
            specialty=job.specialty,
            location=job.location,
            experience_years=job.preferred_experience_years or "not specified",
            employment_type=job.employment_type or "not specified",
        )

        llm_result = claude.complete(
            system_prompt="You extract structured data from job descriptions. Return JSON only.",
            user_prompt=prompt,
            model=model,
            max_tokens=1024,
            prompt_type="jd_parse",
        )

        return ParsedRequirements.from_dict(llm_result.parsed), llm_result

    def _batch_assess(
        self,
        claude: ClaudeService,
        reqs: ParsedRequirements,
        shortlist: list[DeterministicScore],
        model: str,
    ) -> tuple[dict[str, dict], LLMResult | None]:
        candidates_for_llm = []
        for ds in shortlist:
            c = ds.candidate
            candidates_for_llm.append(
                {
                    "candidate_id": c.id,
                    "specialty": c.specialty,
                    "years_experience": c.years_experience,
                    "location": c.location,
                    "board_certified": c.board_certified,
                    "licenses": c.licenses,
                    "education": c.education,
                    "skills": c.skills,
                    "availability": c.availability,
                    "deterministic_score": round(ds.composite * 100),
                }
            )

        reqs_dict = {
            "required_specialty": reqs.required_specialty,
            "min_years_experience": reqs.min_years_experience,
            "required_skills": reqs.required_skills,
            "preferred_skills": reqs.preferred_skills,
            "required_state_licenses": reqs.required_state_licenses,
            "board_certification_required": reqs.board_certification_required,
            "special_requirements": reqs.special_requirements,
        }

        prompt = BATCH_ASSESSMENT_PROMPT.format(
            requirements_json=json.dumps(reqs_dict, indent=2),
            candidates_json=json.dumps(candidates_for_llm, indent=2),
        )

        llm_result = claude.complete(
            system_prompt=MATCHING_SYSTEM_PROMPT,
            user_prompt=prompt,
            model=model,
            max_tokens=4096,
            prompt_type="batch_assessment",
        )

        if isinstance(llm_result.parsed, list):
            assessments = {
                item["candidate_id"]: item
                for item in llm_result.parsed
                if isinstance(item, dict) and "candidate_id" in item
            }
            return assessments, llm_result

        logger.warning(
            "batch_assessment_unexpected_format",
            request_id=claude.request_id,
            result_type=type(llm_result.parsed).__name__,
        )
        return {}, llm_result

    def _merge_results(
        self,
        shortlist: list[DeterministicScore],
        assessments: dict[str, dict],
        reqs: ParsedRequirements,
    ) -> list[CandidateMatch]:
        matches = []

        for ds in shortlist:
            c = ds.candidate
            assessment = assessments.get(c.id, {})

            skills_score = assessment.get("skills_score", 0.5)

            # Final score: 70% deterministic + 30% LLM skills assessment
            overall = (ds.composite * 0.70 + skills_score * 0.30) * 100

            scores = [
                MatchScore(
                    category=label,
                    score=value,
                    explanation=self._explain_score(label, value, c, reqs),
                )
                for label, value in ds.detail_dict.items()
            ]
            scores.append(
                MatchScore(
                    category="Clinical Skills",
                    score=skills_score,
                    explanation=assessment.get("summary", "Skills assessed by AI review"),
                )
            )

            matches.append(
                CandidateMatch(
                    candidate_id=c.id,
                    candidate_name=c.name,
                    overall_score=round(overall, 1),
                    rank=0,
                    scores=scores,
                    summary=assessment.get("summary", ""),
                    strengths=assessment.get("strengths", []),
                    gaps=assessment.get("gaps", []),
                )
            )

        return matches

    def _explain_score(
        self,
        label: str,
        score: float,
        c: Candidate,
        r: ParsedRequirements,
    ) -> str:
        pct = round(score * 100)
        if label == "Specialty Alignment":
            if score >= 0.9:
                return f"Exact specialty match: {c.specialty}"
            elif score >= 0.5:
                return f"{c.specialty} is adjacent to {r.required_specialty}"
            return f"{c.specialty} does not align with {r.required_specialty}"

        if label == "Experience Fit":
            if score >= 0.9:
                return f"{c.years_experience} years meets the {r.min_years_experience}+ year requirement"
            gap = r.min_years_experience - c.years_experience
            return f"{c.years_experience} years is {gap} years below the {r.min_years_experience}+ year requirement"

        if label == "Location & Licensure":
            licenses = ", ".join(c.licenses) if c.licenses else "none"
            required = ", ".join(r.required_state_licenses) if r.required_state_licenses else "any"
            if score >= 0.9:
                return f"Licensed in {licenses}; meets {required} requirement"
            return f"Licensed in {licenses}; {required} license needed"

        if label == "Board Certification":
            status = "Board certified" if c.board_certified else "Not board certified"
            req = "required" if r.board_certification_required else "preferred"
            return f"{status}; certification is {req}"

        if label == "Availability":
            return f"Available: {c.availability or 'not specified'}"

        if label == "Employment Fit":
            prefs = ", ".join(c.preferred_employment) if c.preferred_employment else "not specified"
            return f"Prefers: {prefs}"

        return f"Score: {pct}%"

    def _save_matches(
        self,
        job: JobDescription,
        response: MatchResponse,
        model: str,
        latency_ms: float,
    ) -> None:
        try:
            self.match_repo.create(
                job=job,
                match_response=response,
                model_used=model,
                tokens_used=response.tokens_used,
                cost_usd=response.estimated_cost_usd,
                latency_ms=latency_ms,
            )
        except Exception:
            logger.exception(
                "match_persistence_failed",
                request_id=response.request_id,
            )
