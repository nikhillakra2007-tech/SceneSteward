'use client';

import { useEffect, useRef } from 'react';

/**
 * Scroll-linked word-by-word reveal. Each word lifts from a dim ghost to
 * full ink as the block travels up the viewport, like a line being read
 * aloud. Writes opacity straight to the DOM (no React re-render per
 * frame), rAF-throttled, passive listeners. Reduced-motion never arms:
 * the CSS guard keeps every word at full opacity.
 */
export default function TextReveal({ text, className = '' }: { text: string; className?: string }) {
  const ref = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const words = Array.from(el.querySelectorAll<HTMLSpanElement>('.tr-word'));
    if (!words.length) return;

    let raf = 0;
    let ticking = false;
    const update = () => {
      ticking = false;
      const r = el.getBoundingClientRect();
      const vh = window.innerHeight || 1;
      const start = vh * 0.9;
      const end = vh * 0.32;
      const p = Math.min(1, Math.max(0, (start - r.top) / (start - end)));
      const n = words.length;
      for (let i = 0; i < n; i++) {
        const wp = Math.min(1, Math.max(0, p * (n + 1.5) - i));
        words[i].style.opacity = (0.14 + 0.86 * wp).toFixed(3);
      }
    };
    const onScroll = () => {
      if (!ticking) {
        ticking = true;
        raf = requestAnimationFrame(update);
      }
    };

    update();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      cancelAnimationFrame(raf);
    };
  }, [text]);

  return (
    <p ref={ref} className={`text-reveal ${className}`.trim()}>
      {text.split(' ').map((w, i) => (
        <span className="tr-word" key={i}>
          {w}
          {'\u00A0'}
        </span>
      ))}
    </p>
  );
}
