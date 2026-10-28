import type { CSSProperties } from 'react';
import type { SentenceScale as Scale } from '../api/types';
import { formatMonths, pctOf, plural } from '../lib/format';
import { Icon } from './Icon';
import './SentenceScale.css';

interface Props {
  scale: Scale;
  /** Play the one-shot intro animation (landing demo). */
  animated?: boolean;
  /** "swatch" = legend with color dots (landing), "plain" = text legend + extra notes (cabinet). */
  legend?: 'swatch' | 'plain';
}

export function sanctionLabel(maxMonths: number): string {
  const years = Math.round(maxMonths / 12);
  return `до ${years} ${plural(years, ['года', 'лет', 'лет'])}`;
}

/**
 * "Сверка с законом" card: sanction track, mitigation limit, practice band,
 * median of similar verdicts and the recommendation on one 0..max axis.
 */
export function SentenceScale({ scale, animated = false, legend = 'plain' }: Props) {
  const max = scale.sanctionMaxMonths;
  const limit = pctOf(scale.limitMonths ?? 0, max);
  const [pFrom, pTo] = scale.practiceMonths ?? [0, 0];
  const bandLeft = pctOf(pFrom, max);
  const bandWidth = pctOf(pTo, max) - bandLeft;
  const avg = pctOf(scale.avgSimilarMonths ?? 0, max);
  const rec = pctOf(scale.recommendedMonths ?? 0, max);
  const ticks = Array.from({ length: Math.floor(max / 12) + 1 }, (_, i) => i);
  const a = (cls: string) => (animated ? cls : undefined);
  const slideFrom = (x: string) => ({ ['--from' as string]: x }) as CSSProperties;

  const legendItems = [
    { swatch: 'track', text: `Санкция — ${sanctionLabel(max)}` },
    ...(scale.limitMonths !== null ? [{ swatch: 'limit', text: `Предел по ${scale.limitNorm} — ${formatMonths(scale.limitMonths)}` }] : []),
    ...(scale.practiceMonths ? [{ swatch: 'band', text: `Практика по схожим делам — ${formatMonths(pFrom)} – ${formatMonths(pTo)}` }] : []),
  ];

  return (
    <div className="scale-card">
      <div className="scale-head">
        <div className="eyebrow">Сверка с законом · лишение свободы, лет</div>
        {scale.withinSanction && (
          <span className={`badge ${a('fade-later') ?? ''}`}>
            <Icon name="check" size={12} strokeWidth={3} />В пределах санкции
          </span>
        )}
      </div>
      <div className="scale-plot" role="img" aria-label={legendItems.map(item => item.text).join('; ')}>
        <div className="scale-track" />
        {scale.limitMonths !== null && <div className={`scale-limit ${a('grow-now') ?? ''}`} style={{ width: `${limit}%` }} />}
        {scale.practiceMonths && <div className={`scale-band ${a('grow-now') ?? ''}`} style={{ left: `${bandLeft}%`, width: `${bandWidth}%`, animationDelay: animated ? '.45s' : undefined }} />}
        {scale.avgSimilarMonths !== null && <><div
          className={`scale-avg-label ${a('slide-now') ?? ''}`}
          style={{ left: `${avg}%`, ...(animated ? slideFrom(`translateX(calc(-50% - ${avg}cqw))`) : {}) }}
        >
          Медиана по схожим · {formatMonths(scale.avgSimilarMonths)}
        </div>
        <div className={`scale-avg-dot ${a('slide-now') ?? ''}`} style={{ left: `${avg}%`, ...(animated ? slideFrom(`translateX(-${avg}cqw)`) : {}) }} /></>}
        {scale.recommendedMonths !== null && <><div className={`scale-rec-dot ${a('pop-now') ?? ''}`} style={{ left: `${rec}%` }} />
        <div className={`scale-rec-label ${a('fade-later') ?? ''}`} style={{ left: `${rec}%` }}>
          Рекомендация · {formatMonths(scale.recommendedMonths)}
        </div></>}
      </div>
      <div className="scale-ticks" aria-hidden="true">
        {ticks.map((t) => (
          <span key={t}>{t}</span>
        ))}
      </div>
      <div className="scale-legend">
        {legend === 'swatch'
          ? legendItems.map((l) => (
              <span key={l.swatch} className="legend-item">
                <span className={`legend-dot legend-${l.swatch}`} />
                {l.text}
              </span>
            ))
          : [...legendItems.slice(0, 2), ...scale.extraNotes.map((n) => ({ swatch: n, text: n }))].map((l) => <span key={l.swatch}>{l.text}</span>)}
      </div>
    </div>
  );
}
