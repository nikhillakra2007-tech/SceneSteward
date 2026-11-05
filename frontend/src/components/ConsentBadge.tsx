import React from 'react';

interface ChoiceBadgeProps {
  choice: string;
}

export function ChoiceBadge({ choice }: ChoiceBadgeProps) {
  const norm = (choice || '').toLowerCase();
  
  if (norm === 'agreed') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
        Agreed
      </span>
    );
  }
  if (norm === 'declined') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-rose-950 text-rose-400 border border-rose-800">
        Declined
      </span>
    );
  }
  if (norm === 'needs_clarification' || norm === 'awaiting_confirmation') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-950 text-amber-400 border border-amber-800">
        Needs Clarification
      </span>
    );
  }
  if (norm === 'not_discussed') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
        Not Discussed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
      {choice}
    </span>
  );
}

interface OutcomeBadgeProps {
  outcome: string;
}

export function OutcomeBadge({ outcome }: OutcomeBadgeProps) {
  const o = (outcome || '').toUpperCase();
  
  if (o === 'PERMITTED') {
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-bold bg-emerald-950 text-emerald-400 border border-emerald-700 shadow-sm">
        PERMITTED
      </span>
    );
  }
  if (o === 'PARTICIPANT_DECLINED') {
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-bold bg-rose-950 text-rose-300 border border-rose-700 shadow-sm">
        PARTICIPANT DECLINED
      </span>
    );
  }
  if (o === 'REQUIRES_CARE_REVIEW' || o === 'RESTRICTED') {
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-bold bg-amber-950 text-amber-300 border border-amber-700 shadow-sm">
        {o.replace(/_/g, ' ')}
      </span>
    );
  }
  if (o === 'UNRESOLVED' || o === 'REQUIRES_LEGAL_REVIEW') {
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-bold bg-purple-950 text-purple-300 border border-purple-700 shadow-sm">
        {o.replace(/_/g, ' ')}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-bold bg-slate-800 text-slate-300 border border-slate-600">
      {outcome}
    </span>
  );
}
