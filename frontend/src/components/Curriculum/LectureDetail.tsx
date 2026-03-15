import { useState, useCallback, useEffect } from 'react';
import { X, CheckCircle, Circle, BookOpen, ClipboardCheck, Brain, Eye } from 'lucide-react';
import type { CurriculumEvent, StudentProgress, ColorLevel } from '../../types/curriculum';
import {
  COMPETENCY_COLORS,
  COMPETENCY_LABELS,
  EXPOSURE_COLORS,
  EXPOSURE_LABELS,
  EVENT_TYPE_LABELS,
  EVENT_TYPE_COLORS,
  AAMC_DOMAIN_LABELS,
} from '../../types/curriculum';
import { CompetencyBadge } from './CompetencyBadge';

interface Props {
  event: CurriculumEvent;
  progress: StudentProgress;
  onClose: () => void;
  onSave: (progress: StudentProgress) => void;
}

const COLOR_LEVELS: ColorLevel[] = ['none', 'red', 'yellow', 'green'];

export function LectureDetail({ event, progress: initial, onClose, onSave }: Props) {
  const [draft, setDraft] = useState<StudentProgress>({ ...initial });

  useEffect(() => {
    setDraft({ ...initial });
  }, [initial]);

  const toggleBool = useCallback((field: keyof StudentProgress) => {
    setDraft((p) => ({ ...p, [field]: !p[field as keyof typeof p] } as StudentProgress));
  }, []);

  const handleSave = useCallback(() => {
    onSave(draft);
    onClose();
  }, [draft, onSave, onClose]);

  const typeColor = EVENT_TYPE_COLORS[event.event_type] || '#6b7280';

  const engagementFields = [
    { field: 'attended' as const, label: 'Attended lecture / session' },
    { field: 'lecture_listened' as const, label: 'Listened to lecture content' },
    { field: 'recording_watched' as const, label: 'Watched recording' },
    { field: 'reading_completed' as const, label: 'Completed reading materials' },
    { field: 'assignment_completed' as const, label: 'Completed assignment(s)' },
    { field: 'simulation_completed' as const, label: 'Completed simulation' },
    { field: 'patient_encounter_logged' as const, label: 'Logged patient encounter' },
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.6)' }}
      onClick={onClose}
    >
      <div
        className="rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-5" style={{ borderBottom: '1px solid var(--color-border)' }}>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span
                className="rounded px-2 py-0.5 text-xs font-medium"
                style={{ background: `${typeColor}20`, color: typeColor }}
              >
                {EVENT_TYPE_LABELS[event.event_type]}
              </span>
              <CompetencyBadge level={draft.exposure_level} axis="exposure" size="md" />
              <CompetencyBadge level={draft.competency_level} axis="competency" size="md" />
            </div>
            <h2 className="text-lg font-semibold truncate" style={{ color: 'var(--color-text)' }}>
              {event.title}
            </h2>
            <div className="text-xs mt-1 space-x-3" style={{ color: 'var(--color-text-tertiary)' }}>
              <span>{event.date}</span>
              <span>{event.start_time.slice(0, 5)} - {event.end_time.slice(0, 5)}</span>
              {event.location && <span>{event.location}</span>}
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:opacity-70 shrink-0" style={{ color: 'var(--color-text-tertiary)' }}>
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-5">
          {/* Event info grid */}
          <div className="grid grid-cols-2 gap-3 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            <div><span className="font-medium">Subject:</span> {event.subject}</div>
            <div><span className="font-medium">Topic:</span> {event.topic}</div>
            {event.block && <div><span className="font-medium">Block:</span> {event.block}</div>}
            {event.course && <div><span className="font-medium">Course:</span> {event.course}</div>}
            {event.instructor && <div><span className="font-medium">Instructor:</span> {event.instructor}</div>}
            <div><span className="font-medium">Year:</span> M{event.year}</div>
          </div>

          {event.description && (
            <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
              {event.description}
            </p>
          )}

          {/* Learning Objectives */}
          {event.learning_objectives.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold mb-2 flex items-center gap-1" style={{ color: 'var(--color-text)' }}>
                <BookOpen size={14} /> Learning Objectives
              </h3>
              <ul className="space-y-1.5">
                {event.learning_objectives.map((obj) => (
                  <li
                    key={obj.id}
                    className="text-xs flex items-start gap-2 rounded-md p-2"
                    style={{ background: 'var(--color-bg-secondary)', color: 'var(--color-text-secondary)' }}
                  >
                    <span style={{ color: 'var(--color-accent)', marginTop: 1 }}>&bull;</span>
                    <div className="flex-1">
                      <span>{obj.description}</span>
                      <div className="flex gap-2 mt-1 flex-wrap" style={{ color: 'var(--color-text-tertiary)', fontSize: 10 }}>
                        <span>{AAMC_DOMAIN_LABELS[obj.aamc_domain]}</span>
                        <span>Bloom: {obj.bloom_level}</span>
                        {obj.epa_mapping && <span>{obj.epa_mapping}</span>}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Engagement toggles */}
          <div>
            <h3 className="text-xs font-semibold mb-2 flex items-center gap-1" style={{ color: 'var(--color-text)' }}>
              <ClipboardCheck size={14} /> Engagement Tracking
            </h3>
            <div className="space-y-2">
              {engagementFields.map(({ field, label }) => (
                <button
                  key={field}
                  className="flex items-center gap-2 w-full text-left text-xs rounded-md p-2 transition-colors"
                  style={{
                    background: (draft as Record<string, unknown>)[field]
                      ? 'var(--color-accent-muted, rgba(59,130,246,0.08))'
                      : 'var(--color-bg-secondary)',
                    color: (draft as Record<string, unknown>)[field]
                      ? 'var(--color-accent)'
                      : 'var(--color-text-secondary)',
                  }}
                  onClick={() => toggleBool(field)}
                >
                  {(draft as Record<string, unknown>)[field] ? <CheckCircle size={14} /> : <Circle size={14} />}
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Scores */}
          <div className="grid grid-cols-3 gap-3">
            {(['quiz_score', 'exam_score', 'osce_score'] as const).map((field) => (
              <div key={field}>
                <label className="text-xs font-medium block mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                  {field.replace('_score', '').replace('_', ' ').toUpperCase()} (%)
                </label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  className="w-full rounded-md px-2 py-1.5 text-xs"
                  style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}
                  value={draft[field] !== null ? Math.round((draft[field] as number) * 100) : ''}
                  onChange={(e) =>
                    setDraft((p) => ({ ...p, [field]: e.target.value ? Number(e.target.value) / 100 : null }))
                  }
                  placeholder="--"
                />
              </div>
            ))}
          </div>

          {/* Faculty observation */}
          <div>
            <label className="text-xs font-medium block mb-1" style={{ color: 'var(--color-text-secondary)' }}>
              Faculty Observation
            </label>
            <textarea
              className="w-full rounded-md px-2 py-1.5 text-xs resize-y"
              rows={2}
              style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}
              value={draft.faculty_observation ?? ''}
              onChange={(e) => setDraft((p) => ({ ...p, faculty_observation: e.target.value || null }))}
              placeholder="Clinical faculty evaluation notes..."
            />
          </div>

          {/* Dual R/Y/G selectors */}
          <div className="grid grid-cols-2 gap-4">
            {/* Exposure level */}
            <div>
              <h3 className="text-xs font-semibold mb-2 flex items-center gap-1" style={{ color: 'var(--color-text)' }}>
                <Eye size={14} /> Exposure
              </h3>
              <div className="flex flex-col gap-1">
                {COLOR_LEVELS.map((lvl) => (
                  <button
                    key={lvl}
                    className="rounded-lg py-1.5 text-xs font-medium transition-all text-left px-2"
                    style={{
                      background: draft.exposure_level === lvl ? `${EXPOSURE_COLORS[lvl]}25` : 'var(--color-bg-secondary)',
                      border: `2px solid ${draft.exposure_level === lvl ? EXPOSURE_COLORS[lvl] : 'var(--color-border)'}`,
                      color: draft.exposure_level === lvl ? EXPOSURE_COLORS[lvl] : 'var(--color-text-tertiary)',
                    }}
                    onClick={() => setDraft((p) => ({ ...p, exposure_level: lvl }))}
                  >
                    {EXPOSURE_LABELS[lvl]}
                  </button>
                ))}
              </div>
            </div>

            {/* Competency level */}
            <div>
              <h3 className="text-xs font-semibold mb-2 flex items-center gap-1" style={{ color: 'var(--color-text)' }}>
                <Brain size={14} /> Competency
              </h3>
              <div className="flex flex-col gap-1">
                {COLOR_LEVELS.map((lvl) => (
                  <button
                    key={lvl}
                    className="rounded-lg py-1.5 text-xs font-medium transition-all text-left px-2"
                    style={{
                      background: draft.competency_level === lvl ? `${COMPETENCY_COLORS[lvl]}25` : 'var(--color-bg-secondary)',
                      border: `2px solid ${draft.competency_level === lvl ? COMPETENCY_COLORS[lvl] : 'var(--color-border)'}`,
                      color: draft.competency_level === lvl ? COMPETENCY_COLORS[lvl] : 'var(--color-text-tertiary)',
                    }}
                    onClick={() => setDraft((p) => ({ ...p, competency_level: lvl }))}
                  >
                    {COMPETENCY_LABELS[lvl]}
                  </button>
                ))}
              </div>
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
              style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}
              value={draft.experiential_notes}
              onChange={(e) => setDraft((p) => ({ ...p, experiential_notes: e.target.value }))}
              placeholder="Clinical encounters, patient interactions, reflections..."
            />
          </div>

          {/* xAPI preview */}
          {draft.xapi_statements.length > 0 && (
            <details className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
              <summary className="cursor-pointer font-medium mb-1">
                xAPI Statements ({draft.xapi_statements.length})
              </summary>
              <pre
                className="rounded-md p-2 overflow-x-auto"
                style={{ background: 'var(--color-bg-secondary)', fontSize: 10, maxHeight: 200 }}
              >
                {JSON.stringify(draft.xapi_statements, null, 2)}
              </pre>
            </details>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4" style={{ borderTop: '1px solid var(--color-border)' }}>
          <button
            className="rounded-lg px-4 py-2 text-xs font-medium"
            style={{ background: 'var(--color-bg-secondary)', color: 'var(--color-text-secondary)' }}
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="rounded-lg px-4 py-2 text-xs font-medium"
            style={{ background: 'var(--color-accent)', color: 'white' }}
            onClick={handleSave}
          >
            Save Progress
          </button>
        </div>
      </div>
    </div>
  );
}
