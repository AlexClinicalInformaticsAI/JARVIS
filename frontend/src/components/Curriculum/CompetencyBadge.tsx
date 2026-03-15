import type { CompetencyLevel } from '../../types/curriculum';
import { COMPETENCY_COLORS, COMPETENCY_LABELS } from '../../types/curriculum';

interface Props {
  level: CompetencyLevel;
  size?: 'sm' | 'md';
}

export function CompetencyBadge({ level, size = 'sm' }: Props) {
  const color = COMPETENCY_COLORS[level];
  const label = COMPETENCY_LABELS[level];
  const px = size === 'sm' ? 8 : 12;
  const dot = size === 'sm' ? 8 : 10;

  return (
    <span
      className="inline-flex items-center gap-1 rounded-full font-medium"
      style={{
        fontSize: size === 'sm' ? 10 : 12,
        padding: `2px ${px}px`,
        background: `${color}18`,
        color,
        border: `1px solid ${color}40`,
      }}
      title={label}
    >
      <span
        className="rounded-full inline-block"
        style={{ width: dot, height: dot, background: color }}
      />
      {label}
    </span>
  );
}
