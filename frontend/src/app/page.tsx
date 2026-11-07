'use client';

import { useEffect, useRef } from 'react';
import { ArrowRight, ArrowUpRight, Play, ShieldCheck, ScanLine, Users, Check } from 'lucide-react';
import Link from 'next/link';
import { Reveal } from '@/components/Reveal';
import Marquee from '@/components/Marquee';
import TextReveal from '@/components/TextReveal';
import Magnetic from '@/components/Magnetic';

export default function HomePage() {
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
          <div className="hero-bottom"><p className="hero-lede">SceneSteward keeps a simple record of what each participant said yes or no to. Before you use their footage somewhere new, it checks that record and warns you if they did not agree.</p><div className="hero-actions"><Magnetic><Link href="/projects" className="landing-button">Sign in to open your workspace <ArrowUpRight size={17} /></Link></Magnetic><a href="#how-it-works" className="landing-text-link"><Play size={13} fill="currentColor" /> See how it works</a></div></div>
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

      <section className="statement-section">
        <Reveal><span className="section-index">A QUICK EXAMPLE</span></Reveal>
        <TextReveal text="Maria agreed to be in your film for festivals. If someone wants her clip in an online ad, that is a new question. SceneSteward shows you the difference." />
      </section>

      

      <Reveal as="section" className="boundary-note"><span className="section-index">OUR THREE RULES</span><div><p><Check size={16} /> No answer is not a yes.</p><p><Check size={16} /> Each use needs its own yes.</p><p><Check size={16} /> A person makes the final decision.</p></div></Reveal>
      <Reveal as="section" className="landing-cta"><span className="section-index">READY TO TRY IT?</span><h2>Keep every promise<br /><em>you made on camera.</em></h2><Magnetic strength={7}><Link href="/projects" className="landing-button">Sign in to get started <ArrowRight size={18} /></Link></Magnetic><p>Sign in, choose your role, and start recording what people agreed to. Everything runs in your browser; nothing leaves your device.</p></Reveal>
      <Reveal as="section" className="landing-finale">
        <div className="finale-wordmark" aria-hidden="true"><svg viewBox="0 0 1160 175" preserveAspectRatio="xMidYMid meet"><text x="580" y="132" textAnchor="middle" textLength="1125" lengthAdjust="spacingAndGlyphs">SCENESTEWARD</text></svg></div>
        <div className="finale-meta"><span>SCENE / STEWARD</span><span>CONSENT, WRITTEN DOWN</span><span>2026</span></div>
      </Reveal>
    </div>
  );
}
