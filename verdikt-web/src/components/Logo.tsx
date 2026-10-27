interface LogoMarkProps {
  size?: number;
  color?: string;
  /** Animate the four "knuckles" (used as a thinking indicator). */
  knocking?: boolean;
  label?: string;
}

const KNUCKLES = [18, 35, 52, 69];

/** The "fist" mark from Logo.dc.html. Decorative unless `label` is given. */
export function LogoMark({ size = 32, color = 'currentColor', knocking = false, label }: LogoMarkProps) {
  const a11y = label ? { role: 'img', 'aria-label': label } : { 'aria-hidden': true as const };
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" style={{ flex: 'none', overflow: 'visible' }} {...a11y}>
      <g fill={color}>
        {KNUCKLES.map((x, i) => (
          <rect
            key={x}
            className={knocking ? 'knock' : undefined}
            style={knocking ? { animationDelay: `${i * 0.15}s` } : undefined}
            x={x}
            y={6}
            width={13}
            height={25}
            rx={5}
          />
        ))}
        <path d="M24 34H50V43Q50 48 45 48H18V40Q18 34 24 34Z" />
        <path d="M53 34H76Q82 34 82 40V50Q82 80 40 96Q34 98 34 92V74Q34 70 30 69Q18 66 18 56V51H45Q53 51 53 43Z" />
      </g>
    </svg>
  );
}

/** Mark with a configurable number of lit knuckles (the "How it works" steps). */
export function LogoSteps({ lit, size = 64, label }: { lit: number; size?: number; label: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" role="img" aria-label={label} style={{ overflow: 'visible' }}>
      {KNUCKLES.map((x, i) => (
        <rect key={x} className={i < lit ? 'lit' : undefined} x={x} y={6} width={13} height={25} rx={5} fill={i < lit ? '#ffffff' : '#3a3a3a'} />
      ))}
      <g fill="#ffffff">
        <path d="M24 34H50V43Q50 48 45 48H18V40Q18 34 24 34Z" />
        <path d="M53 34H76Q82 34 82 40V50Q82 80 40 96Q34 98 34 92V74Q34 70 30 69Q18 66 18 56V51H45Q53 51 53 43Z" />
      </g>
    </svg>
  );
}
