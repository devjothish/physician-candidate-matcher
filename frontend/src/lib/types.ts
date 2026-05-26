export type FeedbackType = 'good_match' | 'bad_match' | 'hired' | 'interviewed';

export interface FormState {
  title: string;
  specialty: string;
  location: string;
  requirements: string;
  preferred_experience_years: string;
  employment_type: string;
  limit: number;
  useRouting: boolean;
}

export const SPECIALTIES = [
  'Cardiology',
  'Dermatology',
  'Emergency Medicine',
  'Endocrinology',
  'Family Medicine',
  'Gastroenterology',
  'Internal Medicine',
  'Neurology',
  'Obstetrics & Gynecology',
  'Oncology',
  'Ophthalmology',
  'Orthopedics',
  'Pediatrics',
  'Psychiatry',
  'Radiology',
  'Other',
] as const;

export const EMPLOYMENT_TYPES = [
  'full-time',
  'part-time',
  'locum tenens',
  'any',
] as const;
