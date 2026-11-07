'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Clapperboard, Film, BarChart3, LogOut, UserCircle, LogIn, ArrowRightLeft, X, Menu, Sun, Moon } from 'lucide-react';
import { api, getAuthToken, User } from '@/lib/api';
import { useToast } from '@/components/Toast';
import { toggleTheme, useTheme } from '@/lib/theme';

const ROLE_OPTIONS = [
  { value: 'project_owner', label: 'Project owner' },
  { value: 'director', label: 'Director' },
  { value: 'producer', label: 'Producer' },
  { value: 'care_lead', label: 'Care lead' },
  { value: 'legal_counsel', label: 'Legal counsel' },
];

function NavLink({
  href,
  active,
  icon: Icon,
  children,
  onClick,
}: {
  href: string;
  active: boolean;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className={`group relative flex items-center gap-2 px-3 py-2 text-[13px] font-medium tracking-wide transition ${
        active ? 'text-brass-400' : 'text-slate-400 hover:text-slate-100'
      }`}
    >
      <Icon className={`h-4 w-4 transition ${active ? 'text-brass-400' : 'text-slate-500 group-hover:text-slate-300'}`} />
      <span>{children}</span>
      <span
        className={`absolute inset-x-3 -bottom-[13px] h-px bg-brass-500 transition-opacity ${
          active ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'
        }`}
      />
    </Link>
  );
}

export function Navbar() {
  const pathname = usePathname();
  const theme = useTheme();
  const { success, error: toastError, info } = useToast();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [customEmail, setCustomEmail] = useState('');
  const [customName, setCustomName] = useState('');
  const [customRole, setCustomRole] = useState('director');
  const [authError, setAuthError] = useState<string | null>(null);

  const fetchUser = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    fetchUser();
    setMobileMenuOpen(false);
  }, [pathname, fetchUser]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (modalOpen) setModalOpen(false);
        if (mobileMenuOpen) setMobileMenuOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [modalOpen, mobileMenuOpen]);

  const handleDevLogin = async (email: string, name: string, role: string) => {
    setLoading(true);
    setAuthError(null);
    try {
      await api.loginDev(email, name, role);
      setModalOpen(false);
      setCustomEmail('');
      setCustomName('');
      success(`Signed in as ${name}`);
      window.location.href = '/projects';
    } catch (err: any) {
      setAuthError(err.message || 'Login failed');
      toastError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    api.logout();
    setCurrentUser(null);
    info('Signed out successfully');
    window.location.href = '/';
  };

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-slate-800/90 bg-slate-950/85 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4 md:gap-8 min-w-0">
              <Link href="/" className="group flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-md border border-brass-500/50 bg-gradient-to-b from-brass-500/15 to-transparent text-brass-400 transition group-hover:border-brass-400">
                  <Clapperboard className="h-[18px] w-[18px]" />
                </div>
                <div className="flex flex-col justify-center min-w-0">
                  <span className="font-display text-[15px] sm:text-[17px] font-semibold leading-none tracking-tight text-slate-50 truncate">
                    SceneSteward
                  </span>
                  <span className="mt-1 hidden font-mono text-[9px] uppercase leading-none tracking-[0.24em] text-slate-500 sm:block">
                    Documentary Ethics &amp; Consent
                  </span>
                </div>
              </Link>

              {currentUser && (
              <nav className="hidden md:flex items-center gap-1" aria-label="Main Navigation">
                <NavLink href="/projects" active={!!pathname?.startsWith('/projects')} icon={Film}>
                  Projects
                </NavLink>
                <NavLink href="/analytics" active={!!pathname?.startsWith('/analytics')} icon={BarChart3}>
                  Analytics
                </NavLink>
              </nav>
              )}
            </div>

            <div className="flex items-center gap-2 sm:gap-2.5 shrink-0">
              <button
                type="button"
                onClick={toggleTheme}
                title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                data-testid="theme-toggle"
                className="rounded-md border border-slate-700 p-1.5 text-slate-400 transition hover:border-brass-500/50 hover:text-brass-400"
              >
                {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </button>
              {currentUser ? (
                <div className="flex items-center gap-2.5">
                  <div className="text-right hidden sm:block leading-tight">
                    <div className="text-xs font-semibold text-slate-200">{currentUser.full_name}</div>
                    <div className="font-mono text-[10px] text-emerald-400">{currentUser.email}</div>
                  </div>
                  <button
                    onClick={() => setModalOpen(true)}
                    title="Switch User / Role"
                    data-testid="switch-user-btn"
                    className="flex items-center gap-1.5 rounded-md border border-slate-700 px-2.5 py-1.5 text-xs text-slate-400 transition hover:border-brass-500/50 hover:text-brass-400"
                  >
                    <ArrowRightLeft className="h-3.5 w-3.5" />
                    <span className="hidden md:inline">Switch</span>
                  </button>
                  <button
                    onClick={handleLogout}
                    title="Logout"
                    data-testid="logout-btn"
                    className="rounded-md border border-slate-700 p-1.5 text-slate-400 transition hover:border-rose-500/50 hover:text-rose-400"
                  >
                    <LogOut className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setModalOpen(true)}
                  title="Sign in"
                  aria-label="Sign in"
                  data-testid="custom-login-btn"
                  className="flex items-center gap-1.5 rounded-md border border-brass-500/40 px-3 py-1.5 text-xs font-semibold text-brass-400 transition hover:border-brass-400 hover:text-brass-300"
                >
                  <LogIn className="h-3.5 w-3.5" />
                  <span>Sign in</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => setMobileMenuOpen((prev) => !prev)}
                className="rounded-md p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white md:hidden"
                aria-label="Toggle navigation menu"
                aria-expanded={mobileMenuOpen}
              >
                {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>
            </div>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="md:hidden border-t border-slate-800 bg-slate-950/95 backdrop-blur px-4 pt-3 pb-4 space-y-1.5 animate-in slide-in-from-top-2">
            {currentUser && (
              <>
                <Link
                  href="/projects"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-2.5 rounded-md px-3 py-2.5 text-sm font-medium transition ${
                    pathname?.startsWith('/projects')
                      ? 'bg-slate-850 text-brass-400'
                      : 'text-slate-300 hover:bg-slate-850'
                  }`}
                >
                  <Film className="h-4 w-4" />
                  <span>Projects</span>
                </Link>
                <Link
                  href="/analytics"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-2.5 rounded-md px-3 py-2.5 text-sm font-medium transition ${
                    pathname?.startsWith('/analytics')
                      ? 'bg-slate-850 text-brass-400'
                      : 'text-slate-300 hover:bg-slate-850'
                  }`}
                >
                  <BarChart3 className="h-4 w-4" />
                  <span>Analytics</span>
                </Link>
              </>
            )}
            {currentUser && (
              <div className="border-t border-slate-800 px-3 pt-2.5 text-xs text-slate-400">
                Signed in as <span className="font-semibold text-slate-200">{currentUser.full_name}</span>{' '}
                <span className="font-mono text-[10px]">({currentUser.email})</span>
              </div>
            )}
          </div>
        )}
      </header>

      {modalOpen && (
        <div
          data-testid="auth-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="auth-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
        >
          <div className="relative w-full max-w-md rounded-lg border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2.5">
                <UserCircle className="h-5 w-5 text-brass-400" />
                <h3 id="auth-modal-title" className="font-display text-lg font-semibold text-slate-50">
                  {currentUser ? 'Switch role' : 'Sign in'}
                </h3>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="p-1 text-slate-400 transition hover:text-slate-200"
                aria-label="Close dialog"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {authError && (
              <div className="mt-4 rounded-md border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-400">
                {authError}
              </div>
            )}

            <p className="mt-4 text-xs text-slate-400">
              Choose your name, email and the role you need. Your workspace runs entirely in this browser.
            </p>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (customEmail.trim() && customName.trim()) {
                  handleDevLogin(customEmail.trim(), customName.trim(), customRole);
                }
              }}
              className="mt-4 space-y-3.5"
            >
              <div>
                <label htmlFor="login-name-input" className="mb-1.5 block text-xs font-medium text-slate-300">
                  Full Name
                </label>
                <input
                  id="login-name-input"
                  type="text"
                  required
                  data-testid="login-name-input"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  placeholder="e.g. Maya Lin"
                  className="ss-input"
                />
              </div>

              <div>
                <label htmlFor="login-email-input" className="mb-1.5 block text-xs font-medium text-slate-300">
                  Email Address
                </label>
                <input
                  id="login-email-input"
                  type="email"
                  required
                  data-testid="login-email-input"
                  value={customEmail}
                  onChange={(e) => setCustomEmail(e.target.value)}
                  placeholder="e.g. maya@production.co"
                  className="ss-input"
                />
              </div>

              <div>
                <label htmlFor="login-role-select" className="mb-1.5 block text-xs font-medium text-slate-300">
                  Role
                </label>
                <select
                  id="login-role-select"
                  data-testid="login-role-select"
                  value={customRole}
                  onChange={(e) => setCustomRole(e.target.value)}
                  className="ss-input"
                >
                  {ROLE_OPTIONS.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="ss-btn-ghost px-3 py-1.5 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !customEmail.trim() || !customName.trim()}
                  data-testid="login-submit-btn"
                  className="ss-btn-primary px-4 py-1.5 text-xs"
                >
                  {loading ? 'Signing in...' : currentUser ? 'Switch role' : 'Sign in'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
