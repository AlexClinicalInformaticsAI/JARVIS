// ── AAMC Competency Domains ─────────────────────────────────────────────

export type AAMCDomain =
  | 'professionalism'
  | 'patient_care_and_procedural_skills'
  | 'medical_knowledge'
  | 'practice_based_learning_and_improvement'
  | 'interpersonal_and_communication_skills'
  | 'systems_based_practice';

// ── Competency Levels (R / Y / G) ──────────────────────────────────────

export type CompetencyLevel = 'none' | 'red' | 'yellow' | 'green';

export const COMPETENCY_COLORS: Record<CompetencyLevel, string> = {
  none: 'var(--color-text-tertiary)',
  red: '#ef4444',
  yellow: '#eab308',
  green: '#22c55e',
};

export const COMPETENCY_LABELS: Record<CompetencyLevel, string> = {
  none: 'Not Started',
  red: 'Exposure',
  yellow: 'Practice',
  green: 'Competency',
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
  | 'self_study';

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
};

// ── Learning Objective ──────────────────────────────────────────────────

export interface LearningObjective {
  id: string;
  description: string;
  aamc_domain: AAMCDomain;
  bloom_level: string;
  epa_mapping: string | null;
  tags: string[];
}

// ── Curriculum Event ────────────────────────────────────────────────────

export interface CurriculumEvent {
  id: string;
  title: string;
  event_type: EventType;
  subject: string;
  topic: string;
  date: string;           // ISO date
  start_time: string;     // HH:MM:SS
  end_time: string;       // HH:MM:SS
  year: number;           // M1=1, M2=2, M3=3, M4=4
  block: string;
  location: string;
  instructor: string;
  description: string;
  learning_objectives: LearningObjective[];
  prerequisites: string[];
  resources: string[];
  metadata: Record<string, unknown>;
}

// ── Student Progress ────────────────────────────────────────────────────

export interface StudentProgress {
  event_id: string;
  student_id: string;
  attended: boolean;
  lecture_listened: boolean;
  assignment_completed: boolean;
  quiz_score: number | null;
  exam_score: number | null;
  competency_level: CompetencyLevel;
  experiential_notes: string;
  updated_at: string | null;
  xapi_statements: Record<string, unknown>[];
}

// ── Calendar view helpers ───────────────────────────────────────────────

export interface DayEvents {
  date: string;            // ISO date
  dayOfWeek: number;       // 0=Sun … 6=Sat
  label: string;           // e.g. "Mon 15"
  events: CurriculumEvent[];
  progress: Map<string, StudentProgress>;
}

export interface WeekData {
  weekStart: string;       // ISO Sunday date
  days: DayEvents[];
}
