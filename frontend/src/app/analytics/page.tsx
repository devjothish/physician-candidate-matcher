'use client';

import { useAnalytics } from '@/hooks/use-analytics';
import { MetricsCards } from '@/components/metrics-cards';
import { CostChart } from '@/components/cost-chart';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCircle } from 'lucide-react';

function MetricsSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-24 rounded-xl" />
      ))}
    </div>
  );
}

function ChartSkeleton() {
  return <Skeleton className="h-[400px] rounded-xl" />;
}

export default function AnalyticsPage() {
  const { analytics, costHistory, isLoading, error } = useAnalytics();

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Analytics
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Monitor matching performance, costs, and recruiter feedback.
        </p>
      </div>

      {error && (
        <div className="mb-6 flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="size-4 shrink-0" />
          <p>
            Failed to load analytics data. Make sure the API server is running.
          </p>
        </div>
      )}

      <div className="flex flex-col gap-8">
        {isLoading || !analytics ? (
          <MetricsSkeleton />
        ) : (
          <MetricsCards analytics={analytics} />
        )}

        {isLoading || !costHistory ? (
          <ChartSkeleton />
        ) : (
          <CostChart data={costHistory} />
        )}
      </div>
    </div>
  );
}
