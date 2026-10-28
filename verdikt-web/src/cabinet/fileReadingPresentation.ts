import type { CaseFile } from '../api/types';

type ReadingStatus = CaseFile['recognition'];

export function fileReadingLabel(file: Pick<CaseFile, 'pages' | 'recognition'>): string {
  const labels: Record<ReadingStatus, string> = {
    pending: 'Uploaded · waiting to be read',
    ok: 'Text read',
    partial: 'Partially read',
    empty: 'No readable text',
    error: 'Reading failed',
    unsupported: 'Unsupported format',
  };
  const label = labels[file.recognition];
  return file.pages ? `${file.pages} pages · ${label}` : label;
}

export function fileReadingWarning(status: ReadingStatus): string | null {
  switch (status) {
    case 'partial': return 'Text is incomplete. Review the reading warnings before using the analysis.';
    case 'empty': return 'No readable text was found. A scan may require OCR; provide a readable copy.';
    case 'error': return 'The file could not be read. Check the encoding or provide another copy.';
    case 'unsupported': return 'This file variant is not supported. Convert it to a supported format.';
    default: return null;
  }
}
