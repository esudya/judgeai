// Single entry point for data. Today everything comes from mocks.
// TODO(api): when the backend exposes the analysis shape, implement the real branch:
//   listCases   -> GET  /api/chats
//   getAnalysis -> GET  /api/chats/{id}/messages  (last assistant message .analysis)
//   sendCase    -> POST /api/chats/{id}/messages  (multipart: content, files[])
import { mockAnalysis, mockCases, mockFiles, mockSteps } from './mock';
import type { AnalysisStep, CaseAnalysis, CaseFile, CaseSummary } from './types';

export const api = {
  listCases(): CaseSummary[] {
    return mockCases;
  },
  getFiles(_caseId: string): CaseFile[] {
    return mockFiles;
  },
  getSteps(): AnalysisStep[] {
    return mockSteps;
  },
  getAnalysis(_caseId: string): CaseAnalysis {
    return mockAnalysis;
  },
};
