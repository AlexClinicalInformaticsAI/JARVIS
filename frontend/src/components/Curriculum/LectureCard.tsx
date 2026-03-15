import { useState, useCallback } from 'react';
import type { CurriculumEvent, StudentProgress, ColorLevel } from '../../types/curriculum';
import {
  EVENT_TYPE_COLORS,
  EVENT_TYPE_LABELS,
  EXPOSURE_COLORS,
  EXPOSURE_LABELS,
  COMPETENCY_COLORS,
  COMPETENCY_LABELS,
  AAMC_DOMAIN_LABELS,
} from '../../types/curriculum';
import { DualDot } from './CompetencyBadge';

interface Props {
  event: CurriculumEvent;
  progress?: StudentProgress;
  selected?: boolean;
  onClick: (event: CurriculumEvent) => void;
  onDoubleClick: (event: CurriculumEvent) => void;
}

export function LectureCard({ event, progress, selected, onClick, onDoubleClick }: Props) {
  const [tooltipVisible, setTooltipVisible] = useState(false);

  const handleClick = useCallback(() => onClick(event), [event, onClick]);
  const handleDoubleClick = useCallback(() => onDoubleClick(event), [event, onDoubleClick]);

  const typeColor = EVENT_TYPE_COLORS[event.event_type] || '#6b7280';
  const expLevel: ColorLevel = progress?.exposure_level ?? 'none';
  const compLevel: ColorLevel = progress?.competency_level ?? 'none';

  const startHM = event.start_time.slice(0, 5);
  const endHM = event.end_time.slice(0, 5);

  // Engagement indicators
  const checks = [
    { done: progress?.attended, label: 'Attend' },
    { done: progress?.lecture_listened, label: 'Listen' },
    { done: progress?.recording_watched, label: 'Watch' },
    { done: progress?.assignment_completed, label: 'Assign' },
    { done: progress?.reading_completed, label: 'Read' },
    { done: progress?.simulation_completed, label: 'Sim' },
    { done: progress?.patient_encounter_logged, label: 'Clin' },
  ].filter((c) => c.done !== undefined); // only show applicable

  return (
    <div
      className="relative rounded-lg cursor-pointer transition-all"
      style={{
        background: selected
          ? 'var(--color-accent-muted, rgba(59,130,246,0.08))'
          : 'var(--color-bg-secondary)',
        border: `1px solid ${selected ? 'var(--color-accent)' : 'var(--color-border)'}`,
        borderLeft: `4px solid ${typeColor}`,
        padding: '8px 10px',
        marginBottom: 4,
      }}
      onMouseEnter={() => setTooltipVisible(true)}
      onMouseLeave={() => setTooltipVisible(false)}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
    >
      {/* Header row */}
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-xs font-medium truncate" style={{ color: 'var(--color-text)' }}>
          {event.title}
        </span>
        {/* Dual R/Y/G dots: exposure | competency */}
        <DualDot exposure={expLevel} competency={compLevel} size={8} />
      </div>

      {/* Time and type */}
      <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
        <span>{startHM}-{endHM}</span>
        <span
          className="rounded px-1"
          style={{ background: `${typeColor}20`, color: typeColor, fontSize: 10 }}
        >
          {EVENT_TYPE_LABELS[event.event_type]}
        </span>
      </div>

      {/* Progress mini-icons */}
      <div className="flex items-center gap-1.5 mt-1 flex-wrap" style={{ fontSize: 10, color: 'var(--color-text-tertiary)' }}>
        {checks.map(({ done, label }) => (
          <span key={label} style={{ opacity: done ? 1 : 0.3 }}>
            {done ? '\u2714' : '\u25CB'} {label}
          </span>
        ))}
      </div>

      {/* Tooltip on hover */}
      {tooltipVisible && (
        <div
          className="absolute z-50 rounded-lg shadow-lg"
          style={{
            top: '100%',
            left: 0,
            marginTop: 4,
            padding: '10px 12px',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            minWidth: 300,
            maxWidth: 380,
          }}
        >
          {/* Dual status */}
          <div className="flex gap-3 mb-2" style={{ fontSize: 10 }}>
            <span className="flex items-center gap-1">
              <span className="rounded-full" style={{ width: 8, height: 8, background: EXPOSURE_COLORS[expLevel] }} />
              Exposure: {EXPOSURE_LABELS[expLevel]}
            </span>
            <span className="flex items-center gap-1">
              <span className="rounded-full" style={{ width: 8, height: 8, background: COMPETENCY_COLORS[compLevel] }} />
              Competency: {COMPETENCY_LABELS[compLevel]}
            </span>
          </div>

          {/* Learning objectives */}
          {event.learning_objectives.length > 0 && (
            <>
              <div className="text-xs font-semibold mb-1" style={{ color: 'var(--color-text)' }}>
                Learning Objectives
              </div>
              <ul className="space-y-1 mb-2">
                {event.learning_objectives.map((obj) => (
                  <li key={obj.id} className="text-xs flex items-start gap-1" style={{ color: 'var(--color-text-secondary)' }}>
                    <span style={{ color: 'var(--color-accent)', marginTop: 2 }}>&bull;</span>
                    <div>
                      <span>{obj.description}</span>
                      <span className="ml-1" style={{ color: 'var(--color-text-tertiary)', fontSize: 10 }}>
                        ({AAMC_DOMAIN_LABELS[obj.aamc_domain]})
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}

          {/* Instructor and location */}
          <div className="text-xs space-y-0.5" style={{ color: 'var(--color-text-tertiary)' }}>
            {event.instructor && <div>Instructor: {event.instructor}</div>}
            {event.location && <div>Location: {event.location}</div>}
            {event.block && <div>Block: {event.block}</div>}
          </div>

          {/* Scores if available */}
          {progress && (progress.quiz_score !== null || progress.exam_score !== null) && (
            <div className="flex gap-2 mt-2" style={{ fontSize: 10 }}>
              {progress.quiz_score !== null && (
                <span
                  className="rounded px-1.5 py-0.5"
                  style={{
                    background: progress.quiz_score >= 0.7 ? '#22c55e20' : '#ef444420',
                    color: progress.quiz_score >= 0.7 ? '#22c55e' : '#ef4444',
                  }}
                >
                  Quiz: {Math.round(progress.quiz_score * 100)}%
                </span>
              )}
              {progress.exam_score !== null && (
                <span
                  className="rounded px-1.5 py-0.5"
                  style={{
                    background: progress.exam_score >= 0.7 ? '#22c55e20' : '#ef444420',
                    color: progress.exam_score >= 0.7 ? '#22c55e' : '#ef4444',
                  }}
                >
                  Exam: {Math.round(progress.exam_score * 100)}%
                </span>
              )}
            </div>
          )}

          <div className="text-xs mt-2 italic" style={{ color: 'var(--color-text-tertiary)', fontSize: 10 }}>
            Click to view details &middot; Double-click to edit progress
          </div>
        </div>
      )}
    </div>
  );
}
