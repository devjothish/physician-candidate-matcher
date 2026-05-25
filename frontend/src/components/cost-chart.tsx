'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { CostDataPoint } from '@/lib/api';

interface CostChartProps {
  data: CostDataPoint[];
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

interface TooltipPayloadItem {
  value: number;
  payload: CostDataPoint;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const item = payload[0];
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-sm shadow-md">
      <p className="font-medium">{label}</p>
      <p className="text-muted-foreground">
        Cost: ${item.value.toFixed(4)}
      </p>
      <p className="text-muted-foreground">
        Calls: {item.payload.calls}
      </p>
    </div>
  );
}

export function CostChart({ data }: CostChartProps) {
  const formatted = data.map((d) => ({
    ...d,
    dateLabel: formatDate(d.date),
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cost Over Time</CardTitle>
      </CardHeader>
      <CardContent>
        {formatted.length === 0 ? (
          <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
            No cost data available yet.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart
              data={formatted}
              margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="dateLabel"
                tick={{ fontSize: 12 }}
                className="text-muted-foreground"
              />
              <YAxis
                tick={{ fontSize: 12 }}
                className="text-muted-foreground"
                tickFormatter={(v: number) => `$${v.toFixed(2)}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="cost"
                stroke="oklch(0.488 0.243 264.376)"
                strokeWidth={2}
                dot={{ r: 3, fill: 'oklch(0.488 0.243 264.376)' }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
