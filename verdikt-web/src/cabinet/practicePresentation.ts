import type { PracticeComparison, PrecedentSource } from '../api/types';
import { formatMonths } from '../lib/format.ts';

/** Matches MIN_PRECEDENTS in legal_core.rules.practice_comparison. */
const MIN_PRECEDENTS = 5;

export interface PracticeSummary {
  headline: string;
  basis: string;
  median: string | null;
  range: string | null;
  spread: string | null;
}

export function shareLabel(share: number | null): string {
  return share === null ? '—' : `${Math.round(share * 100)} %`;
}

const POSITION: Record<'below' | 'within' | 'above', string> = {
  below: 'ниже типичного диапазона',
  within: 'в пределах типичного диапазона',
  above: 'выше типичного диапазона',
};

/** Plain-language reading of the T28 comparison; the judge decides what it means. */
export function practiceSummary(p: PracticeComparison): PracticeSummary {
  const median = p.median_months === null ? null : formatMonths(p.median_months);
  const range = p.p25_months === null || p.p75_months === null
    ? null : `${formatMonths(p.p25_months)} – ${formatMonths(p.p75_months)}`;
  const spread = p.min_months === null || p.max_months === null
    ? null : `${formatMonths(p.min_months)} – ${formatMonths(p.max_months)}`;
  const basis = `Сроки известны в ${p.with_term} из ${p.total} сопоставимых приговоров`;
  let headline: string;
  if (p.total === 0) {
    headline = 'Сопоставимые приговоры в базе практики не найдены';
  } else if (!p.enough_data || p.position === null) {
    headline = `Недостаточно данных для вывода: ${p.with_term} из ${MIN_PRECEDENTS} нужных сроков`;
  } else {
    const draft = p.draft_months === null ? 'Срок проекта' : `Срок проекта ${formatMonths(p.draft_months)}`;
    headline = `${draft} — ${POSITION[p.position]}`;
  }
  return { headline, basis, median, range, spread };
}

export function precedentSourceNote(source: PrecedentSource | undefined): string | null {
  switch (source) {
    case 'text':
      return 'Карточки прецедентов ещё не построены — показан приблизительный поиск по тексту.';
    case 'none':
      return 'Похожие приговоры в базе практики не найдены.';
    default:
      return null;
  }
}
