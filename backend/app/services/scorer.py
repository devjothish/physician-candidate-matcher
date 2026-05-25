"""Deterministic scoring engine - no LLM calls.

Scores candidates on 6 structured dimensions using pure Python.
Runs in <1ms per candidate with zero cost and zero hallucination risk.
"""

from dataclasses import dataclass

from app.models.candidate import Candidate
from app.utils.logging import get_logger

logger = get_logger(__name__)

# US state adjacency for location scoring
ADJACENT_STATES: dict[str, set[str]] = {
    "MA": {"CT", "RI", "NH", "VT", "NY"},
    "NY": {"NJ", "CT", "PA", "VT", "MA"},
    "CA": {"OR", "NV", "AZ"},
    "TX": {"NM", "OK", "AR", "LA"},
    "FL": {"GA", "AL"},
    "IL": {"IN", "WI", "IA", "MO", "KY"},
    "PA": {"NJ", "NY", "DE", "MD", "OH", "WV"},
    "OH": {"PA", "WV", "KY", "IN", "MI"},
    "GA": {"FL", "AL", "TN", "NC", "SC"},
    "NC": {"SC", "GA", "TN", "VA"},
    "MI": {"OH", "IN", "WI"},
    "NJ": {"NY", "PA", "DE"},
    "VA": {"MD", "DC", "WV", "KY", "TN", "NC"},
    "WA": {"OR", "ID"},
    "AZ": {"CA", "NV", "UT", "NM", "CO"},
    "CO": {"WY", "NE", "KS", "OK", "NM", "AZ", "UT"},
    "TN": {"KY", "VA", "NC", "GA", "AL", "MS", "AR", "MO"},
    "MN": {"WI", "IA", "SD", "ND"},
    "MO": {"IL", "KY", "TN", "AR", "OK", "KS", "NE", "IA"},
    "IN": {"MI", "OH", "KY", "IL"},
    "MD": {"PA", "DE", "VA", "DC", "WV"},
    "OR": {"WA", "CA", "NV", "ID"},
}


@dataclass
class ParsedRequirements:
    """Structured requirements extracted from a JD by the LLM."""

    required_specialty: str
    adjacent_specialties: list[str]
    min_years_experience: int
    max_years_experience: int | None
    required_state_licenses: list[str]
    preferred_state_licenses: list[str]
    board_certification_required: bool
    required_skills: list[str]
    preferred_skills: list[str]
    employment_types: list[str]
    max_start_days: int | None
    special_requirements: list[str]

    @classmethod
    def from_dict(cls, data: dict) -> "ParsedRequirements":
        return cls(
            required_specialty=data.get("required_specialty", ""),
            adjacent_specialties=data.get("adjacent_specialties", []),
            min_years_experience=data.get("min_years_experience", 0),
            max_years_experience=data.get("max_years_experience"),
            required_state_licenses=data.get("required_state_licenses", []),
            preferred_state_licenses=data.get("preferred_state_licenses", []),
            board_certification_required=data.get("board_certification_required", False),
            required_skills=data.get("required_skills", []),
            preferred_skills=data.get("preferred_skills", []),
            employment_types=data.get("employment_types", []),
            max_start_days=data.get("max_start_days"),
            special_requirements=data.get("special_requirements", []),
        )


@dataclass
class DeterministicScore:
    """Pre-LLM score for a single candidate."""

    candidate: Candidate
    specialty_score: float
    experience_score: float
    location_score: float
    credentials_score: float
    availability_score: float
    employment_score: float
    composite: float

    @property
    def detail_dict(self) -> dict:
        return {
            "Specialty Alignment": self.specialty_score,
            "Experience Fit": self.experience_score,
            "Location & Licensure": self.location_score,
            "Board Certification": self.credentials_score,
            "Availability": self.availability_score,
            "Employment Fit": self.employment_score,
        }


WEIGHTS = {
    "specialty": 0.35,
    "experience": 0.20,
    "location": 0.15,
    "credentials": 0.15,
    "availability": 0.10,
    "employment": 0.05,
}


def _apply_dealbreakers(composite: float, scores: dict[str, float]) -> float:
    """Hard penalties for critical mismatches that should tank the overall score."""
    if scores.get("specialty", 1.0) <= 0.3:
        composite *= 0.4
    if scores.get("credentials", 1.0) <= 0.4:
        composite *= 0.7
    if scores.get("experience", 1.0) <= 0.3:
        composite *= 0.75
    if scores.get("location", 1.0) <= 0.3:
        composite *= 0.75
    return composite


def score_candidate(
    candidate: Candidate,
    reqs: ParsedRequirements,
) -> DeterministicScore:
    """Score a candidate on all deterministic dimensions."""

    specialty = _score_specialty(candidate, reqs)
    experience = _score_experience(candidate, reqs)
    location = _score_location(candidate, reqs)
    credentials = _score_credentials(candidate, reqs)
    availability = _score_availability(candidate, reqs)
    employment = _score_employment(candidate, reqs)

    composite = (
        specialty * WEIGHTS["specialty"]
        + experience * WEIGHTS["experience"]
        + location * WEIGHTS["location"]
        + credentials * WEIGHTS["credentials"]
        + availability * WEIGHTS["availability"]
        + employment * WEIGHTS["employment"]
    )

    composite = _apply_dealbreakers(
        composite,
        {
            "specialty": specialty,
            "experience": experience,
            "credentials": credentials,
            "location": location,
        },
    )

    return DeterministicScore(
        candidate=candidate,
        specialty_score=specialty,
        experience_score=experience,
        location_score=location,
        credentials_score=credentials,
        availability_score=availability,
        employment_score=employment,
        composite=composite,
    )


def score_all(
    candidates: list[Candidate],
    reqs: ParsedRequirements,
    threshold: float = 0.0,
) -> list[DeterministicScore]:
    """Score and rank all candidates, filtering below threshold."""
    scores = [score_candidate(c, reqs) for c in candidates]
    scores.sort(key=lambda s: s.composite, reverse=True)
    if threshold > 0:
        scores = [s for s in scores if s.composite >= threshold]
    return scores


def _score_specialty(c: Candidate, r: ParsedRequirements) -> float:
    c_spec = c.specialty.lower().strip()
    r_spec = r.required_specialty.lower().strip()

    if c_spec == r_spec or c_spec in r_spec or r_spec in c_spec:
        return 1.0

    adjacent_lower = [s.lower() for s in r.adjacent_specialties]
    if c_spec in adjacent_lower:
        return 0.6

    return 0.1


def _score_experience(c: Candidate, r: ParsedRequirements) -> float:
    yrs = c.years_experience
    min_yrs = r.min_years_experience
    max_yrs = r.max_years_experience

    if min_yrs == 0 and max_yrs is None:
        return 0.8

    diff = yrs - min_yrs

    if diff >= 0:
        if max_yrs and yrs > max_yrs:
            over = yrs - max_yrs
            return max(0.5, 1.0 - over * 0.1)
        return 1.0
    elif diff >= -2:
        return 0.7
    elif diff >= -5:
        return 0.4
    else:
        return 0.2


def _score_location(c: Candidate, r: ParsedRequirements) -> float:
    if not r.required_state_licenses and not r.preferred_state_licenses:
        return 0.7

    candidate_licenses = {lic.upper() for lic in c.licenses}
    required = {s.upper() for s in r.required_state_licenses}
    preferred = {s.upper() for s in r.preferred_state_licenses}
    all_target = required | preferred

    if required and required.issubset(candidate_licenses):
        return 1.0

    if all_target & candidate_licenses:
        return 0.9

    for target_state in required | preferred:
        adjacent = ADJACENT_STATES.get(target_state, set())
        if candidate_licenses & adjacent:
            return 0.5

    return 0.2


def _score_credentials(c: Candidate, r: ParsedRequirements) -> float:
    if r.board_certification_required:
        return 1.0 if c.board_certified else 0.3
    return 1.0 if c.board_certified else 0.7


def _score_availability(c: Candidate, r: ParsedRequirements) -> float:
    avail = (c.availability or "").lower().strip()

    if not avail or avail == "unknown":
        return 0.4

    if "immediate" in avail:
        return 1.0

    days = _parse_days(avail)
    if days is None:
        return 0.5

    if r.max_start_days is not None:
        if days <= r.max_start_days:
            return 1.0
        elif days <= r.max_start_days + 30:
            return 0.6
        else:
            return 0.3

    if days <= 30:
        return 0.9
    elif days <= 60:
        return 0.7
    elif days <= 90:
        return 0.5
    else:
        return 0.3


def _score_employment(c: Candidate, r: ParsedRequirements) -> float:
    if not r.employment_types:
        return 0.8

    req_lower = {e.lower() for e in r.employment_types}
    cand_lower = {e.lower() for e in c.preferred_employment}

    if req_lower & cand_lower:
        return 1.0
    return 0.4


def _parse_days(text: str) -> int | None:
    """Extract number of days from availability text like '30 days' or '90 days'."""
    import re

    match = re.search(r"(\d+)\s*day", text)
    if match:
        return int(match.group(1))
    return None
