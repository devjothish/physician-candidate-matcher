'use client';

import { toast } from 'sonner';
import { JobForm } from '@/components/job-form';
import { MatchResults } from '@/components/match-results';
import { useMatch } from '@/hooks/use-match';
import { submitFeedback } from '@/lib/api';
import type { JobDescription } from '@/lib/api';
import type { FeedbackType } from '@/lib/types';

export default function MatchPage() {
  const mutation = useMatch();
  const results = mutation.data ?? mutation.cachedResult ?? null;

  function handleSubmit(
    job: JobDescription,
    limit: number,
    useRouting: boolean
  ) {
    mutation.mutate(
      { job, limit, useRouting },
      {
        onSuccess: (data) => {
          toast.success(
            `Found ${data.matches.length} matches from ${data.total_candidates} candidates`
          );
        },
        onError: (error) => {
          toast.error('Matching failed', {
            description: error.message,
          });
        },
      }
    );
  }

  async function handleFeedback(matchId: string, candidateId: string, type: FeedbackType) {
    if (!results) return;
    try {
      await submitFeedback(matchId, candidateId, type);
      toast.success('Feedback recorded');
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to submit feedback';
      toast.error('Feedback failed', { description: message });
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Candidate Matching
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Enter a job description to find and score matching physician
          candidates.
        </p>
      </div>
      <div className="grid gap-8 lg:grid-cols-[380px_1fr]">
        <aside>
          <JobForm onSubmit={handleSubmit} isLoading={mutation.isPending} />
        </aside>
        <section aria-label="Match results">
          <MatchResults
            results={results}
            onFeedback={handleFeedback}
          />
        </section>
      </div>
    </div>
  );
}
