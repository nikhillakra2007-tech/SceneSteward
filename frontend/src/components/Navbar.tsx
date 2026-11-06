'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ShieldCheck, Film, BarChart3, LogOut, UserCircle, LogIn, ArrowRightLeft, X } from 'lucide-react';
import { api, getAuthToken, User } from '@/lib/api';

const ROLE_PRESETS = [
  { label: 'Olivia (Director / Owner)', email: 'olivia@example.com', name: 'Olivia Director' },
  { label: 'Claire (Care Lead)', email: 'claire@example.com', name: 'Claire Care' },
  { label: 'Marcus (Producer)', email: 'marcus@example.com', name: 'Marcus Producer' },
  { label: 'Elena (Legal Counsel)', email: 'elena@example.com', name: 'Elena Legal' },
];

export function Navbar() {
  const pathname = usePathname();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [customEmail, setCustomEmail] = useState('');
  const [customName, setCustomName] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);

  const fetchUser = async () => {
    if (!getAuthToken()) {
      setCurrentUser(null);
      return;
    }
    try {
      const user = await api.getMe();
      setCurrentUser(user);
    } catch {
      setCurrentUser(null);
    }
  };

  useEffect(() => {
    fetchUser();
  }, [pathname]);

  const handleDevLogin = async (email: string, name: string) => {
    setLoading(true);
    setAuthError(null);
    try {
      await api.loginDev(email, name);
      await fetchUser();
      setModalOpen(false);
      setCustomEmail('');
      setCustomName('');
    } catch (err: any) {
      setAuthError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    api.logout();
    setCurrentUser(null);
    window.location.href = '/';
  };

  return (
    <>
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-6">
              <Link href="/" className="flex items-center space-x-2.5">
                <div className="h-9 w-9 rounded-lg bg-emerald-600/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <div>
                  <span className="text-base font-bold text-slate-100 tracking-tight">SceneSteward</span>
                  <span className="hidden sm:inline-block ml-2 text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                    Documentary Ethics & Consent
                  </span>
                </div>
              </Link>

              <nav className="hidden md:flex space-x-1">
                <Link
                  href="/projects"
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition ${
                    pathname?.startsWith('/projects')
                      ? 'bg-slate-800 text-emerald-400'
                      : 'text-slate-300 hover:text-slate-100 hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center space-x-1.5">
                    <Film className="h-4 w-4" />
                    <span>Projects</span>
                  </div>
                </Link>
                <Link
                  href="/analytics"
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition ${
                    pathname?.startsWith('/analytics')
                      ? 'bg-slate-800 text-emerald-400'
                      : 'text-slate-300 hover:text-slate-100 hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center space-x-1.5">
                    <BarChart3 className="h-4 w-4" />
                    <span>Analytics</span>
                  </div>
                </Link>
              </nav>
            </div>

            <div className="flex items-center space-x-3">
              {currentUser ? (
                <div className="flex items-center space-x-3">
                  <div className="text-right hidden sm:block">
                    <div className="text-xs font-semibold text-slate-200">{currentUser.full_name}</div>
                    <div className="text-[11px] text-emerald-400">{currentUser.email}</div>
                  </div>
                  <button
                    onClick={() => setModalOpen(true)}
                    title="Switch User / Role"
                    data-testid="switch-user-btn"
                    className="p-1.5 rounded-lg border border-slate-700 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 transition flex items-center gap-1.5 text-xs px-2.5"
                  >
                    <ArrowRightLeft className="h-3.5 w-3.5" />
                    <span className="hidden md:inline">Switch</span>
                  </button>
                  <button
                    onClick={handleLogout}
                    title="Logout"
                    data-testid="logout-btn"
                    className="p-1.5 rounded-lg border border-slate-700 text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition"
                  >
                    <LogOut className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-slate-400 hidden lg:inline">Quick Dev:</span>
                  <button
                    disabled={loading}
                    data-testid="quick-login-olivia"
                    onClick={() => handleDevLogin('olivia@example.com', 'Olivia Director')}
                    className="text-xs px-2.5 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition disabled:opacity-50"
                  >
                    Olivia (Director)
                  </button>
                  <button
                    disabled={loading}
                    data-testid="quick-login-claire"
                    onClick={() => handleDevLogin('claire@example.com', 'Claire Care')}
                    className="text-xs px-2.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium transition disabled:opacity-50"
                  >
                    Claire (Care)
                  </button>
                  <button
                    onClick={() => setModalOpen(true)}
                    data-testid="custom-login-btn"
                    className="text-xs px-2.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-emerald-500/40 font-medium transition flex items-center gap-1.5"
                  >
                    <LogIn className="h-3.5 w-3.5" />
                    <span>Custom / Switch</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Identity Switching & Registration Modal */}
      {modalOpen && (
        <div
          data-testid="auth-modal"
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
        >
          <div className="relative w-full max-w-md rounded-xl bg-slate-900 border border-slate-700 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <UserCircle className="h-5 w-5 text-emerald-400" />
                <h3 className="text-base font-semibold text-slate-100">
                  {currentUser ? 'Switch User / Persona' : 'Sign In or Register'}
                </h3>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {authError && (
              <div className="mt-4 p-3 rounded bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
                {authError}
              </div>
            )}

            {/* Quick Role Presets */}
            <div className="mt-4">
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Preset Personas</p>
              <div className="grid grid-cols-2 gap-2">
                {ROLE_PRESETS.map((preset) => (
                  <button
                    key={preset.email}
                    type="button"
                    disabled={loading}
                    onClick={() => handleDevLogin(preset.email, preset.name)}
                    className="p-2 text-left rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 hover:border-emerald-500/50 transition group"
                  >
                    <div className="text-xs font-semibold text-slate-200 group-hover:text-emerald-300">
                      {preset.name}
                    </div>
                    <div className="text-[10px] text-slate-400 truncate">{preset.email}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-800" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-slate-900 px-2 text-slate-500">Or custom identity</span>
              </div>
            </div>

            {/* Custom Input Form */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (customEmail.trim() && customName.trim()) {
                  handleDevLogin(customEmail.trim(), customName.trim());
                }
              }}
              className="space-y-3"
            >
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  data-testid="login-name-input"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  placeholder="e.g. Maya Lin"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  data-testid="login-email-input"
                  value={customEmail}
                  onChange={(e) => setCustomEmail(e.target.value)}
                  placeholder="e.g. maya@production.co"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-3 py-1.5 text-xs rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !customEmail.trim() || !customName.trim()}
                  data-testid="login-submit-btn"
                  className="px-4 py-1.5 text-xs rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition disabled:opacity-50"
                >
                  {loading ? 'Authenticating...' : 'Sign In / Register'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
