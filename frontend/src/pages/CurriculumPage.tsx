import { useState, useEffect, useCallback, useMemo } from 'react';
import { GraduationCap, BarChart3 } from 'lucide-react';
import type {
  CurriculumEvent,
  StudentProgress,
  CurriculumFilters,
  ColorLevel,
} from '../types/curriculum';
import { COMPETENCY_COLORS, COMPETENCY_LABELS, EXPOSURE_COLORS, EXPOSURE_LABELS } from '../types/curriculum';
import { CurriculumCalendar } from '../components/Curriculum/CurriculumCalendar';
import { LectureDetail } from '../components/Curriculum/LectureDetail';
import { LeftRail } from '../components/Curriculum/LeftRail';
import { RightDetailPane } from '../components/Curriculum/RightDetailPane';

const BASE = import.meta.env.VITE_API_URL || '';
const STUDENT_ID = 'default-student';

// ── API helpers ─────────────────────────────────────────────────────────

async function fetchEvents(start: string, end: string, filters: CurriculumFilters): Promise<CurriculumEvent[]> {
  const params = new URLSearchParams({ start, end });
  if (filters.subject) params.set('subject', filters.subject);
  if (filters.block) params.set('block', filters.block);
  if (filters.course) params.set('course', filters.course);
  const res = await fetch(`${BASE}/v1/curriculum/events?${params}`);
  if (!res.ok) return [];
  return res.json();
}

async function fetchProgress(eventId: string): Promise<StudentProgress> {
  const res = await fetch(`${BASE}/v1/curriculum/progress/${eventId}/${STUDENT_ID}`);
  return res.json();
}

async function saveProgressAPI(body: StudentProgress): Promise<StudentProgress> {
  const res = await fetch(`${BASE}/v1/curriculum/progress`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...body, student_id: STUDENT_ID }),
  });
  return res.json();
}

async function fetchSubjects(): Promise<string[]> {
  const res = await fetch(`${BASE}/v1/curriculum/subjects`);
  if (!res.ok) return [];
  return res.json();
}

async function fetchBlocks(): Promise<string[]> {
  const res = await fetch(`${BASE}/v1/curriculum/blocks`);
  if (!res.ok) return [];
  return res.json();
}

async function fetchCourses(): Promise<string[]> {
  const res = await fetch(`${BASE}/v1/curriculum/courses`);
  if (!res.ok) return [];
  return res.json();
}

async function fetchStaleCount(): Promise<number> {
  const res = await fetch(`${BASE}/v1/curriculum/competency/${STUDENT_ID}/stale`);
  if (!res.ok) return 0;
  const data = await res.json();
  return Array.isArray(data) ? data.length : 0;
}

async function fetchCompetencySummary(year?: number): Promise<Record<string, number>> {
  const params = year ? `?year=${year}` : '';
  const res = await fetch(`${BASE}/v1/curriculum/competency/${STUDENT_ID}${params}`);
  if (!res.ok) return {};
  return res.json();
}

// ── Helpers ─────────────────────────────────────────────────────────────

function toISO(d: Date): string { return d.toISOString().slice(0, 10); }
function weekSunday(d: Date): Date { const r = new Date(d); r.setDate(r.getDate() - r.getDay()); return r; }
function addDays(d: Date, n: number): Date { const r = new Date(d); r.setDate(r.getDate() + n); return r; }

const DEFAULT_FILTERS: CurriculumFilters = {
  year: 0,
  subject: '',
  block: '',
  course: '',
  exposureFilter: '',
  competencyFilter: '',
  showOnlyIncomplete: false,
  showOnlyStale: false,
};

// ── Page ────────────────────────────────────────────────────────────────

export function CurriculumPage() {
  const [weekStart, setWeekStart] = useState<Date>(() => weekSunday(new Date()));
  const [events, setEvents] = useState<CurriculumEvent[]>([]);
  const [progressMap, setProgressMap] = useState<Record<string, StudentProgress>>({});
  const [filters, setFilters] = useState<CurriculumFilters>(DEFAULT_FILTERS);
  const [subjects, setSubjects] = useState<string[]>([]);
  const [blocks, setBlocks] = useState<string[]>([]);
  const [courses, setCourses] = useState<string[]>([]);
  const [staleCounts, setStaleCounts] = useState(0);
  const [selectedEvent, setSelectedEvent] = useState<CurriculumEvent | null>(null);
  const [selectedProgress, setSelectedProgress] = useState<StudentProgress | null>(null);
  const [detailEvent, setDetailEvent] = useState<CurriculumEvent | null>(null);
  const [detailProgress, setDetailProgress] = useState<StudentProgress | null>(null);
  const [loading, setLoading] = useState(false);
  const [competencySummary, setCompetencySummary] = useState<Record<string, number>>({});

  // Load metadata on mount
  useEffect(() => {
    fetchSubjects().then(setSubjects).catch(() => {});
    fetchBlocks().then(setBlocks).catch(() => {});
    fetchCourses().then(setCourses).catch(() => {});
    fetchStaleCount().then(setStaleCounts).catch(() => {});
  }, []);

  // Load events when week / filters change
  useEffect(() => {
    const start = toISO(weekStart);
    const end = toISO(addDays(weekStart, 6));
    setLoading(true);
    fetchEvents(start, end, filters)
      .then(async (evts) => {
        let filtered = evts;
        if (filters.year > 0) filtered = filtered.filter((e) => e.year === filters.year);

        // Fetch progress for all events
        const progEntries = await Promise.all(
          filtered.map(async (ev) => {
            const p = await fetchProgress(ev.id).catch(() => null);
            return p ? [ev.id, p] as const : null;
          }),
        );
        const map: Record<string, StudentProgress> = {};
        for (const entry of progEntries) {
          if (entry) map[entry[0]] = entry[1];
        }

        // Apply exposure/competency filters
        if (filters.exposureFilter) {
          filtered = filtered.filter((ev) => map[ev.id]?.exposure_level === filters.exposureFilter);
        }
        if (filters.competencyFilter) {
          filtered = filtered.filter((ev) => map[ev.id]?.competency_level === filters.competencyFilter);
        }
        if (filters.showOnlyIncomplete) {
          filtered = filtered.filter((ev) => {
            const p = map[ev.id];
            return !p || !p.attended || !p.assignment_completed;
          });
        }

        setEvents(filtered);
        setProgressMap(map);
      })
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, [weekStart, filters]);

  // Competency summary
  useEffect(() => {
    fetchCompetencySummary(filters.year || undefined).then(setCompetencySummary).catch(() => {});
  }, [filters.year, progressMap]);

  // Single click → right pane
  const handleEventSelect = useCallback(async (ev: CurriculumEvent) => {
    setSelectedEvent(ev);
    const p = progressMap[ev.id] || await fetchProgress(ev.id).catch(() => null);
    setSelectedProgress(p);
  }, [progressMap]);

  // Double click → modal
  const handleEventOpen = useCallback(async (ev: CurriculumEvent) => {
    setDetailEvent(ev);
    const p = progressMap[ev.id] || await fetchProgress(ev.id).catch(() => null);
    setDetailProgress(
      p ?? {
        event_id: ev.id,
        student_id: STUDENT_ID,
        attended: false,
        lecture_listened: false,
        recording_watched: false,
        assignment_completed: false,
        reading_completed: false,
        simulation_completed: false,
        patient_encounter_logged: false,
        quiz_score: null,
        exam_score: null,
        osce_score: null,
        faculty_observation: null,
        exposure_level: 'none' as ColorLevel,
        competency_level: 'none' as ColorLevel,
        experiential_notes: '',
        clinical_encounters: [],
        updated_at: null,
        xapi_statements: [],
      },
    );
  }, [progressMap]);

  const handleSaveProgress = useCallback(async (p: StudentProgress) => {
    const saved = await saveProgressAPI(p);
    setProgressMap((prev) => ({ ...prev, [saved.event_id]: saved }));
    setDetailEvent(null);
    setDetailProgress(null);
    // Refresh stale count
    fetchStaleCount().then(setStaleCounts).catch(() => {});
  }, []);

  const handleFilterChange = useCallback((partial: Partial<CurriculumFilters>) => {
    setFilters((f) => ({ ...f, ...partial }));
  }, []);

  // Summary bars
  const compSummary = useMemo(() => {
    const combined = (competencySummary as any)?.combined;
    if (!Array.isArray(combined)) return { exposure: {}, competency: {} };
    const exp: Record<string, number> = {};
    const comp: Record<string, number> = {};
    for (const entry of combined) {
      exp[entry.exposure] = (exp[entry.exposure] || 0) + entry.count;
      comp[entry.competency] = (comp[entry.competency] || 0) + entry.count;
    }
    return { exposure: exp, competency: comp };
  }, [competencySummary]);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top bar */}
      <div
        className="shrink-0 px-5 py-3"
        style={{ background: 'var(--color-surface)', borderBottom: '1px solid var(--color-border)' }}
      >
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--color-text)' }}>
            <GraduationCap size={20} style={{ color: 'var(--color-accent)' }} />
            Medical School Curriculum
          </h1>
        </div>

        {/* Dual competency bars */}
        <div className="flex items-center gap-4">
          <SummaryBar label="Exposure" data={compSummary.exposure} colors={EXPOSURE_COLORS} labels={EXPOSURE_LABELS} />
          <SummaryBar label="Competency" data={compSummary.competency} colors={COMPETENCY_COLORS} labels={COMPETENCY_LABELS} />
        </div>
      </div>

      {/* Three-pane layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left rail: filters */}
        <LeftRail
          filters={filters}
          onChange={handleFilterChange}
          subjects={subjects}
          blocks={blocks}
          courses={courses}
          staleCounts={staleCounts}
        />

        {/* Center: calendar */}
        <div className="flex-1 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center h-full text-sm" style={{ color: 'var(--color-text-tertiary)' }}>
              Loading curriculum...
            </div>
          ) : (
            <CurriculumCalendar
              events={events}
              progressMap={progressMap}
              selectedEventId={selectedEvent?.id ?? null}
              onEventSelect={handleEventSelect}
              onEventOpen={handleEventOpen}
              weekStart={weekStart}
              onWeekChange={setWeekStart}
            />
          )}
        </div>

        {/* Right pane: detail */}
        <RightDetailPane
          event={selectedEvent}
          progress={selectedProgress}
          studentId={STUDENT_ID}
        />
      </div>

      {/* Modal */}
      {detailEvent && detailProgress && (
        <LectureDetail
          event={detailEvent}
          progress={detailProgress}
          onClose={() => { setDetailEvent(null); setDetailProgress(null); }}
          onSave={handleSaveProgress}
        />
      )}
    </div>
  );
}

// ── Summary Bar ─────────────────────────────────────────────────────────

function SummaryBar({
  label,
  data,
  colors,
  labels: levelLabels,
}: {
  label: string;
  data: Record<string, number>;
  colors: Record<ColorLevel, string>;
  labels: Record<ColorLevel, string>;
}) {
  const levels: ColorLevel[] = ['green', 'yellow', 'red', 'none'];
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="flex-1 flex items-center gap-2">
      <span className="text-xs flex items-center gap-1 shrink-0" style={{ color: 'var(--color-text-tertiary)', width: 80 }}>
        <BarChart3 size={10} /> {label}
      </span>
      <div className="flex-1 flex h-2.5 rounded-full overflow-hidden" style={{ background: 'var(--color-bg-secondary)' }}>
        {levels.map((lvl) => {
          const count = data[lvl] || 0;
          const pct = Math.round((count / total) * 100);
          return pct > 0 ? (
            <div
              key={lvl}
              style={{ width: `${pct}%`, background: colors[lvl] }}
              title={`${levelLabels[lvl]}: ${count} (${pct}%)`}
            />
          ) : null;
        })}
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        {levels.map((lvl) => (
          <span key={lvl} className="flex items-center gap-0.5 text-xs" style={{ color: 'var(--color-text-tertiary)', fontSize: 10 }}>
            <span className="rounded-full" style={{ width: 6, height: 6, background: colors[lvl] }} />
            {data[lvl] || 0}
          </span>
        ))}
      </div>
    </div>
  );
}
