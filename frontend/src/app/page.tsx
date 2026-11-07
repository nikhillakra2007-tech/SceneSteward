'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ShieldCheck,
  Film,
  Users,
  ArrowRight,
  ArrowUpRight,
  Lock,
  Eye,
  UserCheck,
} from 'lucide-react';
import { api, Project, User, getAuthToken } from '@/lib/api';

const PRINCIPLES = [
  {
    index: '01',
    icon: Lock,
    title: 'Silence is never agreement',
    body: 'Unanswered outreach or missing documentation never defaults to permission. If a participant has not explicitly agreed to a context, it is flagged as Unresolved or Declined.',
  },
  {
    index: '02',
    icon: Eye,
    title: 'Consent is per-use, always',
    body: 'Agreement to an in-depth interview never authorizes synthetic voice cloning, sensationalized trailers, or overseas syndication without a separate explicit release.',
  },
  {
    index: '03',
    icon: UserCheck,
    title: 'A human decides, every time',
    body: 'Advisory agents analyze discrepancies, tone, and vulnerability risk — but only authorized directors and care leads make final determinations.',
  },
];

export default function HomePage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const token = getAuthToken();
        if (token) {
          try {
            const user = await api.getMe();
            setCurrentUser(user);
            const projRes = await api.listProjects();
            setProjects(projRes.items || []);
          } catch {
            // token may be invalid
          }
        }
        try {
          const metrics = await api.getMetrics();
          setBackendOnline(true);
        } catch {
          setBackendOnline(false);
        }
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-16 sm:space-y-20">
      {/* ── Hero ─────────────────────────────────────────── */}
      <section className="relative">
        <div className="pointer-events-none absolute inset-x-0 -top-4 flex justify-between font-mono text-[10px] uppercase tracking-[0.3em] text-slate-600">
          <span>Reel 01</span>
          <span className="hidden sm:inline">Participant consent · Use verification · Human review</span>
          <span>Scene / Steward</span>
        </div>
        <div className="border-y border-slate-800 py-12 sm:py-16">
          <div className="max-w-3xl space-y-6">
            <p className="ss-kicker flex items-center gap-2">
              <ShieldCheck className="h-3.5 w-3.5" />
              Ethical safeguards &amp; verification active
            </p>
            <h1 className="font-display text-4xl font-semibold leading-[1.08] tracking-tight text-slate-50 sm:text-6xl">
              Protecting participant dignity,{' '}
              <em className="text-brass-400">frame by frame.</em>
            </h1>
            <p className="max-w-xl text-[15px] leading-relaxed text-slate-400">
              SceneSteward coordinates participant releases, canonical consent records, advisory
              agents, and strict human-in-the-loop approvals — so documentary filmmakers never
              overstep agreed boundaries.
            </p>
            <div className="flex flex-wrap items-center gap-3 pt-1">
              <Link href="/projects" className="ss-btn-primary">
                <span>View Projects</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
              <div className="inline-flex items-center gap-2 rounded-md border border-slate-800 bg-slate-900/60 px-3.5 py-2 font-mono text-[11px] text-slate-400">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    backendOnline === null
                      ? 'bg-slate-500'
                      : backendOnline
                      ? 'bg-emerald-400'
                      : 'bg-amber-400'
                  }`}
                />
                <span>
                  Backend ·{' '}
                  {backendOnline === null
                    ? 'checking'
                    : backendOnline
                    ? 'connected (FastAPI + RLS)'
                    : 'offline / standalone'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Principles ───────────────────────────────────── */}
      <section>
        <div className="mb-8 flex items-end justify-between gap-4">
          <div>
            <p className="ss-kicker mb-2">The rules we hold the line on</p>
            <h2 className="font-display text-2xl font-semibold tracking-tight text-slate-50 sm:text-3xl">
              Three principles, non-negotiable
            </h2>
          </div>
        </div>
        <div className="divide-y divide-slate-800 border-y border-slate-800">
          {PRINCIPLES.map((p) => (
            <div key={p.index} className="group grid grid-cols-[auto_1fr] gap-5 py-6 sm:grid-cols-[64px_auto_1fr] sm:gap-8 sm:py-7">
              <span className="pt-1 font-mono text-xs text-brass-500/80">{p.index}</span>
              <div className="hidden h-9 w-9 items-center justify-center rounded-md border border-slate-800 text-slate-500 transition group-hover:border-brass-500/40 group-hover:text-brass-400 sm:flex">
                <p.icon className="h-4 w-4" />
              </div>
              <div className="space-y-1.5">
                <h3 className="font-display text-lg font-semibold text-slate-100">{p.title}</h3>
                <p className="max-w-2xl text-sm leading-relaxed text-slate-400">{p.body}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Active Workspaces ────────────────────────────── */}
      <section className="space-y-6">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="ss-kicker mb-2">Production</p>
            <h2 className="font-display text-2xl font-semibold tracking-tight text-slate-50 sm:text-3xl">
              Active documentary workspaces
            </h2>
            <p className="mt-1.5 text-sm text-slate-400">
              Participant rosters, agreements, and proposed footage uses.
            </p>
          </div>
          <Link
            href="/projects"
            className="group hidden items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.18em] text-brass-500 transition hover:text-brass-300 sm:inline-flex"
          >
            <span>View all</span>
            <ArrowUpRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </Link>
        </div>

        {currentUser ? (
          projects.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {projects.map((p) => (
                <Link
                  key={p.id}
                  href={`/projects/${p.id}`}
                  className="group ss-card block space-y-4 p-5 transition hover:border-slate-600 hover:bg-slate-900"
                >
                  <div className="flex items-center justify-between">
                    <span className="rounded-sm border border-slate-700 bg-slate-850 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-emerald-400">
                      {p.status}
                    </span>
                    <Film className="h-4 w-4 text-slate-600 transition group-hover:text-brass-400" />
                  </div>
                  <div>
                    <h3 className="font-display text-lg font-semibold text-slate-100 transition group-hover:text-white">
                      {p.title}
                    </h3>
                    <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-400">
                      {p.description || p.purpose || 'No description provided.'}
                    </p>
                  </div>
                  <div className="flex items-center justify-between border-t border-slate-800/80 pt-3 font-mono text-[10px] uppercase tracking-wider text-slate-500">
                    <span>{p.themes?.slice(0, 2).join(' · ') || 'Documentary'}</span>
                    <span>{new Date(p.updated_at).toLocaleDateString()}</span>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="ss-card border-dashed p-10 text-center text-slate-400">
              <Film className="mx-auto mb-3 h-7 w-7 text-slate-600" />
              <p className="text-sm">
                No active projects yet. Use the Projects tab to create your first documentary workspace.
              </p>
            </div>
          )
        ) : (
          <div className="ss-card space-y-3 p-10 text-center">
            <Users className="mx-auto h-7 w-7 text-brass-400" />
            <p className="text-sm font-medium text-slate-200">
              Sign in to view and manage projects in this workspace.
            </p>
            <p className="text-xs text-slate-500">
              Use &ldquo;Olivia (Director)&rdquo; in the navbar to authenticate with the dev session.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
