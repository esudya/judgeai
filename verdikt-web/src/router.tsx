import { useCallback, useEffect, useState, type AnchorHTMLAttributes, type MouseEvent } from 'react';

// Minimal history router: two areas (landing "/", cabinet "/app/*"), no dependency needed.
// In-page anchors (#how, #faq) keep working because only same-origin path links are intercepted.

function currentPath() {
  return window.location.pathname;
}

export function navigate(to: string, replace = false) {
  if (to === currentPath()) return;
  if (replace) window.history.replaceState(null, '', to);
  else window.history.pushState(null, '', to);
  window.dispatchEvent(new PopStateEvent('popstate'));
  window.scrollTo(0, 0);
}

export function usePath(): [string, (to: string, replace?: boolean) => void] {
  const [path, setPath] = useState(currentPath);
  useEffect(() => {
    const onPop = () => setPath(currentPath());
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);
  return [path, useCallback((to: string, replace?: boolean) => navigate(to, replace), [])];
}

/** <a> that navigates client-side for internal paths and falls back to normal behaviour otherwise. */
export function Link({ href = '/', onClick, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  const handle = (e: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(e);
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (!href.startsWith('/')) return;
    e.preventDefault();
    navigate(href);
  };
  return <a href={href} onClick={handle} {...rest} />;
}
