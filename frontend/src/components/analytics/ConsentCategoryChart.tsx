'use client';

import React from 'react';
import { CategoryMetricDetail } from '@/lib/analytics-types';

interface ConsentCategoryChartProps {
  categories: CategoryMetricDetail[];
  totalParticipants: number;
}

export function ConsentCategoryChart({ categories, totalParticipants }: ConsentCategoryChartProps) {
  if (!categories || categories.length === 0) {
    return (
      <div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-xl">
        <p className="text-sm text-slate-400">No category breakdown data available for this scope.</p>
      </div>
    );
  }

  const formatCategoryName = (raw: string) => {
    return raw
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 mb-6 gap-2">
        <div>
          <h3 className="text-base font-semibold text-slate-100">15-Category Consent Coverage</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Breakdown across canonical documentary categories. Silence or missing records are strictly non-consent.
          </p>
        </div>
        <div className="flex items-center flex-wrap gap-3 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-emerald-500 inline-block" />
            <span className="text-slate-300">Agreed</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-rose-500 inline-block" />
            <span className="text-slate-300">Declined</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-amber-500 inline-block" />
            <span className="text-slate-300">Clarification</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-slate-700 inline-block" />
            <span className="text-slate-400">Not Discussed</span>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {categories.map((cat) => {
          const tot = cat.total_applicable || 1;
          const agreedPct = (cat.agreed / tot) * 100;
          const declinedPct = (cat.declined / tot) * 100;
          const clarifPct = ((cat.needs_clarification + cat.awaiting_confirmation + cat.explained) / tot) * 100;
          const notDiscPct = Math.max(0, 100 - (agreedPct + declinedPct + clarifPct));

          return (
            <div key={cat.category} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-slate-200">{formatCategoryName(cat.category)}</span>
                <div className="flex items-center space-x-3 text-slate-400">
                  <span>
                    Approval: <strong className="text-emerald-400">{cat.approval_rate.toFixed(1)}%</strong>
                  </span>
                  <span>
                    Resolution: <strong className="text-slate-200">{cat.resolution_rate.toFixed(1)}%</strong>
                  </span>
                  <span className="hidden sm:inline text-slate-500">
                    ({cat.agreed} / {cat.total_applicable})
                  </span>
                </div>
              </div>

              {/* Horizontal Multi-Segment Progress Bar */}
              <div className="h-3 w-full bg-slate-800 rounded-full overflow-hidden flex shadow-inner">
                {agreedPct > 0 && (
                  <div
                    style={{ width: `${agreedPct}%` }}
                    title={`Agreed: ${cat.agreed} (${agreedPct.toFixed(1)}%)`}
                    className="bg-emerald-500 hover:bg-emerald-400 transition"
                  />
                )}
                {declinedPct > 0 && (
                  <div
                    style={{ width: `${declinedPct}%` }}
                    title={`Declined: ${cat.declined} (${declinedPct.toFixed(1)}%)`}
                    className="bg-rose-500 hover:bg-rose-400 transition"
                  />
                )}
                {clarifPct > 0 && (
                  <div
                    style={{ width: `${clarifPct}%` }}
                    title={`Clarification: ${cat.needs_clarification} (${clarifPct.toFixed(1)}%)`}
                    className="bg-amber-500 hover:bg-amber-400 transition"
                  />
                )}
                {notDiscPct > 0 && (
                  <div
                    style={{ width: `${notDiscPct}%` }}
                    title={`Not Discussed: ${cat.not_discussed} (${notDiscPct.toFixed(1)}%)`}
                    className="bg-slate-700 hover:bg-slate-600 transition"
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

