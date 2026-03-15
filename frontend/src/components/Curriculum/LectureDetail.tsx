import { useState, useCallback, useEffect } from 'react';
import { X, CheckCircle, Circle, BookOpen, ClipboardCheck, Brain } from 'lucide-react';
import type {
  CurriculumEvent,
  StudentProgress,
  CompetencyLevel,
} from '../../types/curriculum';
import {
  COMPETENCY_COLORS,
  COMPETENCY_LABELS,
  EVENT_TYPE_LABELS,
  EVENT_TYPE_COLORS,
} from '../../types/curriculum';
import { CompetencyBadge } from './CompetencyBadge';

interface Props {
  event: CurriculumEvent;
  progress: StudentProgress;
  onClose: () => void;
  onSave: (progress: StudentProgress) => void;
}

const LEVELS: CompetencyLevel[] = ['none', 'red', 'yellow', 'green'];

export function LectureDetail({ event, progress: initial, onClose, onSave }: Props) {
  const [draft, setDraft] = useState<StudentProgress>({ ...initial });

  // Sync when event changes
  useEffect(() => {
    setDraft({ ...initial });
  }, [initial]);

  const toggle = useCallback((field: 'attended' | 'lecture_listened' | 'assignment_completed') => {
    setDraft((p) => ({ ...p, [field]: !p[field] }));
  }, []);

  const setCompetency = useCallback((level: CompetencyLevel) => {
    setDraft((p) => ({ ...p, competency_level: level }));
  }, []);

  const handleSave = useCallback(() => {
    onSave(draft);
    onClose();
  }, [draft, onSave, onClose]);

  const typeColor = EVENT_TYPE_COLORS[event.event_type] || '#6b7280';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.6)' }}
      onClick={onClose}
    >
      <div
        className="rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-start justify-between p-5"
          style={{ borderBottom: '1px solid var(--color-border)' }}
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span
                className="rounded px-2 py-0.5 text-xs font-medium"
                style={{ background: `${typeColor}20`, color: typeColor }}
              >
                {EVENT_TYPE_LABELS[event.event_type]}
              </span>
              <CompetencyBadge level={draft.competency_level} size="md" />
            </div>
            <h2
              className="text-lg font-semibold truncate"
              style={{ color: 'var(--color-text)' }}
            >
              {event.title}
            </h2>
            <div className="text-xs mt-1 space-x-3" style={{ color: 'var(--color-text-tertiary)' }}>
              <span>{event.date}</span>
              <span>{event.start_time.slice(0, 5)} - {event.end_time.slice(0, 5)}</span>
              {event.location && <span>{event.location}</span>}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:opacity-70 shrink-0"
            style={{ color: 'var(--color-text-tertiary)' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-5">
          {/* Subject / Topic / Block / Instructor */}
          <div className="grid grid-cols-2 gap-3 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            <div><span className="font-medium">Subject:</span> {event.subject}</div>
            <div><span className="font-medium">Topic:</span> {event.topic}</div>
            {event.block && <div><span className="font-medium">Block:</span> {event.block}</div>}
            {event.instructor && <div><span className="font-medium">Instructor:</span> {event.instructor}</div>}
            <div><span className="font-medium">Year:</span> M{event.year}</div>
          </div>

          {/* Description */}
          {event.description && (
            <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
              {event.description}
            </p>
          )}

          {/* Learning Objectives */}
          {event.learning_objectives.length > 0 && (
            <div>
              <h3
                className="text-xs font-semibold mb-2 flex items-center gap-1"
                style={{ color: 'var(--color-text)' }}
              >
                <BookOpen size={14} />
                Learning Objectives
              </h3>
              <ul className="space-y-1.5">
                {event.learning_objectives.map((obj) => (
                  <li
                    key={obj.id}
                    className="text-xs flex items-start gap-2 rounded-md p-2"
                    style={{
                      background: 'var(--color-bg-secondary)',
                      color: 'var(--color-text-secondary)',
                    }}
                  >
                    <span style={{ color: 'var(--color-accent)', marginTop: 1 }}>&bull;</span>
                    <div className="flex-1">
                      <span>{obj.description}</span>
                      <div className="flex gap-2 mt-1" style={{ color: 'var(--color-text-tertiary)', fontSize: 10 }}>
                        <span>AAMC: {obj.aamc_domain.replace(/_/g, ' ')}</span>
                        <span>Bloom: {obj.bloom_level}</span>
                        {obj.epa_mapping && <span>EPA: {obj.epa_mapping}</span>}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Tracking toggles */}
          <div>
            <h3
              className="text-xs font-semibold mb-2 flex items-center gap-1"
              style={{ color: 'var(--color-text)' }}
            >
              <ClipboardCheck size={14} />
              Progress Tracking
            </h3>
            <div className="space-y-2">
              {([
                ['attended', 'Attended lecture / session'],
                ['lecture_listened', 'Listened to recording / completed content'],
                ['assignment_completed', 'Completed assignment(s)'],
              ] as const).map(([field, label]) => (
                <button
                  key={field}
                  className="flex items-center gap-2 w-full text-left text-xs rounded-md p-2 transition-colors"
                  style={{
                    background: draft[field] ? 'var(--color-accent-muted, rgba(59,130,246,0.08))' : 'var(--color-bg-secondary)',
                    color: draft[field] ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                  }}
                  onClick={() => toggle(field)}
                >
                  {draft[field] ? <CheckCircle size={14} /> : <Circle size={14} />}
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Scores */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium block mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Quiz Score (%)
              </label>
              <input
                type="number"
                min={0}
                max={100}
                className="w-full rounded-md px-2 py-1.5 text-xs"
                style={{
                  background: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text)',
                }}
                value={draft.quiz_score !== null ? Math.round(draft.quiz_score * 100) : ''}
                onChange={(e) =>
                  setDraft((p) => ({
                    ...p,
                    quiz_score: e.target.value ? Number(e.target.value) / 100 : null,
                  }))
                }
                placeholder="--"
              />
            </div>
            <div>
              <label className="text-xs font-medium block mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                Exam Score (%)
              </label>
              <input
                type="number"
                min={0}
                max={100}
                className="w-full rounded-md px-2 py-1.5 text-xs"
                style={{
                  background: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text)',
                }}
                value={draft.exam_score !== null ? Math.round(draft.exam_score * 100) : ''}
                onChange={(e) =>
                  setDraft((p) => ({
                    ...p,
                    exam_score: e.target.value ? Number(e.target.value) / 100 : null,
                  }))
                }
                placeholder="--"
              />
            </div>
          </div>

          {/* Competency level selector (R/Y/G) */}
          <div>
            <h3
              className="text-xs font-semibold mb-2 flex items-center gap-1"
              style={{ color: 'var(--color-text)' }}
            >
              <Brain size={14} />
              Competency Level
            </h3>
            <div className="flex gap-2">
              {LEVELS.map((lvl) => (
                <button
                  key={lvl}
                  className="flex-1 rounded-lg py-2 text-xs font-medium transition-all"
                  style={{
                    background:
                      draft.competency_level === lvl
                        ? `${COMPETENCY_COLORS[lvl]}25`
                        : 'var(--color-bg-secondary)',
                    border: `2px solid ${
                      draft.competency_level === lvl
                        ? COMPETENCY_COLORS[lvl]
                        : 'var(--color-border)'
                    }`,
                    color:
                      draft.competency_level === lvl
                        ? COMPETENCY_COLORS[lvl]
                        : 'var(--color-text-tertiary)',
                  }}
                  onClick={() => setCompetency(lvl)}
                >
                  {COMPETENCY_LABELS[lvl]}
                </button>
              ))}
            </div>
          </div>

          {/* Experiential notes */}
          <div>
            <label className="text-xs font-medium block mb-1" style={{ color: 'var(--color-text-secondary)' }}>
              Experiential / Lived Experience Notes
            </label>
            <textarea
              className="w-full rounded-md px-2 py-1.5 text-xs resize-y"
              rows={3}
              style={{
                background: 'var(--color-bg-secondary)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text)',
              }}
              value={draft.experiential_notes}
              onChange={(e) => setDraft((p) => ({ ...p, experiential_notes: e.target.value }))}
              placeholder="Clinical encounters, patient interactions, reflections..."
            />
          </div>

          {/* xAPI statements preview */}
          {draft.xapi_statements.length > 0 && (
            <details className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
              <summary className="cursor-pointer font-medium mb-1">
                xAPI Statements ({draft.xapi_statements.length})
              </summary>
              <pre
                className="rounded-md p-2 overflow-x-auto"
                style={{
                  background: 'var(--color-bg-secondary)',
                  fontSize: 10,
                  maxHeight: 200,
                }}
              >
                {JSON.stringify(draft.xapi_statements, null, 2)}
              </pre>
            </details>
          )}
        </div>

        {/* Footer */}
        <div
          className="flex justify-end gap-2 p-4"
          style={{ borderTop: '1px solid var(--color-border)' }}
        >
          <button
            className="rounded-lg px-4 py-2 text-xs font-medium"
            style={{
              background: 'var(--color-bg-secondary)',
              color: 'var(--color-text-secondary)',
            }}
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="rounded-lg px-4 py-2 text-xs font-medium"
            style={{
              background: 'var(--color-accent)',
              color: 'white',
            }}
            onClick={handleSave}
          >
            Save Progress
          </button>
        </div>
      </div>
    </div>
  );
}
