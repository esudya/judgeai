import { useRef, useState, type DragEvent } from 'react';
import type { CaseAnalysis, CaseFile } from '../api/types';
import { FileChip, FileTile } from '../components/FileTile';
import { Icon, IconTile, type IconName } from '../components/Icon';
import { LogoMark } from '../components/Logo';
import { SentenceScale } from '../components/SentenceScale';
import { plural } from '../lib/format';
import { ACCEPT } from './Composer';
import { legalCheckSourceUrl, legalCheckStatusLabel } from './legalCheckPresentation';

const SUGGESTIONS: [string, string, string, IconName][] = [
  ['Подготовить проект приговора', 'Квалификация, наказание и текст', '#0066ff', 'doc'],
  ['Проверить квалификацию', 'Статья, часть и спорные признаки', '#141414', 'scales'],
  ['Найти схожие приговоры', 'Практика по той же статье', '#e5480f', 'cmp'],
  ['Оценить позицию защиты', 'Смягчающие обстоятельства и риски', '#0f8a52', 'shield'],
];

export function NewCaseScreen({ onFiles }: { onFiles: (list: FileList | null) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDrag(false);
    onFiles(e.dataTransfer.files);
  };
  return (
    <div className="fade-in screen-new">
      <LogoMark size={56} color="#141414" />
      <div>
        <h1 className="screen-h1">С каким делом работаем?</h1>
        <p className="screen-lead">Загрузите материалы — получите квалификацию, проект приговора и сверку с практикой.</p>
      </div>
      <button
        type="button"
        className={`btn-soft dropzone ${drag ? 'drag' : ''}`}
        onClick={() => input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
      >
        <span className="dropzone-icon">
          <Icon name="upload" size={26} strokeWidth={1.6} />
        </span>
        <span style={{ fontWeight: 600 }}>Перетащите материалы дела или выберите файлы</span>
        <span className="muted-14">PDF, DOCX, TXT, MD · 50 MB per file</span>
      </button>
      <input ref={input} type="file" multiple accept={ACCEPT} hidden onChange={(e) => onFiles(e.target.files)} />
      <div className="sug-grid">
        {SUGGESTIONS.map(([title, text, bg, icon]) => (
          <button key={title} type="button" className="sug" onClick={() => onFiles(null)}>
            <IconTile name={icon} bg={bg} size={36} iconSize={18} />
            <span className="sug-text">
              <span className="sug-title">{title}</span>
              <span className="sug-sub">{text}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function fileMeta(f: CaseFile): string {
  if (!f.pages) return 'загружен · ожидает анализа';
  return `${f.pages} стр. · ${f.recognition === 'partial' ? 'распознано частично' : 'распознано'}`;
}

export function AttachScreen({ files, onRemove }: { files: CaseFile[]; onRemove: (name: string) => void }) {
  const pages = files.reduce((s, f) => s + f.pages, 0);
  const partial = files.filter((f) => f.recognition === 'partial');
  return (
    <div className="fade-in screen-attach">
      <div className="attach-head">
        <h1 className="screen-h2">Материалы дела</h1>
        <span className="muted-14">
          {files.length} {plural(files.length, ['файл', 'файла', 'файлов'])} · {pages} {plural(pages, ['страница', 'страницы', 'страниц'])}
        </span>
      </div>
      <ul className="file-list">
        {files.map((f) => (
          <li key={f.name} className="file-row">
            <FileTile ext={f.ext} size={40} />
            <div className="file-text">
              <span className="file-name">{f.name}</span>
              <span className={`file-meta ${f.recognition === 'partial' ? 'warn' : ''}`}>{fileMeta(f)}</span>
            </div>
            <button type="button" aria-label={`Удалить файл ${f.name}`} className="btn btn-soft btn-icon" onClick={() => onRemove(f.name)}>
              <Icon name="close" size={16} strokeWidth={2} />
            </button>
          </li>
        ))}
      </ul>
      {partial.map((f) => (
        <div key={f.name} className="warn-box" role="note">
          <Icon name="warning" size={18} strokeWidth={2} color="#b54708" />
          <span>
            <strong>{f.name}</strong> распознана частично. Анализ возможен, но факт возмещения ущерба лучше подтвердить более чётким сканом.
          </span>
        </div>
      ))}
    </div>
  );
}

interface Step {
  label: string;
  done: boolean;
  active: boolean;
}

export function ThreadScreen({ analysis, files, thinking, steps, prompt }: { prompt?: string; analysis: CaseAnalysis | null; files: CaseFile[]; thinking: boolean; steps: Step[] }) {
  return (
    <div className="thread">
      <div className="thread-user">
        <div className="bubble">
          <span>{analysis?.prompt || prompt}</span>
          <div className="chips">
            {files.slice(0, 3).map((f) => (
              <FileChip key={f.name} name={f.name} ext={f.ext} />
            ))}
          </div>
        </div>
      </div>
      {thinking ? <Thinking steps={steps} /> : analysis && <Result a={analysis} />}
    </div>
  );
}

function Thinking({ steps }: { steps: Step[] }) {
  return (
    <div className="fade-in thread-ai" aria-live="polite">
      <LogoMark size={36} color="#141414" knocking />
      <div className="steps">
        <span className="steps-title">Анализирую материалы дела</span>
        {steps.map((s) => (
          <div key={s.label} className="step-row">
            {s.done && <Icon name="check" size={16} strokeWidth={2.4} />}
            {s.active && <span className="spin" style={{ margin: '0 2px' }} />}
            {!s.done && !s.active && (
              <span className="pending-slot">
                <span />
              </span>
            )}
            <span className={s.done ? 'step-done' : s.active ? 'step-active' : 'step-pending'}>{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Result({ a }: { a: CaseAnalysis }) {
  const [variant, setVariant] = useState(0);
  const current = a.variants[variant];
  const { documents, pages, seconds } = a.stats;
  return (
    <div className="fade-in thread-ai">
      <LogoMark size={36} color="#141414" />
      <div className="result">
        <span className="result-stats">
          Проанализировано {documents} {plural(documents, ['документ', 'документа', 'документов'])} · {pages} {plural(pages, ['страница', 'страницы', 'страниц'])} · {seconds}{' '}
          {plural(seconds, ['секунда', 'секунды', 'секунд'])}
        </span>
        {(a.warnings ?? []).map(w => <div key={w} className="warn-box" role="note">{w}</div>)}
        <p>{a.fabula}</p>

        <div className="grid-2">
          {a.qualification && <div className="card">
            <div className="eyebrow">Квалификация</div>
            <div className="card-title">{a.qualification.article}</div>
            <div className="card-sub">{a.qualification.title}</div>
          </div>}
          {a.draft && <div className="card card-col">
            <div className="eyebrow">Проект приговора</div>
            <div className="doc-row">
              <FileTile ext="DOC" size={44} />
              <div style={{ minWidth: 0 }}>
                <div className="doc-name">{a.draft.filename}</div>
                <div className="doc-meta">{a.draft.note}</div>
              </div>
            </div>
            {/* TODO(api): download link */}
            <button type="button" className="btn btn-ink small-btn" disabled title="Export is not implemented">
              <Icon name="download" size={14} strokeWidth={2.2} />
              Скачать
            </button>
          </div>}
        </div>

        {a.scale && <SentenceScale scale={a.scale} legend="plain" />}

        <div className="grid-2">
          <div className="soft-card">
            <span className="eyebrow">Смягчающие обстоятельства</span>
            {a.mitigating.map((m) => (
              <span key={m.name}>
                <strong>{m.name}</strong> — {m.norm}
              </span>
            ))}
          </div>
          <div className="soft-card">
            <span className="eyebrow">Отягчающие обстоятельства</span>
            <span>{a.aggravating}</span>
            <span className="eyebrow" style={{ marginTop: 4 }}>
              Личность
            </span>
            <span>{a.personality}</span>
          </div>
        </div>

        {current && <div className="variants">
          <div className="variants-head">
            <span className="eyebrow" style={{ color: '#adadad' }}>
              Варианты наказания
            </span>
            <div role="group" aria-label="Вариант наказания" className="variant-tabs">
              {a.variants.map((v, i) => (
                <button key={v.label} type="button" aria-pressed={variant === i} onClick={() => setVariant(i)}>
                  {v.label}
                </button>
              ))}
            </div>
          </div>
          <span className="variant-title">{current.title}</span>
          <span className="variant-details">{current.details}</span>
          <span className="variant-why">{current.rationale}</span>
        </div>}

        {a.similar.length > 0 && <div className="similar">
          <div className="similar-head">
            <span className="eyebrow">Схожие приговоры</span>
            {/* TODO(api): full list page */}
            <a href="#" onClick={(e) => e.preventDefault()} className="similar-all">
              Показать все
            </a>
          </div>
          {a.similar.map((s) => (
            <div key={s.punishment} className="similar-row">
              <div className="similar-text">
                <span className="similar-title">{s.punishment}</span>
                <span className="similar-meta">
                  {s.court} · {s.match}
                </span>
              </div>
              <span className="similar-bar" aria-hidden="true">
                <span style={{ width: `${s.score}%` }} />
              </span>
              <span className="similar-score">{s.score}%</span>
            </div>
          ))}
        </div>

        }
        {(a.legalChecks ?? []).map(check => {
          const sourceUrl = legalCheckSourceUrl(check.source);
          return <section key={check.norm} className={`legal-check legal-check--${check.status}`}>
            <div className="eyebrow">{check.norm} · {legalCheckStatusLabel(check.status)}</div>
            {check.value && <strong>{check.value.replaceAll('_', ' ')}</strong>}
            <p>{check.explanation}</p>
            {check.evidence.map(quote => <blockquote key={quote}>{quote}</blockquote>)}
            <p className="legal-check-source">
              Источник: {sourceUrl ? <a href={sourceUrl} target="_blank" rel="noreferrer">{sourceUrl}</a> : check.source}
            </p>
          </section>;
        })}
        {/* TODO(api): follow-up prompts */}
        <div className="followups">
          <button type="button" className="btn btn-soft btn-xs" disabled title="Not implemented">
            Сравнить с практикой региона
          </button>
          <button type="button" className="btn btn-soft btn-xs" disabled title="Not implemented">
            Позиция защиты
          </button>
          <button type="button" className="btn btn-soft btn-xs" disabled title="Not implemented">
            Подробнее об обстоятельствах
          </button>
        </div>
      </div>
    </div>
  );
}
