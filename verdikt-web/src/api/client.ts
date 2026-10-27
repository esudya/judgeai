import type { CaseAnalysis, CaseFile, CaseSummary, LegalCheck } from './types';

type WireScale = {
  sanction_max_months: number; limit_months: number | null; limit_norm: string | null;
  practice_months: [number, number] | null; avg_similar_months: number | null;
  recommended_months: number | null; within_sanction: boolean | null; extra_notes: string[];
};
export type WireAnalysis = Omit<CaseAnalysis, 'scale' | 'legalChecks'> & {
  schema_version: number; scale: WireScale | null; legal_checks?: LegalCheck[];
};
export interface Message {
  id: number; role: string; content: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed'; stage: string | null;
  error: string | null; result: WireAnalysis | null;
  attachments: { id: number; filename: string; page_count: number | null;
    extraction_status: CaseFile['recognition'] }[];
}
interface Chat { id: number; title: string | null; status: CaseSummary['status']; updated_at: string }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function mapAnalysis(a: WireAnalysis): CaseAnalysis {
  const s = a.scale;
  return { ...a, qualification: a.qualification ?? null, draft: a.draft ?? null,
    warnings: a.warnings ?? [], legalChecks: a.legal_checks ?? [],
    scale: s ? {sanctionMaxMonths: s.sanction_max_months, limitMonths: s.limit_months,
      limitNorm: s.limit_norm, practiceMonths: s.practice_months,
      avgSimilarMonths: s.avg_similar_months, recommendedMonths: s.recommended_months,
      withinSanction: s.within_sanction, extraNotes: s.extra_notes ?? []} : null };
}

export function fileExt(name: string): CaseFile['ext'] {
  const ext = name.split('.').pop()?.toLowerCase();
  return ext === 'pdf' ? 'PDF' : ext === 'docx' ? 'DOC' : ext === 'txt' || ext === 'md' ? 'TXT' : 'JPG';
}

export const api = {
  async listCases(): Promise<CaseSummary[]> {
    const chats = await request<Chat[]>('/chats');
    const labels = {draft: 'Draft', busy: 'Analysing', ready: 'Analysis ready', failed: 'Analysis failed'};
    return chats.map(c => ({id: String(c.id), title: c.title || 'Untitled case',
      group: 'Ранее', status: c.status, meta: labels[c.status]}));
  },
  createCase(): Promise<Chat> {
    return request('/chats', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({title:null})});
  },
  getMessages(id: string, signal?: AbortSignal): Promise<Message[]> {
    return request(`/chats/${encodeURIComponent(id)}/messages`, {signal});
  },
  sendCase(id: string, content: string, files: File[], useKnowledge = false): Promise<{assistant_message: Message}> {
    const body = new FormData();
    body.set('content', content);
    body.set('use_knowledge_base', String(useKnowledge));
    for (const file of files) body.append('files', file);
    return request(`/chats/${encodeURIComponent(id)}/messages`, {method:'POST', body});
  },
};
