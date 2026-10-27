import { useEffect, useRef, useState, type RefObject } from 'react';

export function prefersReducedMotion(): boolean {
  return typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/** True while the element intersects the viewport (or once, with `once`). */
export function useInView<T extends Element>(threshold = 0.35, once = false): [RefObject<T | null>, boolean] {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === 'undefined') {
      setInView(true);
      return;
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          if (once) io.disconnect();
        } else if (!once) {
          setInView(false);
        }
      },
      { threshold },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold, once]);
  return [ref, inView];
}

/** 0→1 progress over `duration` ms, started once the element scrolls into view (after `delay`). */
export function useCountUp<T extends Element>(duration: number, delay = 250): [RefObject<T | null>, number] {
  const [ref, seen] = useInView<T>(0.5, true);
  const [p, setP] = useState(0);
  useEffect(() => {
    if (!seen) return;
    const dur = prefersReducedMotion() ? 1 : duration;
    let raf = 0;
    let t0: number | null = null;
    const step = (now: number) => {
      if (t0 === null) t0 = now;
      const next = Math.min(1, (now - t0) / dur);
      setP(next);
      if (next < 1) raf = requestAnimationFrame(step);
    };
    const timer = window.setTimeout(() => {
      raf = requestAnimationFrame(step);
    }, delay);
    return () => {
      window.clearTimeout(timer);
      cancelAnimationFrame(raf);
    };
  }, [seen, duration, delay]);
  return [ref, p];
}

/** Looping timeline clock in ms that only advances while `playing`. */
export function useTimeline(playing: boolean, total: number, tick = 40): number {
  const [t, setT] = useState(0);
  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => setT((prev) => (prev + tick >= total ? 0 : prev + tick)), tick);
    return () => window.clearInterval(id);
  }, [playing, total, tick]);
  return t;
}

/** Counter that increments every `ms` (wraps at `mod`). */
export function useTicker(ms: number, mod: number): number {
  const [n, setN] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setN((v) => (v + 1) % mod), ms);
    return () => window.clearInterval(id);
  }, [ms, mod]);
  return n;
}

/**
 * One-time scroll reveal: adds `.vk-ready` to <html> and `.is-in` to each
 * `.reveal/.rise/.wipe/.foot/.foot-word` element once it is seen. Without JS nothing is hidden.
 */
export function useScrollReveal(root: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = root.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;
    const targets = el.querySelectorAll('.reveal, .rise, .wipe, .foot, .foot-word');
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('is-in');
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: '0px 0px -8% 0px' },
    );
    targets.forEach((t) => io.observe(t));
    document.documentElement.classList.add('vk-ready');
    return () => {
      io.disconnect();
      document.documentElement.classList.remove('vk-ready');
    };
  }, [root]);
}

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
/** easeOutCubic on a clamped input. */
export const easeOut = (x: number) => 1 - Math.pow(1 - clamp01(x), 3);
