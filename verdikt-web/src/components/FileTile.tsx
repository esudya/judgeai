import type { FileExt } from '../api/types';

const BG: Record<FileExt, string> = { PDF: 'var(--red)', DOC: 'var(--blue)', JPG: 'var(--muted)' };

/** Square file-type badge ("PDF", "DOC", "JPG"); sizes follow the design (20/32/40/44 px). */
export function FileTile({ ext, size }: { ext: FileExt; size: 20 | 32 | 40 | 44 }) {
  const fontSize = { 20: 7, 32: 9, 40: 10, 44: 11 }[size];
  return (
    <span className="ftile" aria-hidden="true" style={{ width: size, height: size, background: BG[ext], fontSize }}>
      {ext}
    </span>
  );
}

export function FileChip({ name, ext }: { name: string; ext: FileExt }) {
  return (
    <span className="file-chip">
      <FileTile ext={ext} size={20} />
      {name}
    </span>
  );
}
