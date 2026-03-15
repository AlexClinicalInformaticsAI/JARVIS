import {
  Filter,
  Calendar,
  BookOpen,
  AlertTriangle,
  Eye,
  Brain,
} from 'lucide-react';
import type { CurriculumFilters, ColorLevel } from '../../types/curriculum';
import {
  EXPOSURE_COLORS,
  EXPOSURE_LABELS,
  COMPETENCY_COLORS,
  COMPETENCY_LABELS,
} from '../../types/curriculum';

interface Props {
  filters: CurriculumFilters;
  onChange: (f: Partial<CurriculumFilters>) => void;
  subjects: string[];
  blocks: string[];
  courses: string[];
  staleCounts: number;
}

const LEVELS: ColorLevel[] = ['red', 'yellow', 'green'];

export function LeftRail({
  filters,
  onChange,
  subjects,
  blocks,
  courses,
  staleCounts,
}: Props) {
  return (
    <aside
      className="w-[220px] shrink-0 flex flex-col overflow-y-auto"
      style={{
        borderRight: '1px solid var(--color-border)',
        background: 'var(--color-sidebar)',
      }}
    >
      <div className="p-3 space-y-4">
        {/* Header */}
        <div className="flex items-center gap-1.5 text-xs font-semibold" style={{ color: 'var(--color-text)' }}>
          <Filter size={14} style={{ color: 'var(--color-accent)' }} />
          Filters
        </div>

        {/* Academic Year */}
        <FilterSection icon={Calendar} label="Academic Year">
          <select
            className="filter-select"
            style={selectStyle}
            value={filters.year}
            onChange={(e) => onChange({ year: Number(e.target.value) })}
          >
            <option value={0}>All Years</option>
            <option value={1}>M1</option>
            <option value={2}>M2</option>
            <option value={3}>M3</option>
            <option value={4}>M4</option>
          </select>
        </FilterSection>

        {/* Subject */}
        <FilterSection icon={BookOpen} label="Subject">
          <select
            style={selectStyle}
            value={filters.subject}
            onChange={(e) => onChange({ subject: e.target.value })}
          >
            <option value="">All Subjects</option>
            {subjects.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </FilterSection>

        {/* Block */}
        {blocks.length > 0 && (
          <FilterSection icon={Calendar} label="Block">
            <select
              style={selectStyle}
              value={filters.block}
              onChange={(e) => onChange({ block: e.target.value })}
            >
              <option value="">All Blocks</option>
              {blocks.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </FilterSection>
        )}

        {/* Course */}
        {courses.length > 0 && (
          <FilterSection icon={BookOpen} label="Course">
            <select
              style={selectStyle}
              value={filters.course}
              onChange={(e) => onChange({ course: e.target.value })}
            >
              <option value="">All Courses</option>
              {courses.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </FilterSection>
        )}

        {/* Exposure filter */}
        <FilterSection icon={Eye} label="Exposure">
          <div className="flex flex-col gap-1">
            <button
              style={pillStyle(filters.exposureFilter === '')}
              onClick={() => onChange({ exposureFilter: '' })}
            >
              All
            </button>
            {LEVELS.map((lvl) => (
              <button
                key={lvl}
                className="flex items-center gap-1.5"
                style={pillStyle(filters.exposureFilter === lvl)}
                onClick={() => onChange({
                  exposureFilter: filters.exposureFilter === lvl ? '' : lvl,
                })}
              >
                <span
                  className="rounded-full"
                  style={{ width: 8, height: 8, background: EXPOSURE_COLORS[lvl] }}
                />
                {EXPOSURE_LABELS[lvl]}
              </button>
            ))}
          </div>
        </FilterSection>

        {/* Competency filter */}
        <FilterSection icon={Brain} label="Competency">
          <div className="flex flex-col gap-1">
            <button
              style={pillStyle(filters.competencyFilter === '')}
              onClick={() => onChange({ competencyFilter: '' })}
            >
              All
            </button>
            {LEVELS.map((lvl) => (
              <button
                key={lvl}
                className="flex items-center gap-1.5"
                style={pillStyle(filters.competencyFilter === lvl)}
                onClick={() => onChange({
                  competencyFilter: filters.competencyFilter === lvl ? '' : lvl,
                })}
              >
                <span
                  className="rounded-full"
                  style={{ width: 8, height: 8, background: COMPETENCY_COLORS[lvl] }}
                />
                {COMPETENCY_LABELS[lvl]}
              </button>
            ))}
          </div>
        </FilterSection>

        {/* Quick toggles */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-xs cursor-pointer" style={{ color: 'var(--color-text-secondary)' }}>
            <input
              type="checkbox"
              checked={filters.showOnlyIncomplete}
              onChange={() => onChange({ showOnlyIncomplete: !filters.showOnlyIncomplete })}
            />
            Show only incomplete
          </label>
          <label className="flex items-center gap-2 text-xs cursor-pointer" style={{ color: 'var(--color-text-secondary)' }}>
            <input
              type="checkbox"
              checked={filters.showOnlyStale}
              onChange={() => onChange({ showOnlyStale: !filters.showOnlyStale })}
            />
            <AlertTriangle size={12} style={{ color: '#ef4444' }} />
            Stale objectives ({staleCounts})
          </label>
        </div>
      </div>
    </aside>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────────

function FilterSection({
  icon: Icon,
  label,
  children,
}: {
  icon: typeof Filter;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center gap-1 text-xs font-medium mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
        <Icon size={12} />
        {label}
      </div>
      {children}
    </div>
  );
}

const selectStyle: React.CSSProperties = {
  width: '100%',
  fontSize: 11,
  padding: '4px 6px',
  borderRadius: 6,
  background: 'var(--color-bg-secondary)',
  border: '1px solid var(--color-border)',
  color: 'var(--color-text)',
};

function pillStyle(active: boolean): React.CSSProperties {
  return {
    fontSize: 11,
    padding: '3px 8px',
    borderRadius: 6,
    width: '100%',
    textAlign: 'left' as const,
    background: active ? 'var(--color-accent-muted, rgba(59,130,246,0.1))' : 'transparent',
    color: active ? 'var(--color-accent)' : 'var(--color-text-secondary)',
    border: 'none',
    cursor: 'pointer',
  };
}
