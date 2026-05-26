import type { FeedbackType } from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface JobDescription {
  title: string;
  specialty: string;
  location: string;
  requirements: string;
  preferred_experience_years?: number;
  employment_type?: string;
}

export interface MatchScore {
  category: string;
  score: number;
  explanation: string;
}

export interface CandidateMatch {
  match_id: string;
  candidate_id: string;
  candidate_name: string;
  overall_score: number;
  rank: number;
  scores: MatchScore[];
  summary: string;
  strengths: string[];
  gaps: string[];
}

export interface MatchResponse {
  job_title: string;
  total_candidates: number;
  matches: CandidateMatch[];
  processing_time_ms: number;
  model_used: string;
  tokens_used: number;
  estimated_cost_usd: number;
  request_id: string;
}

export interface Analytics {
  total_matches: number;
  unique_candidates: number;
  total_tokens: number;
  total_cost: number;
  avg_latency_ms: number;
  good_matches: number;
  bad_matches: number;
  hired: number;
}

export interface CostDataPoint {
  date: string;
  cost: number;
  calls: number;
}

function parseErrorDetail(body: Record<string, unknown>): string {
  if (!body.detail) return '';
  if (typeof body.detail === 'string') return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail
      .map((d: { msg?: string }) => d.msg || '')
      .filter(Boolean)
      .join('; ');
  }
  return JSON.stringify(body.detail);
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      const detail = parseErrorDetail(body);
      if (detail) message = detail;
    } catch {
      // response body was not JSON
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export async function matchCandidates(
  job: JobDescription,
  limit: number,
  useRouting: boolean
): Promise<MatchResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    use_routing: String(useRouting),
  });
  const response = await fetch(`${API_URL}/api/v1/match?${params}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(job),
  });
  return handleResponse<MatchResponse>(response);
}

export async function submitFeedback(
  matchId: string,
  candidateId: string,
  feedbackType: FeedbackType,
  notes?: string
): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      match_id: matchId,
      candidate_id: candidateId,
      feedback_type: feedbackType,
      notes,
    }),
  });
  if (!response.ok) {
    let message = `Feedback submission failed with status ${response.status}`;
    try {
      const body = await response.json();
      const detail = parseErrorDetail(body);
      if (detail) message = detail;
    } catch {
      // response body was not JSON
    }
    throw new Error(message);
  }
}

export async function getAnalytics(): Promise<Analytics> {
  const response = await fetch(`${API_URL}/api/v1/analytics`);
  return handleResponse<Analytics>(response);
}

export async function getCostHistory(days: number = 30): Promise<CostDataPoint[]> {
  const response = await fetch(`${API_URL}/api/v1/analytics/costs?days=${days}`);
  return handleResponse<CostDataPoint[]>(response);
}
