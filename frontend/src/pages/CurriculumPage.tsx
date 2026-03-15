import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Calendar,
  GraduationCap,
  Filter,
  BarChart3,
} from 'lucide-react';
import type {
  CurriculumEvent,
  StudentProgress,
  CompetencyLevel,
} from '../types/curriculum';
import { COMPETENCY_COLORS, COMPETENCY_LABELS } from '../types/curriculum';
import { CurriculumCalendar } from '../components/Curriculum/CurriculumCalendar';
import { LectureDetail } from '../components/Curriculum/LectureDetail';
import { CompetencyBadge } from '../components/Curriculum/CompetencyBadge';

const BASE = import.meta.env.VITE_API_URL || '';
const STUDENT_ID = 'default-student'; // TODO: multi-user auth

// ── API helpers ─────────────────────────────────────────────────────────

async function fetchEvents(start: string, end: string, subject?: string): Promise<CurriculumEvent[]> {
  const params = new URLSearchParams({ start, end });
  if (subject) params.set('subject', subject);
  const res = await fetch(`${BASE}/v1/curriculum/events?${params}`);
  if (!res.ok) return [];
  return res.json();
}

async function fetchProgress(eventId: string): Promise<StudentProgress> {
  const res = await fetch(`${BASE}/v1/curriculum/progress/${eventId}/${STUDENT_ID}`);
  return res.json();
}

async function saveProgress(body: StudentProgress): Promise<StudentProgress> {
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

async function fetchCompetencySummary(year?: number): Promise<Record<string, number>> {
  const params = year ? `?year=${year}` : '';
  const res = await fetch(`${BASE}/v1/curriculum/competency/${STUDENT_ID}${params}`);
  if (!res.ok) return {};
  return res.json();
}

// ── Helpers ─────────────────────────────────────────────────────────────

function toISO(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function weekSunday(d: Date): Date {
  const r = new Date(d);
  r.setDate(r.getDate() - r.getDay());
  return r;
}

function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

// ── Page Component ──────────────────────────────────────────────────────

export function CurriculumPage() {
  // State
  const [weekStart, setWeekStart] = useState<Date>(() => weekSunday(new Date()));
  const [events, setEvents] = useState<CurriculumEvent[]>([]);
  const [progressMap, setProgressMap] = useState<Record<string, StudentProgress>>({});
  const [subjects, setSubjects] = useState<string[]>([]);
  const [selectedSubject, setSelectedSubject] = useState<string>('');
  const [selectedYear, setSelectedYear] = useState<number>(0); // 0 = all
  const [detailEvent, setDetailEvent] = useState<CurriculumEvent | null>(null);
  const [detailProgress, setDetailProgress] = useState<StudentProgress | null>(null);
  const [competencySummary, setCompetencySummary] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);

  // Load subjects on mount
  useEffect(() => {
    fetchSubjects().then(setSubjects).catch(() => {});
  }, []);

  // Load events whenever week / filters change
  useEffect(() => {
    const start = toISO(weekStart);
    const end = toISO(addDays(weekStart, 6));
    setLoading(true);
    fetchEvents(start, end, selectedSubject || undefined)
      .then(async (evts) => {
        // Filter by year if selected
        const filtered = selectedYear > 0 ? evts.filter((e) => e.year === selectedYear) : evts;
        setEvents(filtered);

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
        setProgressMap(map);
      })
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, [weekStart, selectedSubject, selectedYear]);

  // Competency summary
  useEffect(() => {
    fetchCompetencySummary(selectedYear || undefined).then(setCompetencySummary).catch(() => {});
  }, [selectedYear, progressMap]);

  // Event detail (double-click)
  const openDetail = useCallback(async (ev: CurriculumEvent) => {
    setDetailEvent(ev);
    const p = await fetchProgress(ev.id).catch(() => null);
    setDetailProgress(
      p ?? {
        event_id: ev.id,
        student_id: STUDENT_ID,
        attended: false,
        lecture_listened: false,
        assignment_completed: false,
        quiz_score: null,
        exam_score: null,
        competency_level: 'none' as CompetencyLevel,
        experiential_notes: '',
        updated_at: null,
        xapi_statements: [],
      },
    );
  }, []);

  const handleSaveProgress = useCallback(async (p: StudentProgress) => {
    const saved = await saveProgress(p);
    setProgressMap((prev) => ({ ...prev, [saved.event_id]: saved }));
    setDetailEvent(null);
    setDetailProgress(null);
  }, []);

  // Competency bars
  const compBars = useMemo(() => {
    const levels: CompetencyLevel[] = ['green', 'yellow', 'red', 'none'];
    const total = Object.values(competencySummary).reduce((a, b) => a + b, 0) || 1;
    return levels.map((lvl) => ({
      level: lvl,
      count: competencySummary[lvl] ?? 0,
      pct: Math.round(((competencySummary[lvl] ?? 0) / total) * 100),
    }));
  }, [competencySummary]);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top bar: title + filters + competency summary */}
      <div
        className="shrink-0 px-5 py-4"
        style={{
          background: 'var(--color-surface)',
          borderBottom: '1px solid var(--color-border)',
        }}
      >
        <div className="flex items-center justify-between mb-3">
          <h1
            className="text-base font-bold flex items-center gap-2"
            style={{ color: 'var(--color-text)' }}
          >
            <GraduationCap size={20} style={{ color: 'var(--color-accent)' }} />
            Medical School Curriculum
          </h1>

          {/* Filters */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              <Filter size={12} style={{ color: 'var(--color-text-tertiary)' }} />
              <select
                className="text-xs rounded-md px-2 py-1"
                style={{
                  background: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text)',
                }}
                value={selectedYear}
                onChange={(e) => setSelectedYear(Number(e.target.value))}
              >
                <option value={0}>All Years</option>
                <option value={1}>M1</option>
                <option value={2}>M2</option>
                <option value={3}>M3</option>
                <option value={4}>M4</option>
              </select>
            </div>
            <select
              className="text-xs rounded-md px-2 py-1"
              style={{
                background: 'var(--color-bg-secondary)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text)',
              }}
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value)}
            >
              <option value="">All Subjects</option>
              {subjects.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Competency summary bar */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1 text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
            <BarChart3 size={12} />
            <span>Competency:</span>
          </div>
          <div className="flex-1 flex h-3 rounded-full overflow-hidden" style={{ background: 'var(--color-bg-secondary)' }}>
            {compBars.map((bar) =>
              bar.pct > 0 ? (
                <div
                  key={bar.level}
                  style={{
                    width: `${bar.pct}%`,
                    background: COMPETENCY_COLORS[bar.level],
                  }}
                  title={`${COMPETENCY_LABELS[bar.level]}: ${bar.count} (${bar.pct}%)`}
                />
              ) : null,
            )}
          </div>
          <div className="flex items-center gap-2">
            {compBars.map((bar) => (
              <span key={bar.level} className="flex items-center gap-1 text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                <span
                  className="inline-block rounded-full"
                  style={{ width: 8, height: 8, background: COMPETENCY_COLORS[bar.level] }}
                />
                {bar.count}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Calendar body */}
      <div className="flex-1 overflow-hidden">
        {loading ? (
          <div
            className="flex items-center justify-center h-full text-sm"
            style={{ color: 'var(--color-text-tertiary)' }}
          >
            Loading curriculum...
          </div>
        ) : (
          <CurriculumCalendar
            events={events}
            progressMap={progressMap}
            onEventOpen={openDetail}
            weekStart={weekStart}
            onWeekChange={setWeekStart}
          />
        )}
      </div>

      {/* Detail modal */}
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
