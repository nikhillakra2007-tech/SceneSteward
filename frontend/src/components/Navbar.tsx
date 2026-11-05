'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ShieldCheck, Film, Users, Activity, LogOut, UserCircle } from 'lucide-react';
import { api, getAuthToken, User } from '@/lib/api';

export function Navbar() {
  const pathname = usePathname();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);

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
    try {
      await api.loginDev(email, name);
      await fetchUser();
    } catch (err: any) {
      alert(`Login failed: ${err.message}`);
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
                  onClick={handleLogout}
                  title="Logout"
                  className="p-1.5 rounded-lg border border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-400 hidden lg:inline">Quick Dev Login:</span>
                <button
                  disabled={loading}
                  onClick={() => handleDevLogin('olivia@example.com', 'Olivia Owner')}
                  className="text-xs px-2.5 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition disabled:opacity-50"
                >
                  Olivia (Director)
                </button>
                <button
                  disabled={loading}
                  onClick={() => handleDevLogin('claire@example.com', 'Claire Care')}
                  className="text-xs px-2.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium transition disabled:opacity-50"
                >
                  Claire (Care)
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
