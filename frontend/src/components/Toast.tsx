'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback((message: string, type: ToastType = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);

    setTimeout(() => {
      removeToast(id);
    }, 4500);
  }, [removeToast]);

  const success = useCallback((message: string) => showToast(message, 'success'), [showToast]);
  const error = useCallback((message: string) => showToast(message, 'error'), [showToast]);
  const warning = useCallback((message: string) => showToast(message, 'warning'), [showToast]);
  const info = useCallback((message: string) => showToast(message, 'info'), [showToast]);

  return (
    <ToastContext.Provider value={{ showToast, success, error, warning, info }}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none px-4 sm:px-0"
      >
        {toasts.map((t) => {
          const isError = t.type === 'error';
          const isSuccess = t.type === 'success';
          const isWarning = t.type === 'warning';

          return (
            <div
              key={t.id}
              role={isError ? 'alert' : 'status'}
              className={`pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl border shadow-xl backdrop-blur-md transition-all duration-200 animate-in fade-in slide-in-from-bottom-2 text-xs font-medium ${
                isError
                  ? 'bg-rose-950/95 border-rose-800 text-rose-200 shadow-rose-950/40'
                  : isSuccess
                  ? 'bg-emerald-950/95 border-emerald-800 text-emerald-200 shadow-emerald-950/40'
                  : isWarning
                  ? 'bg-amber-950/95 border-amber-800 text-amber-200 shadow-amber-950/40'
                  : 'bg-slate-900/95 border-slate-700 text-slate-200 shadow-slate-950/40'
              }`}
            >
              <div className="flex-shrink-0 mt-0.5">
                {isError && <AlertCircle className="h-4 w-4 text-rose-400" />}
                {isSuccess && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
                {isWarning && <AlertTriangle className="h-4 w-4 text-amber-400" />}
                {!isError && !isSuccess && !isWarning && <Info className="h-4 w-4 text-blue-400" />}
              </div>
              <div className="flex-1 leading-snug break-words">{t.message}</div>
              <button
                type="button"
                onClick={() => removeToast(t.id)}
                className="flex-shrink-0 text-slate-400 hover:text-white transition p-0.5"
                aria-label="Dismiss notification"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

