import { useEffect } from 'react';
import { Cabinet, parseCabinetPath } from './cabinet/Cabinet';
import { Landing } from './landing/Landing';
import { usePath } from './router';

export function App() {
  const [path, go] = usePath();
  const isCabinet = path === '/app' || path.startsWith('/app/');

  useEffect(() => {
    document.title = isCabinet ? 'Вердикт — личный кабинет' : 'Вердикт — ИИ-помощник судьи';
  }, [isCabinet]);

  if (isCabinet) return <Cabinet route={parseCabinetPath(path)} onNavigate={go} />;
  return <Landing />;
}
