import { useCallback, useEffect, useRef, useState } from 'react';
import { api, fileExt, mapAnalysis, type Message, type AuthUser } from '../api/client';
import type { CaseAnalysis, CaseFile, CaseSummary } from '../api/types';
import { Icon } from '../components/Icon';
import { Composer } from './Composer';
import { AttachScreen, NewCaseScreen, ThreadScreen } from './screens';
import { SettingsScreen } from './Settings';
import { Sidebar } from './Sidebar';
import './cabinet.css';

export type CabinetView = 'new' | 'attach' | 'thinking' | 'result' | 'settings';
export interface CabinetRoute { view: CabinetView; caseId: string }

export function parseCabinetPath(path: string): CabinetRoute {
  const parts = path.split('/').filter(Boolean).slice(1);
  if (parts[0] === 'case' && parts[1]) {
    return {view: parts[2] === 'analysis' ? 'thinking' : 'result', caseId: parts[1]};
  }
  return {view: parts[0] === 'settings' ? 'settings' : parts[0] === 'attach' ? 'attach' : 'new', caseId:''};
}

interface Props { route: CabinetRoute; onNavigate: (to: string, replace?: boolean) => void; user: AuthUser; onSignOut: () => Promise<void> }
const STAGES = ['reading', 'searching', 'qualifying', 'checking'];
const LABELS = ['Reading documents', 'Searching precedents', 'Extracting facts', 'Checking legal rules'];

export function Cabinet({route, onNavigate, user: account, onSignOut}: Props) {
  const {view, caseId} = route;
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [analysis, setAnalysis] = useState<CaseAnalysis | null>(null);
  const [error, setError] = useState('');
  const [listError, setListError] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(false);
  const [useKnowledge, setUseKnowledge] = useState(false);
  const [retry, setRetry] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const draftId = useRef<string | null>(null);
  const sendingRef = useRef(false);
  const operation = useRef(0);
  useEffect(() => {
    operation.current += 1;
    sendingRef.current = false;
    setSending(false);
  }, [caseId, view]);
  const refreshCases = useCallback(async () => {
    try { setCases(await api.listCases()); setListError(''); }
    catch (e) { setListError(e instanceof Error ? e.message : 'Cannot load cases'); }
  }, []);
  useEffect(() => { void refreshCases(); }, [refreshCases]);

  useEffect(() => {
    setMessages([]); setAnalysis(null); setError('');
    if (!caseId) { setLoading(false); return; }
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    setLoading(true);
    const poll = async () => {
      try {
        const next = await api.getMessages(caseId, controller.signal);
        if (controller.signal.aborted) return;
        setMessages(next); setLoading(false); setError('');
        const latest = [...next].reverse().find(m => m.role === 'assistant');
        setAnalysis(latest?.result ? mapAnalysis(latest.result) : null);
        if (latest?.status === 'failed') setError(latest.error || 'Analysis failed');
        if (latest?.status === 'pending' || latest?.status === 'running') {
          timer = setTimeout(poll, 1000);
        } else { void refreshCases(); }
      } catch (e) {
        if (controller.signal.aborted) return;
        setLoading(false);
        setError(e instanceof Error ? e.message : 'Cannot load analysis');
      }
    };
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [caseId, retry, refreshCases]);

  const assistant = [...messages].reverse().find(m => m.role === 'assistant');
  const user = [...messages].reverse().find(m => m.role === 'user');
  const busy = sending || assistant?.status === 'pending' || assistant?.status === 'running';
  const attachments: CaseFile[] = (user?.attachments ?? []).map(a => ({
    name:a.filename, ext:fileExt(a.filename), pages:a.page_count ?? 0, recognition:a.extraction_status,
  }));
  const pendingFiles: CaseFile[] = selectedFiles.map(f => ({name:f.name, ext:fileExt(f.name), pages:0, recognition:'ok'}));
  const active = cases.find(c => c.id === caseId);
  const stage = assistant?.stage ? STAGES.indexOf(assistant.stage) : -1;
  const steps = LABELS.map((label, i) => ({label, done: stage > i, active: stage === i}));
  const go = (to: string) => {
    operation.current += 1;
    sendingRef.current = false;
    setSending(false);
    setSidebarOpen(false);
    onNavigate(to);
  };
  const startNew = () => {
    draftId.current = null; setSelectedFiles([]); setPrompt(''); setError(''); go('/app');
  };
  const addFiles = (list: FileList | null) => {
    if (busy) return;
    if (list) setSelectedFiles(prev => [...prev, ...Array.from(list)]);
    if (!caseId) go('/app/attach');
  };
  const send = async () => {
    if (sendingRef.current || busy || (!prompt.trim() && !selectedFiles.length)) return;
    const token = ++operation.current;
    const initialPath = window.location.pathname;
    const isCurrent = () => operation.current === token && window.location.pathname === initialPath;
    sendingRef.current = true; setSending(true); setError('');
    try {
      const id = caseId || draftId.current || String((await api.createCase()).id);
      if (!caseId && isCurrent()) draftId.current = id;
      await api.sendCase(id, prompt, selectedFiles, useKnowledge);
      void refreshCases();
      if (!isCurrent()) return;
      setSelectedFiles([]); setPrompt(''); setRetry(n => n + 1);
      go(`/app/case/${id}/analysis`);
      void refreshCases();
    } catch (e) { if (isCurrent()) setError(e instanceof Error ? e.message : 'Cannot send case'); }
    finally { if (isCurrent()) { sendingRef.current = false; setSending(false); } }
  };

  return (
    <div className="cab">
      <Sidebar cases={cases} activeId={caseId || null} thinking={busy} settingsActive={view === 'settings'}
        open={sidebarOpen} onClose={() => setSidebarOpen(false)} onNew={startNew}
        onPick={c => { setSelectedFiles([]); setPrompt(''); go(`/app/case/${c.id}/result`); }}
        onSettings={() => go('/app/settings')} username={account.username} />
      <main className="cab-main">
        <header className="cab-header">
          <div className="cab-header-title">
            <button type="button" className="btn btn-soft btn-icon cab-menu" aria-label="Open cases"
              aria-expanded={sidebarOpen} onClick={() => setSidebarOpen(true)}><Icon name="menu" size={18} /></button>
            <span className="cab-title">{view === 'settings' ? 'Account' : active?.title || (caseId ? `Case ${caseId}` : 'New case')}</span>
            {busy && <span className="badge"><span className="spin" />Analysing</span>}
            {analysis && !busy && <span className="badge">Analysis ready</span>}
          </div>
          <button type="button" className="btn btn-line btn-sm" onClick={() => { void onSignOut().catch(() => setError("Cannot sign out. Try again.")); }}>Sign out</button>
          {analysis && <button type="button" className="btn btn-line btn-sm hide-sm" disabled title="DOCX export is not implemented">DOCX export · coming soon</button>}
        </header>
        <div className="cab-scroll">
          {listError && <div className="warn-box" role="alert">{listError}<button type="button" onClick={() => void refreshCases()}>Retry cases</button></div>}
          {error && <div className="warn-box" role="alert">{error}<button type="button" onClick={() => setRetry(n => n + 1)}>Reload</button></div>}
          {loading && <p role="status">Loading case…</p>}
          {view === 'settings' ? <SettingsScreen onCancel={() => go('/app')} /> : caseId ? (
            <>
              {busy || analysis ? <ThreadScreen prompt={user?.content || 'Uploaded documents'} analysis={analysis} files={attachments} thinking={busy} steps={steps} /> :
                !loading && !error && <p>No analysis yet. Add a request or upload a verdict.</p>}
              {selectedFiles.length > 0 && <AttachScreen files={pendingFiles} onRemove={name => setSelectedFiles(p => p.filter(f => f.name !== name))} />}
            </>
          ) : view === 'attach' || selectedFiles.length ? <AttachScreen files={pendingFiles} onRemove={name => setSelectedFiles(p => p.filter(f => f.name !== name))} /> : <NewCaseScreen onFiles={addFiles} />}
        </div>
        {view !== 'settings' && <>
          {caseId && !busy && <p className="cab-request-note">A new request uses only its own attachments. Attach previous documents again to include them.</p>}
          {account.is_admin && <label className="cab-knowledge"><input type="checkbox" checked={useKnowledge} disabled={busy} onChange={e => setUseKnowledge(e.target.checked)} />Search shared precedent library</label>}
          <Composer mode={busy ? 'thinking' : selectedFiles.length ? 'attach' : 'idle'} files={pendingFiles}
            value={prompt} onChange={setPrompt} onFiles={addFiles} onSend={() => void send()}
            onStop={() => go('/app')} />
        </>}
      </main>
    </div>
  );
}
