import { useState, useEffect } from 'react';
import {
  BookOpen,
  Clock,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  Lightbulb,
} from 'lucide-react';
import type {
  CurriculumEvent,
  StudentProgress,
  ObjectiveProgressData,
  LearningObjective,
  ColorLevel,
} from '../../types/curriculum';
import {
  AAMC_DOMAIN_LABELS,
  STAGE_LABELS,
  STAGE_COLORS,
  COMPETENCY_LABELS,
  EXPOSURE_LABELS,
  COMPETENCY_COLORS,
  EXPOSURE_COLORS,
} from '../../types/curriculum';
import { CompetencyBadge, DualDot } from './CompetencyBadge';

const BASE = import.meta.env.VITE_API_URL || '';

interface Props {
  event: CurriculumEvent | null;
  progress: StudentProgress | null;
  studentId: string;
}

const TREND_ICONS = {
  improving: TrendingUp,
  stable: Minus,
  declining: TrendingDown,
  stale: AlertTriangle,
};

const TREND_COLORS = {
  improving: '#22c55e',
  stable: '#6b7280',
  declining: '#ef4444',
  stale: '#ef4444',
};

export function RightDetailPane({ event, progress, studentId }: Props) {
  const [objectiveData, setObjectiveData] = useState<
    Record<string, { progress: ObjectiveProgressData; prior: CurriculumEvent[]; future: CurriculumEvent[] }>
  >({});
  const [loading, setLoading] = useState(false);

  // Load objective data when event changes
  useEffect(() => {
    if (!event || event.learning_objectives.length === 0) {
      setObjectiveData({});
      return;
    }

    setLoading(true);
    Promise.all(
      event.learning_objectives.map(async (obj) => {
        const [prog, prior, future] = await Promise.all([
          fetch(`${BASE}/v1/curriculum/objectives/${obj.id}/progress/${studentId}`)
            .then((r) => r.json())
            .catch(() => null),
          fetch(`${BASE}/v1/curriculum/objectives/${obj.id}/prior?before=${event.date}`)
            .then((r) => r.json())
            .catch(() => []),
          fetch(`${BASE}/v1/curriculum/objectives/${obj.id}/future?after=${event.date}`)
            .then((r) => r.json())
            .catch(() => []),
        ]);
        return [obj.id, { progress: prog, prior, future }] as const;
      }),
    )
      .then((entries) => {
        const map: typeof objectiveData = {};
        for (const [id, data] of entries) {
          map[id] = data;
        }
        setObjectiveData(map);
      })
      .finally(() => setLoading(false));
  }, [event, studentId]);

  if (!event) {
    return (
      <aside
        className="w-[320px] shrink-0 flex items-center justify-center"
        style={{
          borderLeft: '1px solid var(--color-border)',
          background: 'var(--color-surface)',
          color: 'var(--color-text-tertiary)',
        }}
      >
        <div className="text-center text-xs">
          <BookOpen size={24} className="mx-auto mb-2 opacity-30" />
          Select an event to see<br />objectives and coverage
        </div>
      </aside>
    );
  }

  return (
    <aside
      className="w-[320px] shrink-0 flex flex-col overflow-y-auto"
      style={{
        borderLeft: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
      }}
    >
      {/* Event header */}
      <div className="p-4" style={{ borderBottom: '1px solid var(--color-border)' }}>
        <h3
          className="text-sm font-semibold mb-1 leading-snug"
          style={{ color: 'var(--color-text)' }}
        >
          {event.title}
        </h3>
        <div className="text-xs space-y-0.5" style={{ color: 'var(--color-text-tertiary)' }}>
          <div>{event.date} &middot; {event.start_time.slice(0, 5)}-{event.end_time.slice(0, 5)}</div>
          <div>{event.subject} &middot; {event.topic}</div>
          {event.instructor && <div>Instructor: {event.instructor}</div>}
          {event.block && <div>Block: {event.block}</div>}
          {event.course && <div>Course: {event.course}</div>}
        </div>

        {/* Dual R/Y/G status */}
        {progress && (
          <div className="flex gap-2 mt-2">
            <CompetencyBadge level={progress.exposure_level} axis="exposure" size="sm" />
            <CompetencyBadge level={progress.competency_level} axis="competency" size="sm" />
          </div>
        )}
      </div>

      {/* Learning Objectives with longitudinal data */}
      <div className="flex-1 p-4 space-y-3">
        <h4
          className="text-xs font-semibold flex items-center gap-1"
          style={{ color: 'var(--color-text)' }}
        >
          <BookOpen size={14} />
          Learning Objectives ({event.learning_objectives.length})
        </h4>

        {loading ? (
          <div className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
            Loading objective data...
          </div>
        ) : (
          event.learning_objectives.map((obj) => (
            <ObjectiveCard
              key={obj.id}
              objective={obj}
              data={objectiveData[obj.id]}
              currentDate={event.date}
            />
          ))
        )}
      </div>
    </aside>
  );
}

// ── Objective Card ──────────────────────────────────────────────────────

function ObjectiveCard({
  objective,
  data,
  currentDate,
}: {
  objective: LearningObjective;
  data?: { progress: ObjectiveProgressData; prior: CurriculumEvent[]; future: CurriculumEvent[] };
  currentDate: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const prog = data?.progress;
  const prior = data?.prior ?? [];
  const future = data?.future ?? [];

  const TrendIcon = prog ? TREND_ICONS[prog.trend] : Minus;
  const trendColor = prog ? TREND_COLORS[prog.trend] : '#6b7280';

  return (
    <div
      className="rounded-lg"
      style={{
        background: 'var(--color-bg-secondary)',
        border: '1px solid var(--color-border)',
      }}
    >
      {/* Header — click to expand */}
      <button
        className="w-full text-left p-2.5 flex items-start gap-2"
        onClick={() => setExpanded(!expanded)}
        style={{ cursor: 'pointer' }}
      >
        <ChevronRight
          size={12}
          className="shrink-0 mt-0.5 transition-transform"
          style={{
            color: 'var(--color-text-tertiary)',
            transform: expanded ? 'rotate(90deg)' : undefined,
          }}
        />
        <div className="flex-1 min-w-0">
          <div className="text-xs leading-snug" style={{ color: 'var(--color-text-secondary)' }}>
            {objective.description}
          </div>
          <div className="flex items-center gap-2 mt-1" style={{ fontSize: 10, color: 'var(--color-text-tertiary)' }}>
            <span>{AAMC_DOMAIN_LABELS[objective.aamc_domain]}</span>
            <span>&middot;</span>
            <span>Bloom: {objective.bloom_level}</span>
            {objective.epa_mapping && <><span>&middot;</span><span>{objective.epa_mapping}</span></>}
          </div>
        </div>
        {/* Dual dot + trend */}
        <div className="shrink-0 flex items-center gap-1">
          {prog && (
            <>
              <DualDot exposure={prog.exposure_level} competency={prog.competency_level} size={8} />
              <TrendIcon size={12} style={{ color: trendColor }} />
            </>
          )}
        </div>
      </button>

      {/* Expanded details */}
      {expanded && prog && (
        <div
          className="px-3 pb-3 space-y-2"
          style={{ borderTop: '1px solid var(--color-border)' }}
        >
          {/* Stage */}
          <div className="flex items-center gap-2 pt-2">
            <span
              className="text-xs font-medium rounded px-1.5 py-0.5"
              style={{
                background: `${STAGE_COLORS[prog.stage]}20`,
                color: STAGE_COLORS[prog.stage],
              }}
            >
              {STAGE_LABELS[prog.stage]}
            </span>
            <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
              {prog.encounter_count} encounter{prog.encounter_count !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Modalities */}
          {prog.modalities_seen.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {prog.modalities_seen.map((m) => (
                <span
                  key={m}
                  className="text-xs rounded px-1.5 py-0.5"
                  style={{ background: 'var(--color-bg-tertiary, #f3f4f6)', color: 'var(--color-text-tertiary)', fontSize: 10 }}
                >
                  {m}
                </span>
              ))}
            </div>
          )}

          {/* Assessment scores */}
          {prog.assessment_scores.length > 0 && (
            <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
              <span className="font-medium">Scores: </span>
              {prog.assessment_scores.map((s, i) => (
                <span
                  key={i}
                  className="inline-block rounded px-1 mr-1"
                  style={{
                    background: s >= 0.7 ? '#22c55e20' : s >= 0.5 ? '#eab30820' : '#ef444420',
                    color: s >= 0.7 ? '#22c55e' : s >= 0.5 ? '#eab308' : '#ef4444',
                  }}
                >
                  {Math.round(s * 100)}%
                </span>
              ))}
            </div>
          )}

          {/* Timeline: first/last exposure */}
          <div className="grid grid-cols-2 gap-1 text-xs" style={{ color: 'var(--color-text-tertiary)', fontSize: 10 }}>
            {prog.first_exposure && <div>First: {prog.first_exposure}</div>}
            {prog.last_exposure && <div>Last: {prog.last_exposure}</div>}
            {prog.last_assessed && <div>Assessed: {prog.last_assessed}</div>}
            {prog.last_applied && <div>Applied: {prog.last_applied}</div>}
          </div>

          {/* Days since last exposure */}
          {prog.days_since_last_exposure !== null && prog.days_since_last_exposure > 0 && (
            <div
              className="flex items-center gap-1 text-xs"
              style={{
                color: prog.days_since_last_exposure > 90 ? '#ef4444' : 'var(--color-text-tertiary)',
              }}
            >
              <Clock size={10} />
              {prog.days_since_last_exposure} days since last exposure
            </div>
          )}

          {/* Recommended action */}
          {prog.recommended_action && (
            <div
              className="flex items-start gap-1.5 text-xs rounded-md p-2"
              style={{
                background: 'var(--color-accent-muted, rgba(59,130,246,0.06))',
                color: 'var(--color-accent)',
              }}
            >
              <Lightbulb size={12} className="shrink-0 mt-0.5" />
              {prog.recommended_action}
            </div>
          )}

          {/* Previously covered */}
          {prior.length > 0 && (
            <div>
              <div className="text-xs font-medium mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                Previously covered ({prior.length})
              </div>
              {prior.slice(-3).map((ev) => (
                <div key={ev.id} className="text-xs mb-0.5" style={{ color: 'var(--color-text-tertiary)', fontSize: 10 }}>
                  {ev.date} — {ev.title}
                </div>
              ))}
            </div>
          )}

          {/* Will be covered */}
          {future.length > 0 && (
            <div>
              <div className="text-xs font-medium mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
                Coming up ({future.length})
              </div>
              {future.slice(0, 3).map((ev) => (
                <div key={ev.id} className="text-xs mb-0.5" style={{ color: 'var(--color-text-tertiary)', fontSize: 10 }}>
                  {ev.date} — {ev.title}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
