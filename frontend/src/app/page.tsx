'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { 
  ShieldCheck, 
  Film, 
  Users, 
  AlertTriangle, 
  CheckCircle2, 
  ArrowRight,
  Lock,
  Sparkles,
  Server
} from 'lucide-react';
import { api, Project, User, getAuthToken } from '@/lib/api';

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
        // Test backend connectivity
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
    <div className="space-y-10">
      {/* Hero Section */}
      <div className="relative rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950 p-8 sm:p-10 shadow-2xl overflow-hidden">
        <div className="absolute right-0 top-0 -mr-16 -mt-16 w-80 h-80 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />
        
        <div className="max-w-3xl space-y-4">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-800 text-emerald-400 text-xs font-semibold">
            <ShieldCheck className="h-4 w-4" />
            <span>Ethical Safeguards &amp; Verification Active</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Protecting participant dignity throughout documentary storytelling.
          </h1>

          <p className="text-slate-300 text-base leading-relaxed">
            SceneSteward coordinates participant releases, canonical consent records, advisory AI agents, 
            and strict human-in-the-loop approvals so documentary filmmakers never overstep agreed boundaries.
          </p>

          <div className="pt-2 flex flex-wrap gap-3">
            <Link
              href="/projects"
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition shadow-lg shadow-emerald-950/50"
            >
              <span>Explore Projects</span>
              <ArrowRight className="h-4 w-4" />
            </Link>

            <div className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300">
              <Server className="h-3.5 w-3.5 text-emerald-400" />
              <span>Backend Status:</span>
              <span className={`font-semibold ${backendOnline ? 'text-emerald-400' : 'text-amber-400'}`}>
                {backendOnline === null ? 'Checking...' : backendOnline ? 'Connected (FastAPI + RLS)' : 'Offline / Standalone'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Core Principles */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-xl border border-slate-800/80 bg-slate-900/40 space-y-3">
          <div className="h-10 w-10 rounded-lg bg-rose-950/60 border border-rose-800 flex items-center justify-center text-rose-400">
            <Lock className="h-5 w-5" />
          </div>
          <h3 className="font-bold text-slate-100 text-lg">Silence is Never Agreement</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            Unanswered outreach or missing documentation never defaults to permission. If a participant hasn&apos;t explicitly agreed to a context, it is flagged as Unresolved or Declined.
          </p>
        </div>

        <div className="p-6 rounded-xl border border-slate-800/80 bg-slate-900/40 space-y-3">
          <div className="h-10 w-10 rounded-lg bg-amber-950/60 border border-amber-800 flex items-center justify-center text-amber-400">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <h3 className="font-bold text-slate-100 text-lg">Per-Use Consent Boundary</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            Agreement to an in-depth documentary interview never authorizes synthetic voice cloning, sensationalized trailers, or overseas promotional syndication without separate explicit release.
          </p>
        </div>

        <div className="p-6 rounded-xl border border-slate-800/80 bg-slate-900/40 space-y-3">
          <div className="h-10 w-10 rounded-lg bg-emerald-950/60 border border-emerald-800 flex items-center justify-center text-emerald-400">
            <CheckCircle2 className="h-5 w-5" />
          </div>
          <h3 className="font-bold text-slate-100 text-lg">Human Review Required</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            Advisory AI agents analyze discrepancies, emotional tone, and vulnerability risks, but only authorized human directors and care leads can make final determinations.
          </p>
        </div>
      </div>

      {/* Active Projects Preview */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-100">Active Documentary Workspaces</h2>
            <p className="text-xs text-slate-400">Manage participant rosters, agreements, and proposed footage uses.</p>
          </div>
          <Link
            href="/projects"
            className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 inline-flex items-center space-x-1"
          >
            <span>View All</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {currentUser ? (
          projects.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {projects.map((p) => (
                <Link
                  key={p.id}
                  href={`/projects/${p.id}`}
                  className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-900 hover:border-slate-700 transition space-y-3 block group"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-emerald-400 border border-slate-700 font-mono">
                      {p.status}
                    </span>
                    <Film className="h-4 w-4 text-slate-500 group-hover:text-emerald-400 transition" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-200 group-hover:text-white transition">{p.title}</h3>
                    <p className="text-xs text-slate-400 line-clamp-2 mt-1">
                      {p.description || p.purpose || 'No description provided.'}
                    </p>
                  </div>
                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
                    <span>{p.themes?.slice(0, 2).join(', ') || 'Documentary'}</span>
                    <span>Updated {new Date(p.updated_at).toLocaleDateString()}</span>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center rounded-xl border border-dashed border-slate-800 bg-slate-900/20 text-slate-400">
              <Film className="h-8 w-8 mx-auto mb-2 text-slate-600" />
              <p className="text-sm">No active projects yet. Use the Projects tab to create your first documentary workspace.</p>
            </div>
          )
        ) : (
          <div className="p-8 text-center rounded-xl border border-slate-800 bg-slate-900/30 text-slate-300 space-y-3">
            <Users className="h-8 w-8 mx-auto text-emerald-400" />
            <p className="text-sm font-medium">Log in to view and manage projects in this workspace.</p>
            <p className="text-xs text-slate-400">Click &ldquo;Olivia (Director)&rdquo; in the top-right navbar to authenticate with the dev session.</p>
          </div>
        )}
      </div>
    </div>
  );
}
