import type { LegalCheck } from '../api/types';

/** Human-readable status of a legal check; every result stays a candidate for the judge. */
export function legalCheckStatusLabel(status: LegalCheck['status']): string {
  switch (status) {
    case 'possible_violation':
      return 'Возможное нарушение · требует проверки';
    case 'insufficient_data':
      return 'Недостаточно данных';
    default:
      return 'Кандидат · требует проверки';
  }
}

/** Only absolute http(s) sources are rendered as links; anything else stays plain text. */
export function legalCheckSourceUrl(source: string): string | null {
  return /^https?:\/\//.test(source) ? source : null;
}
