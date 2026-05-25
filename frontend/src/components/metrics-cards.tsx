'use client';

import { Card, CardContent } from '@/components/ui/card';
import {
  Activity,
  DollarSign,
  Clock,
  ThumbsUp,
  ThumbsDown,
  UserCheck,
} from 'lucide-react';
import type { Analytics } from '@/lib/api';

interface MetricsCardsProps {
  analytics: Analytics;
}

export function MetricsCards({ analytics }: MetricsCardsProps) {
  const good = analytics.good_matches ?? 0;
  const bad = analytics.bad_matches ?? 0;
  const totalFeedback = good + bad;
  const goodRatio =
    totalFeedback > 0
      ? ((good / totalFeedback) * 100).toFixed(0)
      : '--';

  const cards = [
    {
      label: 'Total Matches',
      value: (analytics.total_matches ?? 0).toLocaleString(),
      icon: Activity,
      iconBg: 'bg-blue-50 text-blue-600',
    },
    {
      label: 'Total Cost',
      value: `$${(analytics.total_cost ?? 0).toFixed(2)}`,
      icon: DollarSign,
      iconBg: 'bg-emerald-50 text-emerald-600',
    },
    {
      label: 'Avg Latency',
      value: `${((analytics.avg_latency_ms ?? 0) / 1000).toFixed(1)}s`,
      icon: Clock,
      iconBg: 'bg-amber-50 text-amber-600',
    },
    {
      label: 'Good Match Rate',
      value: `${goodRatio}%`,
      subValue: `${good} good / ${bad} bad`,
      icon: totalFeedback > 0 && analytics.good_matches >= analytics.bad_matches
        ? ThumbsUp
        : ThumbsDown,
      iconBg:
        totalFeedback > 0 && analytics.good_matches >= analytics.bad_matches
          ? 'bg-emerald-50 text-emerald-600'
          : 'bg-red-50 text-red-600',
    },
    {
      label: 'Hired',
      value: (analytics.hired ?? 0).toLocaleString(),
      icon: UserCheck,
      iconBg: 'bg-purple-50 text-purple-600',
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <Card key={card.label} size="sm">
            <CardContent className="flex items-center gap-3">
              <div
                className={`flex size-10 shrink-0 items-center justify-center rounded-lg ${card.iconBg}`}
              >
                <Icon className="size-5" />
              </div>
              <div className="min-w-0">
                <p className="text-xs text-muted-foreground">{card.label}</p>
                <p className="text-xl font-semibold tabular-nums truncate">
                  {card.value}
                </p>
                {card.subValue && (
                  <p className="text-xs text-muted-foreground truncate">
                    {card.subValue}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
