"""Prompt templates for Claude API calls.

Two-phase architecture:
  Phase 1: Parse free-text JD into structured requirements (1 call)
  Phase 3: Assess shortlisted candidates for skills + narrative (1 call)

Phase 2 (deterministic scoring) uses no LLM at all.
"""

JD_PARSE_PROMPT = """Extract structured hiring requirements from this job description.

JOB DESCRIPTION:
{jd_text}

Additional context:
- Title: {title}
- Specialty: {specialty}
- Location: {location}
- Preferred experience years: {experience_years}
- Employment type: {employment_type}

Return a single JSON object with these fields:
{{
  "required_specialty": "<primary specialty>",
  "adjacent_specialties": ["<acceptable adjacent specialties>"],
  "min_years_experience": <integer>,
  "max_years_experience": <integer or null>,
  "required_state_licenses": ["<2-letter state codes>"],
  "preferred_state_licenses": ["<2-letter state codes>"],
  "board_certification_required": <true/false>,
  "required_skills": ["<specific clinical skills required>"],
  "preferred_skills": ["<nice-to-have skills>"],
  "employment_types": ["<full-time/part-time/locum tenens>"],
  "max_start_days": <integer or null>,
  "special_requirements": ["<anything else notable>"]
}}

Be precise with skills - extract specific procedures, techniques, and competencies.
Return valid JSON only. No markdown."""

BATCH_ASSESSMENT_PROMPT = """You are a healthcare recruiting assistant. Assess these shortlisted
physician candidates against the job requirements.

JOB REQUIREMENTS:
{requirements_json}

SHORTLISTED CANDIDATES (pre-screened on credentials, location, experience):
{candidates_json}

For each candidate, provide:
1. A skills alignment score (0.0 to 1.0) based on how well their clinical skills match
2. A 2-3 sentence summary a recruiter can share with the hiring manager
3. Top strengths (2-4 bullet points)
4. Any gaps or concerns (0-3 bullet points)

Return a JSON array with one object per candidate:
[
  {{
    "candidate_id": "<id>",
    "skills_score": <0.0-1.0>,
    "summary": "<recruiter-ready summary>",
    "strengths": ["<strength>", ...],
    "gaps": ["<gap>", ...]
  }},
  ...
]

RULES:
- Demographic information is excluded. Score only on qualifications.
- Be conservative. 0.9+ means near-perfect skills alignment.
- Strengths should cite specific qualifications, not vague praise.
- Gaps should be actionable concerns, not nitpicks.
- Return valid JSON only. No markdown."""

MATCHING_SYSTEM_PROMPT = """You are an expert healthcare recruiting assistant that evaluates \
physician candidates against job descriptions. You produce structured, unbiased assessments.

CRITICAL RULES:
1. NEVER use candidate name, age, gender, race, or demographics in scoring.
2. Score ONLY on clinical qualifications, skills, and credentials.
3. Provide factual explanations citing specific qualifications or gaps.
4. Be conservative in scoring.
5. Flag gaps explicitly."""
