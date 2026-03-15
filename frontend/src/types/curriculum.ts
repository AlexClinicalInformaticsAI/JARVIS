// ── AAMC Competency Domains ─────────────────────────────────────────────

export type AAMCDomain =
  | 'professionalism'
  | 'patient_care_and_procedural_skills'
  | 'medical_knowledge'
  | 'practice_based_learning_and_improvement'
  | 'interpersonal_and_communication_skills'
  | 'systems_based_practice';

export const AAMC_DOMAIN_LABELS: Record<AAMCDomain, string> = {
  professionalism: 'Professionalism',
  patient_care_and_procedural_skills: 'Patient Care',
  medical_knowledge: 'Medical Knowledge',
  practice_based_learning_and_improvement: 'Practice-Based Learning',
  interpersonal_and_communication_skills: 'Communication',
  systems_based_practice: 'Systems-Based Practice',
};

// ── Dual-layer R/Y/G ────────────────────────────────────────────────────
// Exposure ≠ Competency. A student can be green exposure + red competency.

export type ColorLevel = 'none' | 'red' | 'yellow' | 'green';

export const EXPOSURE_COLORS: Record<ColorLevel, string> = {
  none: 'var(--color-text-tertiary)',
  red: '#ef4444',
  yellow: '#eab308',
  green: '#22c55e',
};

export const EXPOSURE_LABELS: Record<ColorLevel, string> = {
  none: 'Not Encountered',
  red: 'Minimal Exposure',
  yellow: 'Partial Exposure',
  green: 'Full Exposure',
};

export const COMPETENCY_COLORS: Record<ColorLevel, string> = {
  none: 'var(--color-text-tertiary)',
  red: '#ef4444',
  yellow: '#eab308',
  green: '#22c55e',
};

export const COMPETENCY_LABELS: Record<ColorLevel, string> = {
  none: 'Not Assessed',
  red: 'Below Expected',
  yellow: 'Developing',
  green: 'Competent',
};

// ── Objective lifecycle stages ──────────────────────────────────────────

export type ObjectiveStage =
  | 'not_started'
  | 'introduced'
  | 'revisited'
  | 'practised'
  | 'assessed'
  | 'applied'
  | 'mastered'
  | 'revalidated'
  | 'stale';

export const STAGE_LABELS: Record<ObjectiveStage, string> = {
  not_started: 'Not Started',
  introduced: 'Introduced',
  revisited: 'Revisited',
  practised: 'Practised',
  assessed: 'Assessed',
  applied: 'Applied',
  mastered: 'Mastered',
  revalidated: 'Revalidated',
  stale: 'Stale',
};

export const STAGE_COLORS: Record<ObjectiveStage, string> = {
  not_started: '#6b7280',
  introduced: '#3b82f6',
  revisited: '#8b5cf6',
  practised: '#f59e0b',
  assessed: '#f97316',
  applied: '#06b6d4',
  mastered: '#22c55e',
  revalidated: '#10b981',
  stale: '#ef4444',
};

// ── Event types ─────────────────────────────────────────────────────────

export type EventType =
  | 'lecture'
  | 'lab'
  | 'clinical'
  | 'small_group'
  | 'simulation'
  | 'exam'
  | 'quiz'
  | 'assignment'
  | 'self_study'
  | 'osce'
  | 'patient_encounter'
  | 'reflection';

export const EVENT_TYPE_COLORS: Record<EventType, string> = {
  lecture: '#3b82f6',
  lab: '#8b5cf6',
  clinical: '#06b6d4',
  small_group: '#f59e0b',
  simulation: '#ec4899',
  exam: '#ef4444',
  quiz: '#f97316',
  assignment: '#10b981',
  self_study: '#6b7280',
  osce: '#dc2626',
  patient_encounter: '#0891b2',
  reflection: '#a855f7',
};

export const EVENT_TYPE_LABELS: Record<EventType, string> = {
  lecture: 'Lecture',
  lab: 'Lab',
  clinical: 'Clinical',
  small_group: 'Small Group',
  simulation: 'Simulation',
  exam: 'Exam',
  quiz: 'Quiz',
  assignment: 'Assignment',
  self_study: 'Self Study',
  osce: 'OSCE',
  patient_encounter: 'Patient Encounter',
  reflection: 'Reflection',
};

// ── Learning Objective ──────────────────────────────────────────────────

export interface LearningObjective {
  id: string;
  description: string;
  aamc_domain: AAMCDomain;
  bloom_level: string;
  epa_mapping: string | null;
  tags: string[];
  aamc_ci_keywords: string[];
}

// ── Curriculum Event ────────────────────────────────────────────────────

export interface CurriculumEvent {
  id: string;
  title: string;
  event_type: EventType;
  subject: string;
  topic: string;
  date: string;
  start_time: string;
  end_time: string;
  year: number;
  block: string;
  course: string;
  clerkship: string;
  location: string;
  instructor: string;
  description: string;
  learning_objectives: LearningObjective[];
  prerequisites: string[];
  resources: string[];
  recording_url: string;
  metadata: Record<string, unknown>;
}

// ── Student Progress (dual-layer) ───────────────────────────────────────

export interface StudentProgress {
  event_id: string;
  student_id: string;
  // engagement
  attended: boolean;
  lecture_listened: boolean;
  recording_watched: boolean;
  assignment_completed: boolean;
  reading_completed: boolean;
  simulation_completed: boolean;
  patient_encounter_logged: boolean;
  // assessment
  quiz_score: number | null;
  exam_score: number | null;
  osce_score: number | null;
  faculty_observation: string | null;
  // dual R/Y/G
  exposure_level: ColorLevel;
  competency_level: ColorLevel;
  // experiential
  experiential_notes: string;
  clinical_encounters: Record<string, unknown>[];
  // meta
  updated_at: string | null;
  xapi_statements: Record<string, unknown>[];
}

// ── Longitudinal Objective Progress ─────────────────────────────────────

export interface ObjectiveProgressData {
  objective_id: string;
  student_id: string;
  stage: ObjectiveStage;
  exposure_level: ColorLevel;
  competency_level: ColorLevel;
  encounter_count: number;
  modalities_seen: string[];
  first_exposure: string | null;
  last_exposure: string | null;
  last_assessed: string | null;
  last_applied: string | null;
  assessment_scores: number[];
  trend: 'improving' | 'stable' | 'declining' | 'stale';
  days_since_last_exposure: number | null;
  recommended_action: string;
}

// ── Filter state ────────────────────────────────────────────────────────

export interface CurriculumFilters {
  year: number;           // 0 = all
  subject: string;        // '' = all
  block: string;          // '' = all
  course: string;         // '' = all
  exposureFilter: ColorLevel | '';  // '' = all
  competencyFilter: ColorLevel | ''; // '' = all
  showOnlyIncomplete: boolean;
  showOnlyStale: boolean;
}
