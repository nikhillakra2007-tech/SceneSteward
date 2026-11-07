'use client';

import { useRef, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, ArrowLeft, ArrowUpRight, Play, X, ShieldCheck, ScanLine, Users, Check, Maximize2, MoveHorizontal } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { useTheme } from '@/lib/theme';

const SCREENS = [
  { id: 'workspace', label: 'Production workspace', number: '01', title: 'The whole production. One shared record.', body: 'Keep participants, releases, proposed uses and human reviews together. See what needs attention before a story leaves the edit.' },
  { id: 'consent', label: 'Participant consent', number: '02', title: 'A yes has boundaries. Keep them visible.', body: 'Track each use separately, from an interview recording to a festival trailer. A declined voice clone stays declined. An unanswered request stays unresolved.' },
  { id: 'analytics', label: 'Operational intelligence', number: '03', title: 'See the gaps before picture lock.', body: 'Discussion coverage, outstanding reviews and care tasks give your team a practical view of what still needs a conversation.' },
];

export default function HomePage() {
  const [active, setActive] = useState(0);
  const [drag, setDrag] = useState<number | null>(null);
  const [zoom, setZoom] = useState<string | null>(null);
  const theme = useTheme();
  const screen = SCREENS[active];
  const imgSrc = (id: string) => `/screens/${id}-${theme}.webp`;

  const gesture = useRef<{ startX: number; startT: number; lastX: number; lastT: number; width: number; dx: number; moved: boolean } | null>(null);
  const suppressClick = useRef(false);

  const goTo = (i: number) => setActive(Math.max(0, Math.min(SCREENS.length - 1, i)));

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    el.setPointerCapture(e.pointerId);
    gesture.current = { startX: e.clientX, startT: e.timeStamp, lastX: e.clientX, lastT: e.timeStamp, width: el.offsetWidth, dx: 0, moved: false };
  };
  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const g = gesture.current;
    if (!g) return;
    let dx = e.clientX - g.startX;
    // resistance past the ends
    if ((active === 0 && dx > 0) || (active === SCREENS.length - 1 && dx < 0)) dx *= 0.35;
    g.dx = dx;
    g.lastX = e.clientX;
    g.lastT = e.timeStamp;
    if (Math.abs(dx) > 7) g.moved = true;
    setDrag(dx);
  };
  const endGesture = (e: React.PointerEvent<HTMLDivElement>) => {
    const g = gesture.current;
    if (!g) return;
    gesture.current = null;
    const dt = Math.max(1, e.timeStamp - g.lastT);
    const velocity = Math.abs(e.clientX - g.lastX) / dt; // px per ms
    const far = Math.abs(g.dx) > g.width * 0.14;
    const flick = Math.abs(g.dx) > 28 && velocity > 0.45;
    if ((far || flick) && g.dx !== 0) goTo(active + (g.dx < 0 ? 1 : -1));
    if (g.moved) {
      suppressClick.current = true;
      window.setTimeout(() => { suppressClick.current = false; }, 0);
    }
    setDrag(null);
  };

  return (
    <div className="product-landing">
      <section className="landing-hero">
        <div className="landing-topline"><span><i /> BUILT FOR DOCUMENTARY TEAMS</span><span>THE PEOPLE BEHIND THE PICTURE</span></div>
        <div className="hero-copy">
          <p className="landing-eyebrow">Good stories start with trust.</p>
          <h1>Every frame has<br />a <em>human story.</em><span className="frame-corner" aria-hidden="true" /></h1>
          <div className="hero-bottom"><p>Make the film. Keep the promise.<br />Consent, participant care and human review,<br className="desktop-break" /> held together from first interview to final cut.</p><div className="hero-actions"><Link href="/projects" className="landing-button">Open workspace <ArrowUpRight size={17} /></Link><a href="#in-action" className="landing-text-link"><Play size={13} fill="currentColor" /> See it in action</a></div></div>
        </div>
        <div className="hero-rule"><span>SCENE / STEWARD</span><span>CONSENT IS A CONVERSATION, NOT A CHECKBOX.</span><span>EST. 2026</span></div>
      </section>

      <Reveal as="section" className="product-stage" delay={60}>
        <div id="in-action" style={{ scrollMarginTop: 90 }} />
        <div className="stage-heading"><div><span className="section-index">INSIDE SCENESTEWARD</span><h2>Less chasing paperwork.<br /><em>More caring for people.</em></h2></div><p>Explore the actual interface.<br />Swipe or drag through the screens.<br />Screens use fictional sample data.</p></div>
        <div className="screen-controls">
          <div className="screen-progress" aria-hidden="true"><span>{screen.number} / 0{SCREENS.length}</span><span className="bar"><i style={{ width: `${((active + 1) / SCREENS.length) * 100}%` }} /></span><span className="screen-progress-label">{screen.label}</span></div>
          <div className="screen-hint" aria-hidden="true"><MoveHorizontal size={13} /><span>DRAG · SWIPE</span></div>
          <div className="screen-arrows">
            <button type="button" onClick={() => goTo(active - 1)} disabled={active === 0} aria-label="Previous screenshot"><ArrowLeft size={15} /></button>
            <button type="button" onClick={() => goTo(active + 1)} disabled={active === SCREENS.length - 1} aria-label="Next screenshot"><ArrowRight size={15} /></button>
          </div>
        </div>
        <div className="screen-frame">
          <div className="screen-toolbar"><span className="window-dots"><i /><i /><i /></span><span>scenesteward / {screen.id}</span><button onClick={() => setZoom(screen.id)} aria-label={`Enlarge ${screen.label} screenshot`}><Maximize2 size={14} /><span>Expand</span></button></div>
          <div
            className={`screen-viewport${drag !== null ? ' dragging' : ''}`}
            role="region"
            aria-roledescription="carousel"
            aria-label="Product screenshots"
            tabIndex={0}
            onKeyDown={e => { if (e.key === 'ArrowLeft') goTo(active - 1); if (e.key === 'ArrowRight') goTo(active + 1); }}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={endGesture}
            onPointerCancel={endGesture}
          >
            <div className="screen-track" style={{ transform: `translateX(calc(${-active * 100}% + ${drag ?? 0}px))` }}>
              {SCREENS.map((s, i) => (
                <div className="screen-slide" key={s.id} role="group" aria-roledescription="slide" aria-label={`${i + 1} of ${SCREENS.length}: ${s.label}`} aria-hidden={active !== i}>
                  <button
                    className="screen-image-button"
                    tabIndex={active === i ? 0 : -1}
                    onClick={() => { if (suppressClick.current) return; setZoom(s.id); }}
                    aria-label={`View ${s.label} screenshot at full size`}
                  >
                    <img src={imgSrc(s.id)} alt={`SceneSteward ${s.label} interface populated with fictional sample data`} width="1440" height="1000" draggable={false} loading={i === 0 ? 'eager' : 'lazy'} />
                  </button>
                </div>
              ))}
            </div>
          </div>
          <div className="screen-caption"><span><i /> ACTUAL FRONTEND CAPTURE</span><span>ILLUSTRATIVE DATA · NOT A LIVE PRODUCTION</span></div>
        </div>
        <div className="screen-explanation" key={screen.id}><span className="section-index">{screen.number} / {screen.label}</span><h3>{screen.title}</h3><p>{screen.body}</p></div>
      </Reveal>

      <section className="promise-section"><Reveal className="promise-intro"><span className="section-index">A CLEAR LINE, AT EVERY STEP</span><h2>Your story can evolve.<br /><em>Consent doesn't travel<br />with it automatically.</em></h2><p>A festival release isn't a streaming release. An interview isn't permission for a synthetic voice. SceneSteward keeps those distinctions in the record.</p></Reveal><div className="promise-list">{[
        [Users, 'Start with the person.', 'Record what each participant agreed to, declined or still needs to discuss. Keep the original context close.'],
        [ScanLine, 'Check the proposed use.', 'Compare the next trailer, platform or audience against the consent record. Bring differences to the surface.'],
        [ShieldCheck, 'Leave the decision to a human.', 'Advisory findings support the review. Authorized people make the final call and record their reasons.'],
      ].map(([Icon, title, body]: any, i) => <Reveal className="promise-row" key={title} delay={i * 110}><div className="promise-number">0{i + 1}</div><div><Icon size={22} strokeWidth={1.4} /><h3>{title}</h3><p>{body}</p></div></Reveal>)}</div></section>

      <Reveal as="section" className="boundary-note"><span className="section-index">THE NON-NEGOTIABLES</span><div><p><Check size={16} /> Silence is never agreement.</p><p><Check size={16} /> Consent is specific to each use.</p><p><Check size={16} /> A human makes the final decision.</p></div></Reveal>
      <Reveal as="section" className="landing-cta"><span className="section-index">FROM FIRST INTERVIEW TO FINAL CUT</span><h2>Make room for<br /><em>the people in your film.</em></h2><Link href="/projects" className="landing-button">Open your workspace <ArrowRight size={18} /></Link><p>The frontend is ready to explore. Workspace data and actions require your connected backend.</p></Reveal>
      {zoom && <div className="screenshot-modal" role="dialog" aria-modal="true" aria-label="Product screenshot" onClick={() => setZoom(null)}><button autoFocus onClick={() => setZoom(null)} aria-label="Close screenshot"><X /></button><img src={imgSrc(zoom)} alt="SceneSteward actual frontend with fictional sample data" onClick={e => e.stopPropagation()} onKeyDown={e => {if (e.key === 'Escape') setZoom(null);}} /><p>Actual SceneSteward frontend · Fictional sample data</p></div>}
    </div>
  );
}
