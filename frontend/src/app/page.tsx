'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight, ArrowLeft, ArrowUpRight, Play, X, ShieldCheck, ScanLine, Users, Check, Maximize2, MoveHorizontal } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import CursorStage from '@/components/CursorStage';
import Marquee from '@/components/Marquee';
import TextReveal from '@/components/TextReveal';
import Magnetic from '@/components/Magnetic';
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
  const heroCopyRef = useRef<HTMLDivElement>(null);

  // Gentle hero parallax: the copy drifts up and fades as you scroll away.
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const el = heroCopyRef.current;
    if (!el) return;
    let raf = 0;
    let ticking = false;
    const update = () => {
      ticking = false;
      const y = window.scrollY;
      const p = Math.min(1, y / 480);
      el.style.transform = `translate3d(0, ${(y * 0.1).toFixed(1)}px, 0)`;
      el.style.opacity = (1 - p).toFixed(3);
    };
    const onScroll = () => {
      if (!ticking) {
        ticking = true;
        raf = requestAnimationFrame(update);
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

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
    } else {
      // pointer capture retargets the click to the viewport, so a tap zooms from here
      setZoom(SCREENS[active].id);
    }
    setDrag(null);
  };
  const cancelGesture = () => { gesture.current = null; setDrag(null); };

  return (
    <div className="product-landing">
      <section className="landing-hero">
        <div className="landing-topline"><span><i /> BUILT FOR DOCUMENTARY TEAMS</span><span>THE PEOPLE BEHIND THE PICTURE</span></div>
        <div className="hero-copy" ref={heroCopyRef}>
          <p className="landing-eyebrow">Good stories start with trust.</p>
          <h1>
            <span className="h1-line"><span className="h1-inner">Every frame has</span></span>
            <span className="h1-line"><span className="h1-inner h1-inner-2">a <em>human story.</em></span></span>
            <span className="frame-corner" aria-hidden="true" />
          </h1>
          <div className="hero-bottom"><p>Make the film. Keep the promise.<br />Consent, participant care and human review,<br className="desktop-break" /> held together from first interview to final cut.</p><div className="hero-actions"><Magnetic><Link href="/projects" className="landing-button">Open workspace <ArrowUpRight size={17} /></Link></Magnetic><a href="#in-action" className="landing-text-link"><Play size={13} fill="currentColor" /> See it in action</a></div></div>
        </div>
        <div className="hero-rule"><span>SCENE / STEWARD</span><span>CONSENT IS A CONVERSATION, NOT A CHECKBOX.</span><span>EST. 2026</span></div>
        <div className="scroll-cue" aria-hidden="true"><span>SCROLL</span><i /></div>
      </section>

      <Marquee items={['SILENCE IS NEVER AGREEMENT', 'CONSENT IS SPECIFIC TO EACH USE', 'A HUMAN MAKES THE FINAL CALL', 'EVERY USE IS ITS OWN QUESTION', 'TRUST IS THE FIRST CREDIT']} />

      <Reveal as="section" className="product-stage" delay={60}>
        <div id="in-action" style={{ scrollMarginTop: 90 }} />
        <div className="stage-heading"><div><span className="section-index">INSIDE SCENESTEWARD</span><h2>Less chasing paperwork.<br /><em>More caring for people.</em></h2></div><p>Explore the actual interface.<br />Move across it - hover, swipe or drag.<br />Screens use fictional sample data.</p></div>
        <div className="screen-controls">
          <div className="screen-progress" aria-hidden="true"><span>{screen.number} / 0{SCREENS.length}</span><span className="bar"><i style={{ width: `${((active + 1) / SCREENS.length) * 100}%` }} /></span><span className="screen-progress-label">{screen.label}</span></div>
          <div className="screen-hint" aria-hidden="true"><MoveHorizontal size={13} /><span>HOVER · DRAG · SWIPE</span></div>
          <div className="screen-arrows">
            <button type="button" onClick={() => goTo(active - 1)} disabled={active === 0} aria-label="Previous screenshot"><ArrowLeft size={15} /></button>
            <button type="button" onClick={() => goTo(active + 1)} disabled={active === SCREENS.length - 1} aria-label="Next screenshot"><ArrowRight size={15} /></button>
          </div>
        </div>
        <CursorStage overlays={<>
          <div className="stage-chip chip-review" aria-hidden="true"><span><i />HUMAN REVIEW · PENDING</span></div>
          <div className="stage-chip chip-consent" aria-hidden="true"><span><i />CONSENT CLEARED · TRAILER V2</span></div>
          <div className="stage-chip chip-window" aria-hidden="true"><span><i />RELEASE WINDOW · FESTIVAL ONLY</span></div>
        </>}>
        <div className="frame-ring">
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
            onPointerCancel={cancelGesture}
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
                    <Image src={imgSrc(s.id)} alt={`SceneSteward ${s.label} interface populated with fictional sample data`} width={1440} height={1000} draggable={false} priority={i === 0} unoptimized />
                  </button>
                </div>
              ))}
            </div>
          </div>
          <div className="screen-caption"><span><i /> ACTUAL FRONTEND CAPTURE</span><span>ILLUSTRATIVE DATA · NOT A LIVE PRODUCTION</span></div>
        </div>
        </div>
        </CursorStage>
        <div className="screen-explanation" key={screen.id}><span className="section-index">{screen.number} / {screen.label}</span><h3>{screen.title}</h3><p>{screen.body}</p></div>
      </Reveal>

      <section className="statement-section">
        <Reveal><span className="section-index">WHY IT EXISTS</span></Reveal>
        <TextReveal text="A festival release is not a streaming release. An interview is not permission for a synthetic voice. The record keeps the difference." />
      </section>

      <section className="promise-section"><Reveal className="promise-intro"><span className="section-index">A CLEAR LINE, AT EVERY STEP</span><h2>Your story can evolve.<br /><em>Consent doesn&rsquo;t travel<br />with it automatically.</em></h2></Reveal><div className="promise-list">{[
        [Users, 'Start with the person.', 'Record what each participant agreed to, declined or still needs to discuss. Keep the original context close.'],
        [ScanLine, 'Check the proposed use.', 'Compare the next trailer, platform or audience against the consent record. Bring differences to the surface.'],
        [ShieldCheck, 'Leave the decision to a human.', 'Advisory findings support the review. Authorized people make the final call and record their reasons.'],
      ].map(([Icon, title, body]: any, i) => <Reveal className="promise-row" key={title} delay={i * 110}><div className="promise-number">0{i + 1}</div><div><Icon size={22} strokeWidth={1.4} /><h3>{title}</h3><p>{body}</p></div></Reveal>)}</div></section>

      <Reveal as="section" className="boundary-note"><span className="section-index">THE NON-NEGOTIABLES</span><div><p><Check size={16} /> Silence is never agreement.</p><p><Check size={16} /> Consent is specific to each use.</p><p><Check size={16} /> A human makes the final decision.</p></div></Reveal>
      <Reveal as="section" className="landing-cta"><span className="section-index">FROM FIRST INTERVIEW TO FINAL CUT</span><h2>Make room for<br /><em>the people in your film.</em></h2><Magnetic strength={7}><Link href="/projects" className="landing-button">Open your workspace <ArrowRight size={18} /></Link></Magnetic><p>The frontend is ready to explore. Workspace data and actions require your connected backend.</p></Reveal>
      <Reveal as="section" className="landing-finale">
        <div className="finale-wordmark" aria-hidden="true"><svg viewBox="0 0 1160 175" preserveAspectRatio="xMidYMid meet"><text x="580" y="132" textAnchor="middle" textLength="1125" lengthAdjust="spacingAndGlyphs">SCENESTEWARD</text></svg></div>
        <div className="finale-meta"><span>SCENE / STEWARD</span><span>CONSENT, KEPT IN THE RECORD</span><span>EST. 2026</span></div>
      </Reveal>
      {zoom && <div className="screenshot-modal" role="dialog" aria-modal="true" aria-label="Product screenshot" onClick={() => setZoom(null)}><button autoFocus onClick={() => setZoom(null)} aria-label="Close screenshot"><X /></button><Image src={imgSrc(zoom)} alt="SceneSteward actual frontend with fictional sample data" width={1440} height={1000} onClick={e => e.stopPropagation()} onKeyDown={e => {if (e.key === 'Escape') setZoom(null);}} unoptimized /><p>Actual SceneSteward frontend · Fictional sample data</p></div>}
    </div>
  );
}
