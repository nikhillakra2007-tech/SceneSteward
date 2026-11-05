'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { 
  UserCheck, 
  ShieldCheck, 
  FileCheck, 
  Lock, 
  HelpCircle, 
  AlertCircle, 
  CheckCircle2, 
  MessageSquare, 
  ArrowLeft 
} from 'lucide-react';
import { api, Participant, ConsentRecord, ProposedUse, TimelineEntry } from '@/lib/api';
import { ChoiceBadge } from '@/components/ConsentBadge';

const CANONICAL_CATEGORIES = [
  'interview_inclusion',
  'name_attribution',
  'likeness_display',
  'voice_recording',
  'sensitive_topics',
  'historical_footage',
  'personal_photos',
  'location_disclosure',
  'family_mention',
  'dramatization',
  'voice_cloning',
  'promotional_trailers',
  'social_media_clips',
  'international_broadcast',
  'future_syndication'
];

export default function ParticipantPortalPage() {
  const params = useParams();
  const participantId = params?.id as string;

  const [participant, setParticipant] = useState<Participant | null>(null);
  const [consents, setConsents] = useState<ConsentRecord[]>([]);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Participant Feedback Form
  const [feedback, setFeedback] = useState('');
  const [feedbackSent, setFeedbackSent] = useState(false);

  useEffect(() => {
    async function loadData() {
      if (!participantId) return;
      setLoading(true);
      setError(null);
      try {
        const pt = await api.getParticipant(participantId);
        setParticipant(pt);

        const cList = await api.getParticipantConsents(participantId);
        setConsents(cList.items || []);

        const tl = await api.getParticipantTimeline(participantId);
        setTimeline(tl.items || []);
      } catch (err: any) {
        setError(err.message || 'Error loading participant record');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [participantId]);

  const handleSendFeedback = (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedback.trim()) return;
    setFeedbackSent(true);
    setFeedback('');
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-400">
        <UserCheck className="h-10 w-10 mx-auto animate-pulse text-emerald-400 mb-3" />
        <p className="text-sm font-medium">Loading your consent transparency record...</p>
      </div>
    );
  }

  if (error || !participant) {
    return (
      <div className="p-8 text-center rounded-2xl border border-slate-800 bg-slate-900/30 text-slate-400 space-y-3">
        <AlertCircle className="h-10 w-10 mx-auto text-amber-400" />
        <h2 className="text-lg font-bold text-white">Record Not Found</h2>
        <p className="text-xs max-w-md mx-auto">{error || 'Participant record not accessible.'}</p>
        <Link href="/" className="inline-flex items-center space-x-1 text-xs text-emerald-400 hover:underline pt-2">
          <ArrowLeft className="h-3 w-3" />
          <span>Return Home</span>
        </Link>
      </div>
    );
  }

  const latestConsent = consents[0];

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Participant Header */}
      <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-6 sm:p-8 space-y-3 shadow-xl">
        <div className="flex items-center justify-between">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-800 text-emerald-400 text-xs font-semibold">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>Participant Dignity &amp; Consent Portal</span>
          </div>
          <Link
            href={`/projects/${participant.project_id}`}
            className="text-xs text-slate-400 hover:text-emerald-400 inline-flex items-center space-x-1"
          >
            <ArrowLeft className="h-3 w-3" />
            <span>Project Workspace</span>
          </Link>
        </div>

        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">{participant.display_name}</h1>
        <p className="text-xs text-slate-300">
          This portal gives you full visibility into what permissions you granted to the documentary production. 
          Under our core ethics guarantee, <strong>agreement to one use is never agreement to another use</strong>.
        </p>

        <div className="pt-2 flex flex-wrap gap-4 text-xs text-slate-400">
          <div>Language: <span className="text-slate-200 font-semibold">{participant.preferred_language}</span></div>
          <div>Contact: <span className="text-slate-200 font-semibold">{participant.preferred_contact_method}</span></div>
          <div>Status: <span className="text-emerald-400 font-semibold font-mono">{participant.status}</span></div>
        </div>
      </div>

      {/* Consent Record Breakdown */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <FileCheck className="h-5 w-5 text-emerald-400" />
              <span>Your Current Consent Record</span>
            </h2>
            <p className="text-xs text-slate-400">
              {latestConsent ? `Version ${latestConsent.version} (${latestConsent.source_type})` : 'No consent record on file'}
            </p>
          </div>
          {latestConsent && (
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">
              {latestConsent.status}
            </span>
          )}
        </div>

        {latestConsent ? (
          <div className="space-y-4">
            {latestConsent.explanation && (
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 italic">
                &ldquo;{latestConsent.explanation}&rdquo;
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {CANONICAL_CATEGORIES.map((cat) => {
                const choiceData = latestConsent.choices?.[cat];
                const choiceVal = typeof choiceData === 'object' && choiceData ? choiceData.choice : (choiceData || 'not_discussed');
                return (
                  <div key={cat} className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between space-y-2">
                    <span className="text-xs font-medium text-slate-300">
                      {cat.replace(/_/g, ' ')}
                    </span>
                    <div>
                      <ChoiceBadge choice={choiceVal} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-500 italic">No formal consent record has been logged for your profile yet.</p>
        )}
      </div>

      {/* Participant Question / Feedback Form */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
        <h2 className="text-base font-bold text-white flex items-center space-x-2">
          <MessageSquare className="h-5 w-5 text-emerald-400" />
          <span>Need Clarification or Want to Change a Preference?</span>
        </h2>
        <p className="text-xs text-slate-400 leading-relaxed">
          You have the right to ask questions or decline any use at any time before final picture lock. 
          Your request is routed directly to the documentary&apos;s designated Participant Care Lead.
        </p>

        {feedbackSent ? (
          <div className="p-4 rounded-xl border border-emerald-800/80 bg-emerald-950/30 text-emerald-300 text-xs flex items-center space-x-2">
            <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
            <span>Thank you. Your message has been securely submitted to the Participant Care team.</span>
          </div>
        ) : (
          <form onSubmit={handleSendFeedback} className="space-y-3">
            <textarea
              rows={3}
              placeholder="e.g. I have concerns about using my home location in promotional trailers..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
            />
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={!feedback.trim()}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold disabled:opacity-50 transition"
              >
                Send to Care Lead
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Personal Audit Timeline */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
        <h2 className="text-base font-bold text-white flex items-center space-x-2">
          <Lock className="h-4 w-4 text-emerald-400" />
          <span>Your Accountability Timeline</span>
        </h2>
        <p className="text-xs text-slate-400">
          Immutable event log of every action touching your consent records.
        </p>

        {timeline.length === 0 ? (
          <p className="text-xs text-slate-500 italic">No historical events recorded yet.</p>
        ) : (
          <div className="space-y-2">
            {timeline.map((entry) => (
              <div key={entry.id} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs flex items-center justify-between">
                <span className="font-semibold text-slate-200">{entry.action}</span>
                <span className="text-[11px] text-slate-500">{new Date(entry.timestamp).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
