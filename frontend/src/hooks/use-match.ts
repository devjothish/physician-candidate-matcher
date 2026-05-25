import { useMutation } from '@tanstack/react-query';
import { matchCandidates, type JobDescription, type MatchResponse } from '@/lib/api';

interface MatchVariables {
  job: JobDescription;
  limit: number;
  useRouting: boolean;
}

export function useMatch() {
  return useMutation<MatchResponse, Error, MatchVariables>({
    mutationFn: ({ job, limit, useRouting }) =>
      matchCandidates(job, limit, useRouting),
  });
}
