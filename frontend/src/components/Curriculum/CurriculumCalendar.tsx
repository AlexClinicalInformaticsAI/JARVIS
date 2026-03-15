import { useState, useMemo, useCallback } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { CurriculumEvent, StudentProgress, CompetencyLevel } from '../../types/curriculum';
import { COMPETENCY_COLORS } from '../../types/curriculum';
import { LectureCard } from './LectureCard';

interface Props {
  events: CurriculumEvent[];
  progressMap: Record<string, StudentProgress>;
  onEventOpen: (event: CurriculumEvent) => void;
  weekStart: Date;
  onWeekChange: (newStart: Date) => void;
}

const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const DAY_SHORT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function toISO(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

/** Compute the Sunday that starts the week containing *d*. */
function weekSunday(d: Date): Date {
  const r = new Date(d);
  r.setDate(r.getDate() - r.getDay());
  return r;
}

/** Aggregate competency for a day (returns highest level among events). */
function dayCompetency(
  dayEvents: CurriculumEvent[],
  progressMap: Record<string, StudentProgress>,
): CompetencyLevel {
  let best: CompetencyLevel = 'none';
  const rank: Record<CompetencyLevel, number> = { none: 0, red: 1, yellow: 2, green: 3 };
  for (const ev of dayEvents) {
    const p = progressMap[ev.id];
    if (p && rank[p.competency_level] > rank[best]) {
      best = p.competency_level;
    }
  }
  return best;
}

export function CurriculumCalendar({
  events,
  progressMap,
  onEventOpen,
  weekStart,
  onWeekChange,
}: Props) {
  const today = useMemo(() => toISO(new Date()), []);

  // Group events by date
  const byDate = useMemo(() => {
    const map: Record<string, CurriculumEvent[]> = {};
    for (const ev of events) {
      (map[ev.date] ??= []).push(ev);
    }
    return map;
  }, [events]);

  // Build 7 days
  const days = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => {
      const d = addDays(weekStart, i);
      const iso = toISO(d);
      return {
        date: d,
        iso,
        dayOfWeek: d.getDay(),
        dayNum: d.getDate(),
        month: d.toLocaleString('default', { month: 'short' }),
        events: byDate[iso] ?? [],
        isToday: iso === today,
      };
    });
  }, [weekStart, byDate, today]);

  const prevWeek = useCallback(
    () => onWeekChange(addDays(weekStart, -7)),
    [weekStart, onWeekChange],
  );
  const nextWeek = useCallback(
    () => onWeekChange(addDays(weekStart, 7)),
    [weekStart, onWeekChange],
  );
  const goToday = useCallback(
    () => onWeekChange(weekSunday(new Date())),
    [onWeekChange],
  );

  // Week label
  const weekLabel = useMemo(() => {
    const end = addDays(weekStart, 6);
    const startStr = weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    const endStr = end.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    return `${startStr} \u2013 ${endStr}`;
  }, [weekStart]);

  return (
    <div className="flex flex-col h-full">
      {/* Navigation bar */}
      <div
        className="flex items-center justify-between px-4 py-3 shrink-0"
        style={{ borderBottom: '1px solid var(--color-border)' }}
      >
        <div className="flex items-center gap-2">
          <button
            onClick={prevWeek}
            className="p-1.5 rounded-lg hover:opacity-70"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            <ChevronLeft size={18} />
          </button>
          <button
            onClick={goToday}
            className="px-3 py-1 rounded-lg text-xs font-medium"
            style={{
              background: 'var(--color-accent)',
              color: 'white',
            }}
          >
            Today
          </button>
          <button
            onClick={nextWeek}
            className="p-1.5 rounded-lg hover:opacity-70"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            <ChevronRight size={18} />
          </button>
        </div>
        <span
          className="text-sm font-semibold"
          style={{ color: 'var(--color-text)' }}
        >
          {weekLabel}
        </span>
      </div>

      {/* Vertical day columns */}
      <div className="flex-1 overflow-y-auto">
        <div className="flex h-full" style={{ minHeight: 600 }}>
          {days.map((day) => {
            const comp = dayCompetency(day.events, progressMap);
            return (
              <div
                key={day.iso}
                className="flex-1 flex flex-col min-w-0"
                style={{
                  borderRight: '1px solid var(--color-border)',
                  background: day.isToday
                    ? 'var(--color-accent-muted, rgba(59,130,246,0.04))'
                    : undefined,
                }}
              >
                {/* Day header */}
                <div
                  className="text-center py-2 shrink-0"
                  style={{
                    borderBottom: '1px solid var(--color-border)',
                    background: day.isToday
                      ? 'var(--color-accent-muted, rgba(59,130,246,0.08))'
                      : 'var(--color-bg-secondary)',
                  }}
                >
                  <div
                    className="text-xs font-medium"
                    style={{
                      color: day.isToday ? 'var(--color-accent)' : 'var(--color-text-tertiary)',
                    }}
                  >
                    {DAY_SHORT[day.dayOfWeek]}
                  </div>
                  <div
                    className="text-lg font-bold"
                    style={{
                      color: day.isToday ? 'var(--color-accent)' : 'var(--color-text)',
                    }}
                  >
                    {day.dayNum}
                  </div>
                  <div
                    className="text-xs"
                    style={{ color: 'var(--color-text-tertiary)' }}
                  >
                    {day.month}
                  </div>
                  {/* Day-level competency dot */}
                  {day.events.length > 0 && (
                    <span
                      className="inline-block rounded-full mt-1"
                      style={{
                        width: 6,
                        height: 6,
                        background: COMPETENCY_COLORS[comp],
                      }}
                    />
                  )}
                </div>

                {/* Events list */}
                <div className="flex-1 p-1 overflow-y-auto">
                  {day.events.length === 0 ? (
                    <div
                      className="text-xs text-center py-4"
                      style={{ color: 'var(--color-text-tertiary)' }}
                    >
                      No events
                    </div>
                  ) : (
                    day.events.map((ev) => (
                      <LectureCard
                        key={ev.id}
                        event={ev}
                        progress={progressMap[ev.id]}
                        onDoubleClick={onEventOpen}
                      />
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
