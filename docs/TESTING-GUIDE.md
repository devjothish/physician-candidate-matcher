# Testing Guide

Hands-on test cases for the Physician Candidate Matcher. Each test takes 30-60 seconds to run through the UI and verifies a specific capability.

**Live App:** https://frontend-phi-ruby-58.vercel.app/match
**API Docs:** https://physician-matcher-api-production.up.railway.app/docs

---

## Test 1: Strong Match (Happy Path)

**What it tests:** The system correctly identifies a near-perfect candidate.

| Field | Value |
|-------|-------|
| Job Title | Interventional Cardiologist |
| Specialty | Cardiology |
| Location | Boston, MA |
| Requirements | Board-certified interventional cardiologist with 5+ years experience in cardiac catheterization and interventional procedures. Massachusetts license required. Fellowship training preferred. |
| Experience | 5 |
| Employment Type | full-time |

**Expected result:**
- Dr. Sarah Chen ranks #1 with score 90+
- Badge shows "Strong Match"
- Strengths include board certification, MA license, interventional skills
- Gaps should be minimal (possibly availability timing)
- Score breakdown shows Specialty Alignment at 100%

---

## Test 2: Specialty Mismatch (Dealbreaker)

**What it tests:** A completely wrong specialty gets penalized hard, not just scored slightly lower.

| Field | Value |
|-------|-------|
| Job Title | Dermatologist |
| Specialty | Other |
| Location | Boston, MA |
| Requirements | Board-certified dermatologist with experience in Mohs surgery, cosmetic procedures, and skin cancer screening. Massachusetts license required. Minimum 3 years experience. |
| Experience | 3 |
| Employment Type | full-time |

**Expected result:**
- Dr. Jennifer Walsh (Dermatology, Scottsdale, AZ) should appear but with location penalty
- No cardiologists or internists should rank above dermatology candidates
- Candidates with unrelated specialties should score below 30

---

## Test 3: Location and License Check

**What it tests:** Candidates without the required state license score lower even if specialty matches.

| Field | Value |
|-------|-------|
| Job Title | Emergency Medicine Physician |
| Specialty | Emergency Medicine |
| Location | Phoenix, AZ |
| Requirements | Board-certified emergency physician for Level 1 trauma center. Arizona license required. Immediate start preferred. ATLS certification. |
| Experience | 4 |
| Employment Type | full-time |

**Expected result:**
- Dr. Kevin O'Brien (Phoenix, AZ, licensed in AZ) should rank highest
- Dr. Robert Thompson (Denver, CO) should rank lower due to no AZ license
- Location and Licensure score should clearly differentiate the two

---

## Test 4: Board Certification Required

**What it tests:** Candidates who are not board-certified get penalized when the JD requires it.

| Field | Value |
|-------|-------|
| Job Title | Cardiologist |
| Specialty | Cardiology |
| Location | Atlanta, GA |
| Requirements | Board-certified cardiologist needed for outpatient cardiology practice. Georgia license required. Echocardiography and stress testing experience preferred. |
| Experience | 3 |
| Employment Type | full-time |

**Expected result:**
- Dr. Priya Patel (Atlanta, GA, Cardiology, NOT board certified) should appear
- Her Board Certification score should be low (around 30%)
- She should rank below any board-certified cardiologist
- Gaps should mention board certification status

---

## Test 5: Experience Shortfall

**What it tests:** A candidate with insufficient experience is flagged, not hidden.

| Field | Value |
|-------|-------|
| Job Title | Senior Neurologist |
| Specialty | Other |
| Location | Philadelphia, PA |
| Requirements | Board-certified neurologist with 12+ years of clinical experience. Subspecialty in epilepsy or stroke preferred. PA license required. Academic teaching experience desired. |
| Experience | 12 |
| Employment Type | full-time |

**Expected result:**
- Dr. Michael Brown (Philadelphia, 15 yrs, Neurology) should rank #1 with 85+
- Dr. Marcus Johnson (Detroit, 5 yrs, Neurology) should rank lower
- Experience Fit score should clearly show the gap for junior candidates
- Gaps should mention years below requirement

---

## Test 6: Broad Search (Multiple Matches)

**What it tests:** System handles multiple candidates in the same specialty and ranks them meaningfully.

| Field | Value |
|-------|-------|
| Job Title | Psychiatrist |
| Specialty | Other |
| Location | Austin, TX |
| Requirements | Psychiatrist for outpatient mental health clinic. Experience in child/adolescent psychiatry, psychopharmacology, and CBT. Texas license preferred. Telepsychiatry experience a plus. |
| Experience | 5 |
| Employment Type | full-time |

**Expected result:**
- Dr. Jessica Taylor (Austin, TX, Child Psychiatry, 8 yrs) should rank highest
- Dr. Lisa Nguyen (Seattle, WA, Psychiatry, 6 yrs) should rank lower (wrong state)
- Skills breakdown should show alignment with child/adolescent psychiatry requirements
- Both should have different strengths and gaps

---

## Test 7: Empty Results

**What it tests:** System handles gracefully when no candidates match.

| Field | Value |
|-------|-------|
| Job Title | Aerospace Medicine Physician |
| Specialty | Other |
| Location | Houston, TX |
| Requirements | Board-certified aerospace medicine specialist with experience in astronaut medical screening, flight physiology, and space radiation exposure assessment. FAA aviation medical examiner certification required. |
| Experience | 10 |
| Employment Type | full-time |

**Expected result:**
- All candidates should score very low (no aerospace medicine specialists in the pool)
- No candidate should show "Strong Match"
- The system should not crash or return an error
- Results should still show scored candidates with appropriate low scores

---

## Test 8: Minimal Input

**What it tests:** System works with sparse job descriptions.

| Field | Value |
|-------|-------|
| Job Title | Pediatrician |
| Specialty | Pediatrics |
| Location | (leave empty) |
| Requirements | General pediatrician needed for primary care clinic. Board certification preferred but not required. Any location considered. |
| Experience | (leave empty) |
| Employment Type | full-time |

**Expected result:**
- Pediatrics candidates should rank highest
- Dr. Maria Rodriguez and Dr. Megan Scott should appear
- Location scores should be moderate (no specific location requirement)
- System should not error on missing optional fields

---

## Test 9: Analytics Page

**What it tests:** Match history is tracked and displayed.

1. Run Test 1 and Test 2 first (generates match data)
2. Click "Analytics" in the top navigation
3. Verify:
   - Total Matches count reflects the searches you ran
   - Cost shows actual API spend (should be under $0.01 per match)
   - Latency shows average processing time
   - Good Match Rate shows feedback if you clicked any Good/Poor buttons

---

## Test 10: Feedback Loop

**What it tests:** Recruiter feedback is recorded.

1. Run any match from Tests 1-6
2. On a result card, click "Good" for the top candidate
3. Click "Poor" for a low-ranked candidate
4. Verify:
   - Buttons disable after clicking (no double-submit)
   - Toast notification confirms feedback was recorded
   - Analytics page reflects the feedback counts

---

## API Tests (for technical reviewers)

These can be run from the Swagger docs at the API URL above, or via curl.

### Health Check
```bash
curl https://physician-matcher-api-production.up.railway.app/api/v1/health
```
Expected: `{"status":"healthy","service":"physician-candidate-matcher"}`

### Golden Set Evaluation (scoring accuracy)
```bash
curl https://physician-matcher-api-production.up.railway.app/api/v1/eval/golden-set
```
Expected: `"passed": 5, "total_cases": 5, "accuracy": 1.0`

### Match via API
```bash
curl -X POST "https://physician-matcher-api-production.up.railway.app/api/v1/match?limit=3" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Cardiologist",
    "specialty": "Cardiology",
    "location": "Boston, MA",
    "requirements": "Board-certified cardiologist with 5+ years experience in cardiac catheterization. Massachusetts license required.",
    "preferred_experience_years": 5
  }'
```
Expected: JSON response with ranked candidates, scores, and explanations.

### Analytics
```bash
curl https://physician-matcher-api-production.up.railway.app/api/v1/analytics
```
Expected: JSON with total_matches, total_cost, avg_latency_ms, feedback counts.
