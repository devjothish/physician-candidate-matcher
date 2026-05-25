import { useQuery } from '@tanstack/react-query';
import { getAnalytics, getCostHistory, type Analytics, type CostDataPoint } from '@/lib/api';

export function useAnalytics() {
  const analyticsQuery = useQuery<Analytics, Error>({
    queryKey: ['analytics'],
    queryFn: getAnalytics,
    refetchInterval: 30_000,
  });

  const costQuery = useQuery<CostDataPoint[], Error>({
    queryKey: ['cost-history'],
    queryFn: () => getCostHistory(30),
    refetchInterval: 60_000,
  });

  return {
    analytics: analyticsQuery.data,
    costHistory: costQuery.data,
    isLoading: analyticsQuery.isLoading || costQuery.isLoading,
    error: analyticsQuery.error || costQuery.error,
  };
}
