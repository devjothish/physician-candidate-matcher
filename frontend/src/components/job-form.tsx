'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, Send } from 'lucide-react';
import { SPECIALTIES, EMPLOYMENT_TYPES, type FormState } from '@/lib/types';
import type { JobDescription } from '@/lib/api';

interface JobFormProps {
  onSubmit: (job: JobDescription, limit: number, useRouting: boolean) => void;
  isLoading: boolean;
}

const initialState: FormState = {
  title: '',
  specialty: '',
  location: '',
  requirements: '',
  preferred_experience_years: '',
  employment_type: 'full-time',
  limit: 10,
  useRouting: true,
};

export function JobForm({ onSubmit, isLoading }: JobFormProps) {
  const [form, setForm] = useState<FormState>(initialState);

  function handleChange(
    field: keyof FormState,
    value: string | number | boolean | null
  ) {
    if (value === null) return;
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim() || !form.specialty || !form.requirements.trim()) {
      return;
    }
    const job: JobDescription = {
      title: form.title.trim(),
      specialty: form.specialty,
      location: form.location.trim(),
      requirements: form.requirements.trim(),
      preferred_experience_years: parseInt(form.preferred_experience_years, 10) || 0,
      employment_type: form.employment_type,
    };
    onSubmit(job, form.limit, form.useRouting);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Job Description</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <Label htmlFor="title">
              Job Title <span className="text-destructive">*</span>
            </Label>
            <Input
              id="title"
              placeholder="e.g. Staff Cardiologist"
              value={form.title}
              onChange={(e) => handleChange('title', e.target.value)}
              required
              aria-required="true"
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="specialty">
              Specialty <span className="text-destructive">*</span>
            </Label>
            <Select
              value={form.specialty}
              onValueChange={(val) => handleChange('specialty', val)}
            >
              <SelectTrigger id="specialty" className="w-full" aria-label="Specialty">
                <SelectValue placeholder="Select a specialty" />
              </SelectTrigger>
              <SelectContent>
                {SPECIALTIES.map((spec) => (
                  <SelectItem key={spec} value={spec}>
                    {spec}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="location">Location</Label>
            <Input
              id="location"
              placeholder="e.g. Boston, MA"
              value={form.location}
              onChange={(e) => handleChange('location', e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="requirements">
              Requirements <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="requirements"
              placeholder="Describe the position requirements, qualifications, and responsibilities..."
              rows={6}
              value={form.requirements}
              onChange={(e) => handleChange('requirements', e.target.value)}
              required
              aria-required="true"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="experience">Experience (years)</Label>
              <Input
                id="experience"
                type="number"
                min={0}
                max={50}
                placeholder="0"
                value={form.preferred_experience_years}
                onChange={(e) => handleChange('preferred_experience_years', e.target.value)}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="employment-type">Employment Type</Label>
              <Select
                value={form.employment_type}
                onValueChange={(val) => handleChange('employment_type', val)}
              >
                <SelectTrigger id="employment-type" className="w-full" aria-label="Employment type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EMPLOYMENT_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button
            type="submit"
            size="lg"
            disabled={
              isLoading ||
              !form.title.trim() ||
              !form.specialty ||
              !form.requirements.trim()
            }
            className="w-full"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Analyzing candidates...
              </>
            ) : (
              <>
                <Send className="mr-2 size-4" />
                Find Matching Candidates
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
