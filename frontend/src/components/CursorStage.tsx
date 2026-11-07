'use client';

import { useEffect, useRef, ReactNode } from 'react';

/**
 * Cursor-reactive 3D stage. Fine-pointer devices get a lerped tilt,
 * a cursor-following glare and parallax overlay chips (passed via `overlays`,
 * moved through the --px/--py custom properties). Touch and reduced-motion
 * users get the static frame - listeners are never attached for them.
 */
export default function CursorStage({ children, overlays }: { children: ReactNode; overlays?: ReactNode }) {
  const wrap = useRef<HTMLDivElement>(null);
  const inner = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const wrapEl = wrap.current;
    const innerEl = inner.current;
    if (!wrapEl || !innerEl) return;
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const target = { x: 0, y: 0, s: 1 };
    const cur = { x: 0, y: 0, s: 1 };
    let raf = 0;
    let running = false;

    const apply = () => {
      innerEl.style.transform = `rotateX(${(-cur.y * 7).toFixed(3)}deg) rotateY(${(cur.x * 9).toFixed(3)}deg) scale(${cur.s.toFixed(4)})`;
      wrapEl.style.setProperty('--px', cur.x.toFixed(4));
      wrapEl.style.setProperty('--py', cur.y.toFixed(4));
    };
    const tick = () => {
      cur.x += (target.x - cur.x) * 0.12;
      cur.y += (target.y - cur.y) * 0.12;
      cur.s += (target.s - cur.s) * 0.12;
      apply();
      if (Math.abs(target.x - cur.x) > 0.0006 || Math.abs(target.y - cur.y) > 0.0006 || Math.abs(target.s - cur.s) > 0.0006) {
        raf = requestAnimationFrame(tick);
      } else {
        running = false;
      }
    };
    const kick = () => { if (!running) { running = true; raf = requestAnimationFrame(tick); } };

    const onMove = (e: PointerEvent) => {
      if (e.buttons !== 0) return; // a carousel drag owns the gesture
      const r = wrapEl.getBoundingClientRect();
      const nx = ((e.clientX - r.left) / r.width) * 2 - 1;
      const ny = ((e.clientY - r.top) / r.height) * 2 - 1;
      target.x = Math.max(-1, Math.min(1, nx));
      target.y = Math.max(-1, Math.min(1, ny));
      target.s = 1.014;
      wrapEl.style.setProperty('--gx', (((e.clientX - r.left) / r.width) * 100).toFixed(2));
      wrapEl.style.setProperty('--gy', (((e.clientY - r.top) / r.height) * 100).toFixed(2));
      wrapEl.classList.add('cursor-on');
      kick();
    };
    const onLeave = () => {
      target.x = 0; target.y = 0; target.s = 1;
      wrapEl.classList.remove('cursor-on');
      kick();
    };

    wrapEl.addEventListener('pointermove', onMove);
    wrapEl.addEventListener('pointerleave', onLeave);
    return () => {
      wrapEl.removeEventListener('pointermove', onMove);
      wrapEl.removeEventListener('pointerleave', onLeave);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div className="cursor-stage" ref={wrap}>
      <div className="cursor-stage-inner" ref={inner}>
        {children}
        <div className="screen-glare" aria-hidden="true" />
      </div>
      {overlays}
    </div>
  );
}
