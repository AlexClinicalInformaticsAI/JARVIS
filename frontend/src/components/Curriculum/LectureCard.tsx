import { useState, useCallback } from 'react';
import type { CurriculumEvent, StudentProgress, CompetencyLevel } from '../../types/curriculum';
import { EVENT_TYPE_COLORS, EVENT_TYPE_LABELS, COMPETENCY_COLORS } from '../../types/curriculum';
import { CompetencyBadge } from './CompetencyBadge';

interface Props {
  event: CurriculumEvent;
  progress?: StudentProgress;
  onDoubleClick: (event: CurriculumEvent) => void;
}

export function LectureCard({ event, progress, onDoubleClick }: Props) {
  const [tooltipVisible, setTooltipVisible] = useState(false);

  const handleDoubleClick = useCallback(() => {
    onDoubleClick(event);
  }, [event, onDoubleClick]);

  const typeColor = EVENT_TYPE_COLORS[event.event_type] || '#6b7280';
  const compLevel: CompetencyLevel = progress?.competency_level ?? 'none';
  const compColor = COMPETENCY_COLORS[compLevel];

  // Format time display
  const startHM = event.start_time.slice(0, 5);
  const endHM = event.end_time.slice(0, 5);

  // Progress indicators
  const attended = progress?.attended ?? false;
  const listened = progress?.lecture_listened ?? false;
  const assignDone = progress?.assignment_completed ?? false;

  return (
    <div
      className="relative rounded-lg cursor-pointer transition-all"
      style={{
        background: 'var(--color-bg-secondary)',
        border: `1px solid var(--color-border)`,
        borderLeft: `4px solid ${typeColor}`,
        padding: '8px 10px',
        marginBottom: 4,
      }}
      onMouseEnter={() => setTooltipVisible(true)}
      onMouseLeave={() => setTooltipVisible(false)}
      onDoubleClick={handleDoubleClick}
    >
      {/* Header row */}
      <div className="flex items-center justify-between gap-2 mb-1">
        <span
          className="text-xs font-medium truncate"
          style={{ color: 'var(--color-text)' }}
        >
          {event.title}
        </span>
        {/* R/Y/G dot */}
        <span
          className="shrink-0 rounded-full"
          style={{ width: 10, height: 10, background: compColor }}
          title={`Competency: ${compLevel}`}
        />
      </div>

      {/* Time and type */}
      <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
        <span>{startHM} - {endHM}</span>
        <span
          className="rounded px-1"
          style={{ background: `${typeColor}20`, color: typeColor, fontSize: 10 }}
        >
          {EVENT_TYPE_LABELS[event.event_type]}
        </span>
      </div>

      {/* Progress mini-icons */}
      <div className="flex items-center gap-2 mt-1" style={{ fontSize: 10, color: 'var(--color-text-tertiary)' }}>
        <span style={{ opacity: attended ? 1 : 0.3 }} title="Attended">
          {attended ? '\u2714' : '\u25CB'} Attend
        </span>
        <span style={{ opacity: listened ? 1 : 0.3 }} title="Listened">
          {listened ? '\u2714' : '\u25CB'} Listen
        </span>
        <span style={{ opacity: assignDone ? 1 : 0.3 }} title="Assignment">
          {assignDone ? '\u2714' : '\u25CB'} Assign
        </span>
      </div>

      {/* Tooltip on hover — learning objectives */}
      {tooltipVisible && event.learning_objectives.length > 0 && (
        <div
          className="absolute z-50 rounded-lg shadow-lg"
          style={{
            top: '100%',
            left: 0,
            marginTop: 4,
            padding: '10px 12px',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            minWidth: 280,
            maxWidth: 360,
          }}
        >
          <div
            className="text-xs font-semibold mb-2"
            style={{ color: 'var(--color-text)' }}
          >
            Learning Objectives
          </div>
          <ul className="space-y-1">
            {event.learning_objectives.map((obj) => (
              <li
                key={obj.id}
                className="text-xs flex items-start gap-1"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                <span style={{ color: 'var(--color-accent)', marginTop: 2 }}>&bull;</span>
                <span>{obj.description}</span>
              </li>
            ))}
          </ul>
          {event.instructor && (
            <div
              className="text-xs mt-2 pt-2"
              style={{
                borderTop: '1px solid var(--color-border)',
                color: 'var(--color-text-tertiary)',
              }}
            >
              Instructor: {event.instructor}
            </div>
          )}
          <CompetencyBadge level={compLevel} size="sm" />
        </div>
      )}
    </div>
  );
}
