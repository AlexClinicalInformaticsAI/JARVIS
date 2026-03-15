import type { ColorLevel } from '../../types/curriculum';
import { COMPETENCY_COLORS, COMPETENCY_LABELS, EXPOSURE_COLORS, EXPOSURE_LABELS } from '../../types/curriculum';

interface Props {
  level: ColorLevel;
  axis: 'exposure' | 'competency';
  size?: 'sm' | 'md';
}

export function CompetencyBadge({ level, axis, size = 'sm' }: Props) {
  const colors = axis === 'exposure' ? EXPOSURE_COLORS : COMPETENCY_COLORS;
  const labels = axis === 'exposure' ? EXPOSURE_LABELS : COMPETENCY_LABELS;
  const color = colors[level];
  const label = labels[level];
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
      title={`${axis === 'exposure' ? 'Exposure' : 'Competency'}: ${label}`}
    >
      <span
        className="rounded-full inline-block"
        style={{ width: dot, height: dot, background: color }}
      />
      {label}
    </span>
  );
}

/** Compact dual-dot showing both exposure and competency at a glance. */
export function DualDot({
  exposure,
  competency,
  size = 10,
}: {
  exposure: ColorLevel;
  competency: ColorLevel;
  size?: number;
}) {
  return (
    <span
      className="inline-flex items-center gap-0.5"
      title={`Exposure: ${EXPOSURE_LABELS[exposure]} | Competency: ${COMPETENCY_LABELS[competency]}`}
    >
      <span
        className="rounded-full"
        style={{ width: size, height: size, background: EXPOSURE_COLORS[exposure] }}
      />
      <span
        className="rounded-full"
        style={{ width: size, height: size, background: COMPETENCY_COLORS[competency] }}
      />
    </span>
  );
}
