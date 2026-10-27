import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import type { CaseFile, FileExt } from '../api/types';
import { Icon } from '../components/Icon';
import { Composer } from './Composer';
import { AttachScreen, NewCaseScreen, ThreadScreen } from './screens';
import { SettingsScreen } from './Settings';
import { Sidebar } from './Sidebar';
import './cabinet.css';

export type CabinetView = 'new' | 'attach' | 'thinking' | 'result' | 'settings';

export interface CabinetRoute {
  view: CabinetView;
  caseId: string;
}

const VIEWS: CabinetView[] = ['new', 'attach', 'thinking', 'result', 'settings'];
const DEFAULT_CASE = 'c1';

/**
 * /app -> result of the first case; /app/<view>;
 * /app/case/<id> -> that case (analysis if it is still running);
 * /app/case/<id>/analysis -> analysis in progress; /app/case/<id>/result -> result.
 */
export function parseCabinetPath(path: string): CabinetRoute {
  const parts = path.split('/').filter(Boolean).slice(1);
  if (parts[0] === 'case' && parts[1]) {
    const c = api.listCases().find((x) => x.id === parts[1]);
    const running = parts[2] === 'analysis' || (parts[2] !== 'result' && c?.status === 'busy');
    return { view: running ? 'thinking' : 'result', caseId: c?.id ?? DEFAULT_CASE };
  }
  const view = VIEWS.find((v) => v === parts[0]) ?? 'result';
  return { view, caseId: DEFAULT_CASE };
}

function routeToPath({ view, caseId }: CabinetRoute): string {
  if (view === 'thinking') return `/app/case/${caseId}/analysis`;
  // Explicit "/result" so a case whose stored status is still "busy" does not re-enter the analysis.
  if (view === 'result') return caseId === DEFAULT_CASE ? '/app' : `/app/case/${caseId}/result`;
  return `/app/${view}`;
}

/** Thinking timeline (ms): each of the steps takes STEP_MS; the result opens at THINK_TOTAL. */
const STEP_MS = 1100;
const DEFAULT_PROMPT = 'Подготовь проект приговора, учти явку с повинной';
const THINK_TOTAL = 4600;

function extOf(name: string): FileExt {
  const e = name.split('.').pop()?.toLowerCase() ?? '';
  if (e === 'pdf') return 'PDF';
  if (e === 'doc' || e === 'docx' || e === 'rtf') return 'DOC';
  return 'JPG';
}

interface Props {
  route: CabinetRoute;
  onNavigate: (to: string, replace?: boolean) => void;
}

export function Cabinet({ route, onNavigate }: Props) {
  const cases = api.listCases();
  const steps = api.getSteps();
  const { view, caseId } = route;
  const analysis = api.getAnalysis(caseId);
  const [files, setFiles] = useState<CaseFile[]>(() => api.getFiles(caseId));
  const [prompt, setPrompt] = useState(() => (route.view === 'attach' ? DEFAULT_PROMPT : ''));
  const [think, setThink] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const go = (next: Partial<CabinetRoute>) => {
    setSidebarOpen(false);
    onNavigate(routeToPath({ view, caseId, ...next }));
  };

  // Analysis progress on mocks. TODO(api): drive from backend status instead of a timer.
  // The completion check lives inside the interval: a separate effect would read the previous run's
  // `think` (still >= THINK_TOTAL) in the same commit and skip the analysis entirely.
  useEffect(() => {
    if (view !== 'thinking') return;
    let elapsed = 0;
    setThink(0);
    const id = window.setInterval(() => {
      elapsed += 100;
      setThink(elapsed);
      if (elapsed >= THINK_TOTAL) {
        window.clearInterval(id);
        onNavigate(routeToPath({ view: 'result', caseId }), true);
      }
    }, 100);
    return () => window.clearInterval(id);
  }, [view, caseId, onNavigate]);

  const active = cases.find((c) => c.id === caseId) ?? cases[0];
  const isThread = view === 'result' || view === 'thinking';
  const headerTitle = view === 'settings' ? 'Аккаунт' : isThread ? active.title : 'Новое дело';

  const stepState = useMemo(
    () =>
      steps.map((s, i) => {
        const s0 = i * STEP_MS;
        const done = think >= s0 + STEP_MS;
        return { label: s.label, done, active: !done && think >= s0 };
      }),
    [steps, think],
  );

  const addFiles = (list: FileList | null) => {
    if (list && list.length) {
      const added = Array.from(list).map<CaseFile>((f) => ({ name: f.name, ext: extOf(f.name), pages: 0, recognition: 'ok' }));
      setFiles((prev) => [...prev, ...added]);
    }
    // Prefill the request as in the design; the user can edit it before sending.
    setPrompt((p) => p || DEFAULT_PROMPT);
    if (view !== 'attach') go({ view: 'attach' });
  };

  return (
    <div className="cab">
      <Sidebar
        cases={cases}
        activeId={isThread ? caseId : null}
        thinking={view === 'thinking'}
        settingsActive={view === 'settings'}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNew={() => go({ view: 'new' })}
        onPick={(c) => go({ view: c.status === 'busy' ? 'thinking' : 'result', caseId: c.id })}
        onSettings={() => go({ view: 'settings' })}
      />

      <main className="cab-main">
        <header className="cab-header">
          <div className="cab-header-title">
            <button type="button" className="btn btn-soft btn-icon cab-menu" aria-label="Открыть список дел" aria-expanded={sidebarOpen} onClick={() => setSidebarOpen(true)}>
              <Icon name="menu" size={18} />
            </button>
            <span className="cab-title">{headerTitle}</span>
            {view === 'thinking' && (
              <span className="badge">
                <span className="spin" />
                Анализ
              </span>
            )}
            {view === 'result' && <span className="badge">Проект готов</span>}
          </div>
          {view === 'result' && (
            <div className="cab-header-actions">
              <button type="button" className="btn btn-line btn-sm hide-sm">
                Материалы · {analysis.stats.documents}
              </button>
              {/* TODO(api): download the generated .docx */}
              <button type="button" className="btn btn-ink btn-sm" aria-label="Экспорт в DOCX">
                <Icon name="download" size={16} strokeWidth={2.2} />
                <span className="hide-sm" aria-hidden="true">Экспорт в DOCX</span>
              </button>
            </div>
          )}
        </header>

        <div className="cab-scroll">
          {view === 'new' && <NewCaseScreen onFiles={addFiles} />}
          {view === 'attach' && <AttachScreen files={files} onRemove={(name) => setFiles((p) => p.filter((f) => f.name !== name))} />}
          {isThread && <ThreadScreen analysis={analysis} files={files} thinking={view === 'thinking'} steps={stepState} />}
          {view === 'settings' && <SettingsScreen onCancel={() => go({ view: 'result', caseId: DEFAULT_CASE })} />}
        </div>

        {view !== 'settings' && (
          <Composer
            mode={view === 'thinking' ? 'thinking' : view === 'attach' ? 'attach' : 'idle'}
            files={files}
            value={prompt}
            onChange={setPrompt}
            onFiles={addFiles}
            onSend={() => go({ view: 'thinking', caseId: DEFAULT_CASE })}
            onStop={() => go({ view: 'attach' })}
          />
        )}
      </main>
    </div>
  );
}
