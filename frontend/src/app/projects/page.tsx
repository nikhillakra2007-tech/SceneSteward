'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Film, Plus, Sparkles, AlertCircle, Calendar, ArrowRight } from 'lucide-react';
import { api, Project, getAuthToken } from '@/lib/api';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New project modal state
  const [showModal, setShowModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [purpose, setPurpose] = useState('');
  const [themesStr, setThemesStr] = useState('environment, social justice');
  const [distributionPlan, setDistributionPlan] = useState('Festival premiere followed by educational screening');

  const loadProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      if (!getAuthToken()) {
        setError('Please sign in via the top navbar to view projects.');
        setProjects([]);
        return;
      }
      const res = await api.listProjects();
      setProjects(res.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setCreating(true);
    try {
      const themes = themesStr.split(',').map((s) => s.trim()).filter(Boolean);
      await api.createProject({
        title: title.trim(),
        description: description.trim() || undefined,
        purpose: purpose.trim() || undefined,
        themes,
        distribution_plan: distributionPlan.trim() || undefined,
      });
      setShowModal(false);
      setTitle('');
      setDescription('');
      setPurpose('');
      await loadProjects();
    } catch (err: any) {
      alert(`Creation failed: ${err.message}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center space-x-2.5">
            <Film className="h-6 w-6 text-emerald-400" />
            <span>Documentary Projects</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Production workspaces scoped with PostgreSQL Row-Level Security (RLS) and cryptographic trust tokens.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition"
        >
          <Plus className="h-4 w-4" />
          <span>New Project</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl border border-amber-800/80 bg-amber-950/30 text-amber-300 text-sm flex items-center space-x-3">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="text-center py-16 text-slate-500 text-sm">
          Loading projects from secure backend...
        </div>
      ) : projects.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/20 space-y-3">
          <Film className="h-10 w-10 mx-auto text-slate-600" />
          <h3 className="font-semibold text-slate-300">No projects found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Get started by creating a new documentary project workspace to track participant releases.
          </p>
          <button
            onClick={() => setShowModal(true)}
            className="mt-2 inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Create First Project</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((proj) => (
            <Link
              key={proj.id}
              href={`/projects/${proj.id}`}
              className="p-6 rounded-2xl border border-slate-800 bg-slate-900/50 hover:bg-slate-900 hover:border-slate-700 transition flex flex-col justify-between group space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-emerald-400 border border-slate-700 font-mono">
                    {proj.status}
                  </span>
                  <ArrowRight className="h-4 w-4 text-slate-600 group-hover:text-emerald-400 group-hover:translate-x-1 transition" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white group-hover:text-emerald-300 transition">
                    {proj.title}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                    {proj.description || proj.purpose || 'No description provided.'}
                  </p>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800/80 space-y-2 text-xs text-slate-500">
                {proj.themes && proj.themes.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {proj.themes.map((t, idx) => (
                      <span key={idx} className="px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 text-[11px]">
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex items-center justify-between pt-1">
                  <span>Updated {new Date(proj.updated_at).toLocaleDateString()}</span>
                  <span className="text-emerald-500 font-medium">Open Workspace &rarr;</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* New Project Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                <Film className="h-5 w-5 text-emerald-400" />
                <span>Create Documentary Project</span>
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Project Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Voices of the Salmon River"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Description
                </label>
                <textarea
                  rows={2}
                  placeholder="Summary of the documentary subject and focus..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Themes (comma separated)
                </label>
                <input
                  type="text"
                  value={themesStr}
                  onChange={(e) => setThemesStr(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Distribution Plan
                </label>
                <input
                  type="text"
                  value={distributionPlan}
                  onChange={(e) => setDistributionPlan(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="pt-2 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !title.trim()}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition disabled:opacity-50"
                >
                  {creating ? 'Creating...' : 'Create Workspace'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
