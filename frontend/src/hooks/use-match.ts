import { useMutation, useQueryClient } from '@tanstack/react-query';
import { matchCandidates, type JobDescription, type MatchResponse } from '@/lib/api';

interface MatchVariables {
  job: JobDescription;
  limit: number;
  useRouting: boolean;
}

const LAST_MATCH_KEY = ['last-match-result'];

export function useMatch() {
  const queryClient = useQueryClient();

  const mutation = useMutation<MatchResponse, Error, MatchVariables>({
    mutationFn: ({ job, limit, useRouting }) =>
      matchCandidates(job, limit, useRouting),
    onSuccess: (data) => {
      queryClient.setQueryData(LAST_MATCH_KEY, data);
    },
  });

  const cachedResult = queryClient.getQueryData<MatchResponse>(LAST_MATCH_KEY);

  return { ...mutation, cachedResult };
}
