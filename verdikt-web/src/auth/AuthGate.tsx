import { useEffect, useState, type ReactNode } from 'react';
import { auth, AuthenticationError, type AuthUser } from '../api/client';
import { LogoMark } from '../components/Logo';
import './auth.css';

export function AuthGate({children}: {children: (user: AuthUser, signOut: () => Promise<void>) => ReactNode}) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [checking, setChecking] = useState(true);
  const [retry, setRetry] = useState(0);
  const [connectionError, setConnectionError] = useState('');
  useEffect(() => {
    let current = true;
    setChecking(true);
    const expired = () => { setUser(null); setConnectionError(''); };
    window.addEventListener('judgeai:unauthorized', expired);
    void auth.me().then(next => { if (current) { setUser(next); setConnectionError(''); } })
      .catch(error => { if (current && !(error instanceof AuthenticationError)) setConnectionError('Cannot connect to the server. Try again.'); })
      .finally(() => { if (current) setChecking(false); });
    return () => { current = false; window.removeEventListener('judgeai:unauthorized', expired); };
  }, [retry]);

  if (checking) return <div className="auth-status" role="status">Checking your session…</div>;
  if (connectionError) return <div className="auth-status" role="alert"><p>{connectionError}</p><button className="btn btn-ink" onClick={() => setRetry(n => n + 1)}>Retry connection</button></div>;
  if (user) return children(user, async () => { await auth.logout(); setUser(null); });
  return <Login onLogin={setUser} />;
}

function Login({onLogin}: {onLogin: (user: AuthUser) => void}) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  return <main className="auth-page">
    <a href="/" className="auth-brand"><LogoMark size={30} /><span>Вердикт</span></a>
    <section className="auth-panel" aria-labelledby="login-title">
      <p className="auth-eyebrow">Your private workspace</p>
      <h1 id="login-title">Sign in to your cases.</h1>
      <p className="auth-intro">Review documents and continue your analysis in one place.</p>
      <form onSubmit={async event => {
        event.preventDefault();
        if (pending) return;
        setPending(true); setError('');
        try { const user = await auth.login(username, password); setPassword(''); onLogin(user); }
        catch (cause) { setError(cause instanceof Error ? cause.message : 'Cannot sign in'); setPassword(''); }
        finally { setPending(false); }
      }}>
        <label htmlFor="username">Username</label>
        <input id="username" name="username" autoComplete="username" autoCapitalize="none" spellCheck={false}
          required maxLength={80} value={username} onChange={event => setUsername(event.target.value)} disabled={pending} />
        <label htmlFor="password">Password</label>
        <input id="password" name="password" type="password" autoComplete="current-password" required
          maxLength={1024} value={password} onChange={event => setPassword(event.target.value)} disabled={pending}
          aria-describedby={error ? 'login-error' : undefined} />
        {error && <p id="login-error" className="auth-error" role="alert">{error}</p>}
        <button type="submit" className="btn btn-ink btn-md" disabled={pending}>{pending ? 'Signing in…' : 'Sign in'}</button>
      </form>
      <p className="auth-help">Need access? Ask your workspace administrator for an account.</p>
    </section>
    <footer className="auth-footer">A second opinion for a considered decision.</footer>
  </main>;
}
