'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CandidateCard } from '@/components/candidate-card';
import { Download, Users, Clock, Search } from 'lucide-react';
import type { MatchResponse } from '@/lib/api';
import type { FeedbackType } from '@/lib/types';

interface MatchResultsProps {
  results: MatchResponse | null;
  onFeedback: (candidateId: string, type: FeedbackType) => void;
}

export function MatchResults({
  results,
  onFeedback,
}: MatchResultsProps) {
  if (!results) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
        <Search className="mb-4 size-12 text-muted-foreground/30" />
        <h3 className="text-lg font-medium text-muted-foreground">
          Ready to match
        </h3>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground/70">
          Enter a job description and click &quot;Find Matching
          Candidates&quot; to see ranked physician matches with detailed
          scoring.
        </p>
      </div>
    );
  }

  function handleExportCSV() {
    if (!results) return;
    const headers = [
      'Rank',
      'Name',
      'Match Score',
      'Summary',
      'Strengths',
      'Gaps',
    ];
    function esc(val: unknown): string {
      const s = String(val ?? '');
      if (s.includes(',') || s.includes('"') || s.includes('\n')) {
        return `"${s.replace(/"/g, '""')}"`;
      }
      return s;
    }
    const rows = results.matches.map((m) => [
      esc(m.rank),
      esc(m.candidate_name),
      esc(Math.round(m.overall_score)),
      esc(m.summary),
      esc(m.strengths.join('; ')),
      esc(m.gaps.join('; ')),
    ]);
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join(
      '\n'
    );
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `matches-${results.job_title.replace(/\s+/g, '-')}.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 200);
  }

  const strongMatches = results.matches.filter(
    (m) => m.overall_score >= 75
  ).length;

  return (
    <div className="flex flex-col gap-6">
      {/* Recruiter-facing summary bar */}
      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="flex items-center gap-3 py-4">
            <div className="flex size-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
              <Users className="size-5" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">
                Candidates Evaluated
              </p>
              <p className="text-xl font-semibold tabular-nums">
                {results.total_candidates}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 py-4">
            <div className="flex size-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
              <Search className="size-5" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Strong Matches</p>
              <p className="text-xl font-semibold tabular-nums">
                {strongMatches}{' '}
                <span className="text-sm font-normal text-muted-foreground">
                  of {results.matches.length}
                </span>
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 py-4">
            <div className="flex size-10 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
              <Clock className="size-5" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Analysis Time</p>
              <p className="text-xl font-semibold tabular-nums">
                {(results.processing_time_ms / 1000).toFixed(1)}
                <span className="text-sm font-normal text-muted-foreground">
                  {' '}
                  sec
                </span>
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Results header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">
            Results for &quot;{results.job_title}&quot;
          </h2>
          <p className="text-sm text-muted-foreground">
            Ranked by overall match score across 6 evaluation criteria
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleExportCSV}>
          <Download className="mr-1.5 size-3.5" />
          Export CSV
        </Button>
      </div>

      {/* Candidate cards */}
      {results.matches.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
          <Search className="mb-3 size-10 text-muted-foreground/30" />
          <h3 className="text-base font-medium text-muted-foreground">
            No matching candidates found
          </h3>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground/70">
            Try broadening the requirements, changing the specialty, or
            adjusting the experience level.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {results.matches.map((candidate) => (
            <CandidateCard
              key={candidate.candidate_id}
              candidate={candidate}
              onFeedback={onFeedback}
              feedbackDisabled={false}
            />
          ))}
        </div>
      )}
    </div>
  );
}
