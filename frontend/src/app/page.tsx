import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';
import { buttonVariants } from '@/components/ui/button';
import {
  Stethoscope,
  BarChart3,
  Zap,
  Shield,
  MessageSquare,
  ArrowRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const features = [
  {
    icon: BarChart3,
    title: 'Explainable Scores',
    description:
      'Every candidate receives a transparent, multi-category score breakdown with plain-language explanations recruiters can share with hiring managers.',
  },
  {
    icon: Zap,
    title: 'Smart Model Routing',
    description:
      'Cost-efficient AI pipeline uses fast screening for initial passes and deeper analysis only for top candidates, reducing cost without sacrificing accuracy.',
  },
  {
    icon: Shield,
    title: 'Bias-Free Evaluation',
    description:
      'Structured scoring criteria focus exclusively on qualifications, experience, and skills to support fair and compliant hiring practices.',
  },
  {
    icon: MessageSquare,
    title: 'Feedback Loop',
    description:
      'Recruiter feedback on match quality feeds back into the system, enabling continuous improvement of matching accuracy over time.',
  },
];

export default function Home() {
  return (
    <div className="flex flex-col">
      <section className="border-b bg-white">
        <div className="mx-auto flex max-w-7xl flex-col items-center px-4 py-20 text-center sm:px-6 sm:py-28 lg:px-8">
          <div className="mb-6 flex size-16 items-center justify-center rounded-2xl bg-blue-50">
            <Stethoscope className="size-8 text-blue-600" />
          </div>
          <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            Physician Candidate Matcher
          </h1>
          <p className="mt-4 max-w-2xl text-lg leading-relaxed text-muted-foreground">
            AI-powered matching that scores and ranks physician candidates
            against your job descriptions. Get explainable results in seconds,
            not days.
          </p>
          <div className="mt-8 flex gap-3">
            <Link
              href="/match"
              className={cn(
                buttonVariants({ size: 'lg' }),
                'gap-1.5'
              )}
            >
              Start Matching
              <ArrowRight className="size-4" />
            </Link>
            <Link
              href="/analytics"
              className={cn(buttonVariants({ variant: 'outline', size: 'lg' }))}
            >
              View Analytics
            </Link>
          </div>
        </div>
      </section>

      <section className="py-16 sm:py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-12 text-center">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              Built for Healthcare Recruiting
            </h2>
            <p className="mt-2 text-muted-foreground">
              Purpose-built features that address the unique needs of physician
              recruitment.
            </p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <Card key={feature.title}>
                  <CardContent className="flex flex-col gap-3 pt-2">
                    <div className="flex size-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                      <Icon className="size-5" />
                    </div>
                    <h3 className="font-semibold text-foreground">
                      {feature.title}
                    </h3>
                    <p className="text-sm leading-relaxed text-muted-foreground">
                      {feature.description}
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>
    </div>
  );
}
