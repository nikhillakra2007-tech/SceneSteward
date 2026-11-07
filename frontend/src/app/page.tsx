'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowRight, ArrowUpRight, Play, X, ShieldCheck, ScanLine, Users, Check, Maximize2 } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { useTheme } from '@/lib/theme';

const SCREENS = [
  { id: 'workspace', label: 'Production workspace', number: '01', title: 'The whole production. One shared record.', body: 'Keep participants, releases, proposed uses and human reviews together. See what needs attention before a story leaves the edit.' },
  { id: 'consent', label: 'Participant consent', number: '02', title: 'A yes has boundaries. Keep them visible.', body: 'Track each use separately, from an interview recording to a festival trailer. A declined voice clone stays declined. An unanswered request stays unresolved.' },
  { id: 'analytics', label: 'Operational intelligence', number: '03', title: 'See the gaps before picture lock.', body: 'Discussion coverage, outstanding reviews and care tasks give your team a practical view of what still needs a conversation.' },
];

export default function HomePage() {
  const [active, setActive] = useState(0);
  const [zoom, setZoom] = useState<string | null>(null);
  const theme = useTheme();
  const screen = SCREENS[active];
  const imgSrc = (id: string) => `/screens/${id}-${theme}.webp`;
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
        <div className="stage-heading"><div><span className="section-index">INSIDE SCENESTEWARD</span><h2>Less chasing paperwork.<br /><em>More caring for people.</em></h2></div><p>Explore the actual interface.<br />Screens below use fictional sample data.</p></div>
        <div className="screen-tabs" role="tablist" aria-label="Product screenshots">{SCREENS.map((s, i) => <button key={s.id} id={`tab-${s.id}`} role="tab" aria-selected={active === i} aria-controls="product-panel" onClick={() => setActive(i)}><span>{s.number}</span>{s.label}<ArrowUpRight size={14} /></button>)}</div>
        <div id="product-panel" role="tabpanel" aria-labelledby={`tab-${screen.id}`} className="screen-frame"><div className="screen-toolbar"><span className="window-dots"><i /><i /><i /></span><span>scenesteward / {screen.id}</span><button onClick={() => setZoom(screen.id)} aria-label={`Enlarge ${screen.label} screenshot`}><Maximize2 size={14} /><span>Expand</span></button></div><button className="screen-image-button" onClick={() => setZoom(screen.id)} aria-label={`View ${screen.label} screenshot at full size`}><img key={`${screen.id}-${theme}`} src={imgSrc(screen.id)} alt={`SceneSteward ${screen.label} interface populated with fictional sample data`} width="1440" height="1000" /></button><div className="screen-caption"><span><i /> ACTUAL FRONTEND CAPTURE</span><span>ILLUSTRATIVE DATA · NOT A LIVE PRODUCTION</span></div></div>
        <div className="screen-explanation"><span className="section-index">{screen.number} / {screen.label}</span><h3>{screen.title}</h3><p>{screen.body}</p></div>
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
