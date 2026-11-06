'use client';

import React from 'react';
import { TrendDataPoint } from '@/lib/analytics-types';

interface TrendsChartProps {
  series: TrendDataPoint[];
}

export function TrendsChart({ series }: TrendsChartProps) {
  if (!series || series.length === 0) {
    return (
      <div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-xl">
        <p className="text-sm text-slate-400">No trend events recorded in this period.</p>
      </div>
    );
  }

  // Calculate maximum value across series to scale SVG
  const maxVal = Math.max(
    1,
    ...series.map((p) =>
      Math.max(p.consent_confirmed, p.reviews_decided, p.withdrawals_requested, p.tasks_completed)
    )
  );

  const width = 600;
  const height = 180;
  const padding = 20;

  const pointsCount = series.length;
  const getX = (idx: number) => {
    if (pointsCount <= 1) return width / 2;
    return padding + (idx / (pointsCount - 1)) * (width - 2 * padding);
  };

  const getY = (val: number) => {
    return height - padding - (val / maxVal) * (height - 2 * padding);
  };

  const createPath = (key: keyof TrendDataPoint) => {
    return series
      .map((p, idx) => {
        const x = getX(idx);
        const y = getY(Number(p[key]) || 0);
        return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(' ');
  };

  const pathConsent = createPath('consent_confirmed');
  const pathReviews = createPath('reviews_decided');
  const pathWithdrawals = createPath('withdrawals_requested');
  const pathTasks = createPath('tasks_completed');

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 mb-4 gap-2">
        <div>
          <h3 className="text-base font-semibold text-slate-100">Operational Trends & Event Activity</h3>
          <p className="text-xs text-slate-400 mt-0.5">Chronological activity across consent, reviews, and tasks.</p>
        </div>
        <div className="flex items-center flex-wrap gap-3 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400 inline-block" />
            <span className="text-slate-300">Consents</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="h-2 w-2 rounded-full bg-blue-400 inline-block" />
            <span className="text-slate-300">Reviews</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-400 inline-block" />
            <span className="text-slate-300">Tasks</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="h-2 w-2 rounded-full bg-rose-400 inline-block" />
            <span className="text-slate-300">Withdrawals</span>
          </div>
        </div>
      </div>

      <div className="relative w-full overflow-hidden">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-44 overflow-visible">
          {/* Subtle grid lines */}
          <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="#334155" strokeDasharray="3 3" opacity={0.4} />
          <line x1={padding} y1={height / 2} x2={width - padding} y2={height / 2} stroke="#334155" strokeDasharray="3 3" opacity={0.4} />
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#334155" strokeDasharray="3 3" opacity={0.6} />

          {/* Paths */}
          <path d={pathConsent} fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d={pathReviews} fill="none" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <path d={pathTasks} fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          {series.some((p) => p.withdrawals_requested > 0) && (
            <path d={pathWithdrawals} fill="none" stroke="#f43f5e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          )}

          {/* Active Data Points */}
          {series.map((p, idx) => (
            <g key={p.date}>
              {p.consent_confirmed > 0 && (
                <circle cx={getX(idx)} cy={getY(p.consent_confirmed)} r="3" fill="#10b981" />
              )}
              {p.withdrawals_requested > 0 && (
                <circle cx={getX(idx)} cy={getY(p.withdrawals_requested)} r="3.5" fill="#f43f5e" />
              )}
            </g>
          ))}
        </svg>

        {/* X-Axis dates */}
        <div className="flex justify-between text-[10px] text-slate-500 mt-2 px-2 font-mono">
          <span>{series[0]?.date}</span>
          {series.length > 2 && <span>{series[Math.floor(series.length / 2)]?.date}</span>}
          <span>{series[series.length - 1]?.date}</span>
        </div>
      </div>
    </div>
  );
}

