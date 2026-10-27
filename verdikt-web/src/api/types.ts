// Domain types for the cabinet UI.
// Mapping to the backend (judgeai/judgeai, src/db/models.py):
//   CaseSummary  ~ Chat
//   CaseFile     ~ Attachment
//   CaseAnalysis ~ Message.analysis (assistant message) — shape not yet agreed with backend.

export type CaseStatus = 'ready' | 'busy' | 'draft' | 'failed';
export type CaseGroup = 'Сегодня' | 'Вчера' | 'Ранее';

export interface CaseSummary {
  id: string;
  title: string;
  group: CaseGroup;
  status: CaseStatus;
  /** Secondary line in the sidebar, e.g. "8 окт. · проект готов". */
  meta: string;
}

export type FileExt = 'PDF' | 'DOC' | 'JPG' | 'TXT';

export interface CaseFile {
  name: string;
  ext: FileExt;
  pages: number;
  /** "partial" = OCR could not read everything; the UI shows a warning. */
  recognition: 'ok' | 'partial' | 'empty' | 'error' | 'unsupported';
}

/** All terms are in months; the scale is drawn from 0 to sanctionMaxMonths. */
export interface SentenceScale {
  sanctionMaxMonths: number;
  /** Upper limit after mitigating rules (e.g. ч. 1 ст. 62 УК РФ). */
  limitMonths: number | null;
  limitNorm: string | null;
  practiceMonths: [from: number, to: number] | null;
  avgSimilarMonths: number | null;
  recommendedMonths: number | null;
  withinSanction: boolean | null;
  extraNotes: string[];
}

export interface PunishmentVariant {
  label: string;
  title: string;
  details: string;
  rationale: string;
}

export interface SimilarVerdict {
  punishment: string;
  court: string;
  match: string;
  /** 0–100 */
  score: number;
}

export interface LegalCheck {
  norm: string;
  status: 'ok' | 'possible_violation' | 'insufficient_data';
  explanation: string;
  source: string;
  value: string | null;
  evidence: string[];
  needs_legal_review: boolean;
}

export interface CaseAnalysis {
  warnings?: string[];
  legalChecks?: LegalCheck[];
  stats: { documents: number; pages: number; seconds: number };
  prompt: string;
  fabula: string;
  qualification: { article: string; title: string } | null;
  draft: { filename: string; note: string } | null;
  scale: SentenceScale | null;
  mitigating: { name: string; norm: string }[];
  aggravating: string;
  personality: string;
  variants: PunishmentVariant[];
  similar: SimilarVerdict[];
}

export interface AnalysisStep {
  label: string;
}
