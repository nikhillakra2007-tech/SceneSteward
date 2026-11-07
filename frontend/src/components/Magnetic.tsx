'use client';

import { useEffect, useRef, ReactNode } from 'react';

/**
 * Magnetic hover: the wrapped element drifts a few px toward the cursor
 * and lerps home on leave. Fine-pointer devices only; on touch and under
 * reduced-motion no listener is ever attached and the wrapper is inert.
 */
export default function Magnetic({ children, strength = 5 }: { children: ReactNode; strength?: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const target = { x: 0, y: 0 };
    const cur = { x: 0, y: 0 };
    let raf = 0;
    let running = false;

    const tick = () => {
      cur.x += (target.x - cur.x) * 0.16;
      cur.y += (target.y - cur.y) * 0.16;
      el.style.transform = `translate3d(${cur.x.toFixed(2)}px, ${cur.y.toFixed(2)}px, 0)`;
      if (Math.abs(target.x - cur.x) > 0.1 || Math.abs(target.y - cur.y) > 0.1) {
        raf = requestAnimationFrame(tick);
      } else {
        running = false;
        el.style.transform = '';
      }
    };
    const kick = () => {
      if (!running) {
        running = true;
        raf = requestAnimationFrame(tick);
      }
    };
    const onMove = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      target.x = ((e.clientX - (r.left + r.width / 2)) / (r.width / 2)) * strength;
      target.y = ((e.clientY - (r.top + r.height / 2)) / (r.height / 2)) * strength;
      kick();
    };
    const onLeave = () => {
      target.x = 0;
      target.y = 0;
      kick();
    };

    el.addEventListener('pointermove', onMove);
    el.addEventListener('pointerleave', onLeave);
    return () => {
      el.removeEventListener('pointermove', onMove);
      el.removeEventListener('pointerleave', onLeave);
      cancelAnimationFrame(raf);
    };
  }, [strength]);

  return (
    <div className="magnetic" ref={ref}>
      {children}
    </div>
  );
}
