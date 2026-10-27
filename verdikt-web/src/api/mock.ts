// Mock data copied from the design canvas (Cabinet.dc.html renderVals).
// Replace with real API calls in client.ts; components must not import this file directly.
import type { AnalysisStep, CaseAnalysis, CaseFile, CaseSummary } from './types';

export const mockCases: CaseSummary[] = [
  { id: 'c1', group: 'Сегодня', title: 'Кража, п. «в» ч. 2 ст. 158', meta: 'Проект готов', status: 'ready' },
  { id: 'c2', group: 'Сегодня', title: 'Мошенничество, ч. 3 ст. 159', meta: 'Идёт анализ', status: 'busy' },
  { id: 'c3', group: 'Вчера', title: 'Грабёж, ч. 1 ст. 161', meta: 'Черновик', status: 'draft' },
  { id: 'c4', group: 'Ранее', title: 'Нарушение ПДД, ч. 1 ст. 264', meta: '8 окт. · проект готов', status: 'ready' },
  { id: 'c5', group: 'Ранее', title: 'Присвоение, ч. 3 ст. 160', meta: '2 окт. · проект готов', status: 'ready' },
  { id: 'c6', group: 'Ранее', title: 'Побои, ст. 116.1', meta: '28 сент. · проект готов', status: 'ready' },
];

export const mockFiles: CaseFile[] = [
  { name: 'Обвинительное заключение.pdf', ext: 'PDF', pages: 38, recognition: 'ok' },
  { name: 'Протоколы допросов.pdf', ext: 'PDF', pages: 61, recognition: 'ok' },
  { name: 'Характеристика.docx', ext: 'DOC', pages: 2, recognition: 'ok' },
  { name: 'Расписка потерпевшего.jpg', ext: 'JPG', pages: 1, recognition: 'partial' },
];

export const mockSteps: AnalysisStep[] = [
  { label: 'Читаю материалы — 142 страницы' },
  { label: 'Квалифицирую деяние' },
  { label: 'Ищу схожие приговоры' },
  { label: 'Сверяю с санкцией статьи' },
];

export const mockAnalysis: CaseAnalysis = {
  stats: { documents: 7, pages: 142, seconds: 38 },
  prompt: 'Подготовь проект приговора. Подсудимый признал вину, написал явку с повинной, ущерб возместил полностью.',
  fabula:
    'Подсудимый тайно похитил ноутбук стоимостью 64 000 ₽ из квартиры потерпевшей. С учётом её дохода ущерб значительный. Похищенное возвращено, ущерб возмещён полностью (т. 1 л. д. 87).',
  qualification: {
    article: 'п. «в» ч. 2 ст. 158 УК РФ',
    title: 'Кража с причинением значительного ущерба гражданину. Средней тяжести.',
  },
  draft: { filename: 'Приговор.docx', note: 'Все части приговора · можно редактировать' },
  scale: {
    sanctionMaxMonths: 60,
    limitMonths: 40,
    limitNorm: 'ч. 1 ст. 62',
    practiceMonths: [11, 24],
    avgSimilarMonths: 14,
    recommendedMonths: 18,
    withinSanction: true,
    extraNotes: ['Условное осуждение по ст. 73 — допустимо'],
  },
  mitigating: [
    { name: 'Явка с повинной', norm: 'п. «и» ч. 1 ст. 61' },
    { name: 'Возмещение ущерба', norm: 'п. «к» ч. 1 ст. 61' },
    { name: 'Признание вины', norm: 'ч. 2 ст. 61' },
  ],
  aggravating: 'Не установлены (ст. 63 УК РФ).',
  personality: 'Ранее не судим, характеризуется положительно, трудоустроен.',
  variants: [
    {
      label: 'Основной',
      title: 'Лишение свободы 1 год 6 месяцев условно',
      details: 'Испытательный срок 2 года. Не менять место жительства без уведомления УИИ, являться на регистрацию.',
      rationale:
        'Учтены п. «и», «к» ч. 1 ст. 61, отсутствие отягчающих обстоятельств и положительная характеристика. Срок ниже предела ч. 1 ст. 62 и близок к среднему по схожим делам.',
    },
    {
      label: 'Исправительные работы',
      title: 'Исправительные работы 1 год',
      details: 'С удержанием 10% заработной платы в доход государства.',
      rationale: 'Менее строгий вид наказания из санкции. Ограничение ч. 1 ст. 62 применяется только к наиболее строгому виду.',
    },
    {
      label: 'Штраф',
      title: 'Штраф 100 000 ₽',
      details: 'В пределах санкции: до 200 000 ₽ или дохода за период до 18 месяцев.',
      rationale: 'Возможен с учётом имущественного положения и полного возмещения ущерба (ч. 3 ст. 46 УК РФ).',
    },
  ],
  similar: [
    { punishment: '1 год лишения свободы условно, испытательный срок 1 год', court: 'Районный суд · 2025', match: 'явка с повинной, полное возмещение', score: 94 },
    { punishment: '1 год 6 месяцев условно, испытательный срок 2 года', court: 'Городской суд · 2025', match: 'возмещение, положительная характеристика', score: 89 },
    { punishment: 'Исправительные работы 10 месяцев, удержание 10%', court: 'Районный суд · 2024', match: 'явка с повинной; ущерб возмещён частично', score: 81 },
  ],
};
