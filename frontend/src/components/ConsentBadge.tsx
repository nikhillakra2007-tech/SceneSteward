import React from 'react';

const base = 'inline-flex items-center rounded-sm border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.12em]';

export function ChoiceBadge({ choice }: { choice: string }) {
  const norm = (choice || '').toLowerCase();

  if (norm === 'agreed') {
    return <span className={`${base} border-emerald-800 bg-emerald-950 text-emerald-400`}>Agreed</span>;
  }
  if (norm === 'declined') {
    return <span className={`${base} border-rose-800 bg-rose-950 text-rose-400`}>Declined</span>;
  }
  if (norm === 'needs_clarification' || norm === 'awaiting_confirmation') {
    return <span className={`${base} border-amber-800 bg-amber-950 text-amber-400`}>Needs Clarification</span>;
  }
  if (norm === 'not_discussed') {
    return <span className={`${base} border-slate-700 bg-slate-850 text-slate-400`}>Not Discussed</span>;
  }
  return <span className={`${base} border-slate-700 bg-slate-850 text-slate-300`}>{choice}</span>;
}

export function OutcomeBadge({ outcome }: { outcome: string }) {
  const o = (outcome || '').toUpperCase();

  if (o === 'PERMITTED') {
    return <span className={`${base} border-emerald-700 bg-emerald-950 px-2.5 py-1 text-emerald-300`}>PERMITTED</span>;
  }
  if (o === 'PARTICIPANT_DECLINED') {
    return <span className={`${base} border-rose-700 bg-rose-950 px-2.5 py-1 text-rose-300`}>PARTICIPANT DECLINED</span>;
  }
  if (o === 'REQUIRES_CARE_REVIEW' || o === 'RESTRICTED') {
    return <span className={`${base} border-amber-700 bg-amber-950 px-2.5 py-1 text-amber-300`}>{o.replace(/_/g, ' ')}</span>;
  }
  if (o === 'UNRESOLVED' || o === 'REQUIRES_LEGAL_REVIEW') {
    return <span className={`${base} border-purple-700 bg-purple-950 px-2.5 py-1 text-purple-300`}>{o.replace(/_/g, ' ')}</span>;
  }
  return <span className={`${base} border-slate-600 bg-slate-850 px-2.5 py-1 text-slate-300`}>{outcome}</span>;
}
