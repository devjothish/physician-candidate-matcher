'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  ThumbsUp,
  ThumbsDown,
  ChevronDown,
  ChevronUp,
  MapPin,
  Briefcase,
  ShieldCheck,
  ShieldX,
  Clock,
} from 'lucide-react';
import type { CandidateMatch } from '@/lib/api';
import type { FeedbackType } from '@/lib/types';

interface CandidateCardProps {
  candidate: CandidateMatch;
  onFeedback: (matchId: string, candidateId: string, type: FeedbackType) => void;
  feedbackDisabled: boolean;
}

const CATEGORY_LABELS: Record<string, string> = {
  specialty_match: 'Specialty Alignment',
  experience_match: 'Experience Fit',
  location_match: 'Location & Licensure',
  credentials_match: 'Board Certification',
  skills_match: 'Clinical Skills',
  availability_match: 'Availability',
};

function scoreColor(pct: number): string {
  if (pct >= 75) return 'text-emerald-700';
  if (pct >= 50) return 'text-amber-600';
  return 'text-red-600';
}

function scoreBorder(pct: number): string {
  if (pct >= 75) return 'border-emerald-400';
  if (pct >= 50) return 'border-amber-400';
  return 'border-red-400';
}

function progressColor(pct: number): string {
  if (pct >= 75) return '[&_[data-slot=progress-indicator]]:bg-emerald-600';
  if (pct >= 50) return '[&_[data-slot=progress-indicator]]:bg-amber-500';
  return '[&_[data-slot=progress-indicator]]:bg-red-500';
}

function matchLabel(score: number): string {
  if (score >= 85) return 'Strong Match';
  if (score >= 65) return 'Potential Match';
  if (score >= 45) return 'Weak Match';
  return 'Not Recommended';
}

function matchLabelColor(score: number): string {
  if (score >= 85) return 'bg-emerald-100 text-emerald-800 border-emerald-300';
  if (score >= 65) return 'bg-blue-100 text-blue-800 border-blue-300';
  if (score >= 45) return 'bg-amber-100 text-amber-800 border-amber-300';
  return 'bg-red-100 text-red-800 border-red-300';
}

export function CandidateCard({
  candidate,
  onFeedback,
  feedbackDisabled,
}: CandidateCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<FeedbackType | null>(null);

  function handleFeedback(type: FeedbackType) {
    setFeedbackGiven(type);
    onFeedback(candidate.match_id, candidate.candidate_id, type);
  }

  const overallPct = Math.round(candidate.overall_score);

  return (
    <Card className={`border-l-4 ${scoreBorder(overallPct)}`}>
      <CardContent className="flex flex-col gap-5 pt-5">
        {/* Header: rank, name, score */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2.5">
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground">
                {candidate.rank}
              </span>
              <h3 className="text-lg font-semibold tracking-tight">
                {candidate.candidate_name}
              </h3>
            </div>
            <Badge
              variant="outline"
              className={`ml-9 w-fit text-xs ${matchLabelColor(overallPct)}`}
            >
              {matchLabel(overallPct)}
            </Badge>
          </div>
          <div className="flex flex-col items-center">
            <span className={`text-3xl font-bold tabular-nums ${scoreColor(overallPct)}`}>
              {overallPct}
            </span>
            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Match Score
            </span>
          </div>
        </div>

        {/* Summary */}
        <p className="text-sm leading-relaxed text-muted-foreground">
          {candidate.summary}
        </p>

        {/* Strengths */}
        {candidate.strengths.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
              Strengths
            </span>
            <ul className="flex flex-col gap-1 pl-1">
              {candidate.strengths.map((s, i) => (
                <li key={`s-${i}`} className="flex items-start gap-2 text-sm text-foreground">
                  <ShieldCheck className="mt-0.5 size-3.5 shrink-0 text-emerald-600" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Gaps */}
        {candidate.gaps.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-red-600">
              Gaps &amp; Risks
            </span>
            <ul className="flex flex-col gap-1 pl-1">
              {candidate.gaps.map((g, i) => (
                <li key={`g-${i}`} className="flex items-start gap-2 text-sm text-foreground">
                  <ShieldX className="mt-0.5 size-3.5 shrink-0 text-red-500" />
                  {g}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Score Breakdown */}
        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
          <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted transition-colors">
            <span>Detailed Score Breakdown</span>
            {isOpen ? (
              <ChevronUp className="size-4" />
            ) : (
              <ChevronDown className="size-4" />
            )}
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="mt-3 flex flex-col gap-4 rounded-lg border bg-muted/30 p-4">
              {candidate.scores.map((score) => {
                const pct = Math.round(score.score * 100);
                const label =
                  CATEGORY_LABELS[score.category] ||
                  score.category.replace(/_/g, ' ');
                return (
                  <div key={score.category} className="flex flex-col gap-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium capitalize">{label}</span>
                      <span
                        className={`font-semibold tabular-nums ${scoreColor(pct)}`}
                      >
                        {pct}%
                      </span>
                    </div>
                    <Progress
                      value={pct}
                      className={`h-2 ${progressColor(pct)}`}
                    />
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      {score.explanation}
                    </p>
                  </div>
                );
              })}
            </div>
          </CollapsibleContent>
        </Collapsible>

        {/* Feedback */}
        <div className="flex items-center gap-2 border-t pt-3">
          <span className="mr-auto text-xs text-muted-foreground">
            {feedbackGiven
              ? 'Thank you for your feedback'
              : 'How would you rate this match?'}
          </span>
          <Button
            variant={feedbackGiven === 'good_match' ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleFeedback('good_match')}
            disabled={feedbackDisabled || feedbackGiven !== null}
            aria-label={`Rate ${candidate.candidate_name} as good match`}
          >
            <ThumbsUp className="mr-1 size-3.5" />
            Good
          </Button>
          <Button
            variant={feedbackGiven === 'bad_match' ? 'destructive' : 'outline'}
            size="sm"
            onClick={() => handleFeedback('bad_match')}
            disabled={feedbackDisabled || feedbackGiven !== null}
            aria-label={`Rate ${candidate.candidate_name} as poor match`}
          >
            <ThumbsDown className="mr-1 size-3.5" />
            Poor
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
