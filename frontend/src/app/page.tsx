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
  { id: 'workspace', label: 'Project overview', number: '01', title: 'Everything about your film in one place.', body: 'See your participants, their release forms, the ways you plan to use their footage, and what still needs a decision.' },
  { id: 'consent', label: 'Participant consent', number: '02', title: 'See what each person said yes or no to.', body: 'Every use is tracked on its own, like an interview clip, a festival trailer or a voice clone. A "no" stays a "no". No answer yet stays "not decided".' },
  { id: 'analytics', label: 'Progress and gaps', number: '03', title: 'Spot what is missing before the final edit.', body: 'See which people you have not talked to yet, which reviews are waiting, and which care tasks are open.' },
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
        <div className="landing-topline"><span><i /> FOR DOCUMENTARY FILM TEAMS</span><span>CONSENT TRACKING</span></div>
        <div className="hero-copy" ref={heroCopyRef}>
          <p className="landing-eyebrow">Consent tracking for documentary films</p>
          <h1>
            <span className="h1-line"><span className="h1-inner">Know what everyone</span></span>
            <span className="h1-line"><span className="h1-inner h1-inner-2">in your film <em>agreed to.</em></span></span>
            <span className="frame-corner" aria-hidden="true" />
          </h1>
          <div className="hero-bottom"><p className="hero-lede">SceneSteward keeps a simple record of what each participant said yes or no to. Before you use their footage somewhere new, it checks that record and warns you if they did not agree.</p><div className="hero-actions"><Magnetic><Link href="/projects" className="landing-button">Open workspace <ArrowUpRight size={17} /></Link></Magnetic><a href="#how-it-works" className="landing-text-link"><Play size={13} fill="currentColor" /> See how it works</a></div></div>
        </div>
        <ul className="hero-facts">
          <li><b>1</b><span>Write down what each person agreed to</span></li>
          <li><b>2</b><span>Check every new use of their footage</span></li>
          <li><b>3</b><span>You make the final call</span></li>
        </ul>
        <div className="scroll-cue" aria-hidden="true"><span>SCROLL</span><i /></div>
      </section>

      <Marquee items={['SILENCE IS NOT A YES', 'EACH USE NEEDS ITS OWN YES', 'A PERSON MAKES THE FINAL CALL', 'CHECK BEFORE YOU PUBLISH', 'RESPECT THE PEOPLE IN YOUR FILM']} />

      <Reveal as="section" className="how-section"><div id="how-it-works" style={{ scrollMarginTop: 90 }} /><span className="section-index">HOW IT WORKS</span><h2>Three simple steps.</h2><ol className="how-steps">{[
        [Users, 'Record what people agreed to', 'For each participant, note what they said yes to, what they said no to, and what is still undecided. Keep their original words close by.'],
        [ScanLine, 'Check each new use', 'Planning a trailer, a social post or a new audience? SceneSteward compares it with what the person agreed to and points out any mismatch.'],
        [ShieldCheck, 'You decide', 'SceneSteward only suggests. A real person on your team makes the final decision and writes down why.'],
      ].map(([Icon, title, body]: any, i) => <li className="how-step" key={title} style={{ ['--i' as any]: i }}><div className="how-icon"><Icon size={24} strokeWidth={1.5} /></div><span className="how-num">Step {i + 1}</span><h3>{title}</h3><p>{body}</p></li>)}</ol></Reveal>

      <Reveal as="section" className="product-stage" delay={60}>
        <div id="in-action" style={{ scrollMarginTop: 90 }} />
        <div className="stage-heading"><div><span className="section-index">THE APP</span><h2>See what it looks like.<br /><em>Click, swipe or use the arrows.</em></h2></div><p>These are real screens from the app, filled with made-up sample data.</p></div>
        <div className="screen-controls">
          <div className="screen-progress" aria-hidden="true"><span>{screen.number} / 0{SCREENS.length}</span><span className="bar"><i style={{ width: `${((active + 1) / SCREENS.length) * 100}%` }} /></span><span className="screen-progress-label">{screen.label}</span></div>
          <div className="screen-hint" aria-hidden="true"><MoveHorizontal size={13} /><span>DRAG OR SWIPE</span></div>
          <div className="screen-arrows">
            <button type="button" onClick={() => goTo(active - 1)} disabled={active === 0} aria-label="Previous screenshot"><ArrowLeft size={15} /></button>
            <button type="button" onClick={() => goTo(active + 1)} disabled={active === SCREENS.length - 1} aria-label="Next screenshot"><ArrowRight size={15} /></button>
          </div>
        </div>
        <CursorStage overlays={<>
          <div className="stage-chip chip-review" aria-hidden="true"><span><i />WAITING FOR REVIEW</span></div>
          <div className="stage-chip chip-consent" aria-hidden="true"><span><i />OK TO USE IN TRAILER</span></div>
          <div className="stage-chip chip-window" aria-hidden="true"><span><i />FESTIVALS ONLY</span></div>
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
          <div className="screen-caption"><span><i /> REAL SCREENSHOT</span><span>SAMPLE DATA ONLY</span></div>
        </div>
        </div>
        </CursorStage>
        <div className="screen-explanation" key={screen.id}><span className="section-index">{screen.number} / {screen.label}</span><h3>{screen.title}</h3><p>{screen.body}</p></div>
      </Reveal>

      <section className="statement-section">
        <Reveal><span className="section-index">A QUICK EXAMPLE</span></Reveal>
        <TextReveal text="Maria agreed to be in your film for festivals. If someone wants her clip in an online ad, that is a new question. SceneSteward shows you the difference." />
      </section>

      

      <Reveal as="section" className="boundary-note"><span className="section-index">OUR THREE RULES</span><div><p><Check size={16} /> No answer is not a yes.</p><p><Check size={16} /> Each use needs its own yes.</p><p><Check size={16} /> A person makes the final decision.</p></div></Reveal>
      <Reveal as="section" className="landing-cta"><span className="section-index">READY TO TRY IT?</span><h2>Keep every promise<br /><em>you made on camera.</em></h2><Magnetic strength={7}><Link href="/projects" className="landing-button">Open your workspace <ArrowRight size={18} /></Link></Magnetic><p>Open the workspace to explore. Saving real project data needs the backend connected.</p></Reveal>
      <Reveal as="section" className="landing-finale">
        <div className="finale-wordmark" aria-hidden="true"><svg viewBox="0 0 1160 175" preserveAspectRatio="xMidYMid meet"><text x="580" y="132" textAnchor="middle" textLength="1125" lengthAdjust="spacingAndGlyphs">SCENESTEWARD</text></svg></div>
        <div className="finale-meta"><span>SCENE / STEWARD</span><span>CONSENT, WRITTEN DOWN</span><span>2026</span></div>
      </Reveal>
      {zoom && <div className="screenshot-modal" role="dialog" aria-modal="true" aria-label="Product screenshot" onClick={() => setZoom(null)}><button autoFocus onClick={() => setZoom(null)} aria-label="Close screenshot"><X /></button><Image src={imgSrc(zoom)} alt="SceneSteward actual frontend with fictional sample data" width={1440} height={1000} onClick={e => e.stopPropagation()} onKeyDown={e => {if (e.key === 'Escape') setZoom(null);}} unoptimized /><p>Actual SceneSteward frontend · Fictional sample data</p></div>}
    </div>
  );
}
