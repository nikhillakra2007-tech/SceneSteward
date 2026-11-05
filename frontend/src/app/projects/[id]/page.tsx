'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { 
  Film, 
  Users, 
  FileCheck, 
  FileText, 
  GitCompare, 
  CheckSquare, 
  ListTodo, 
  Mail, 
  History, 
  Plus, 
  AlertTriangle, 
  CheckCircle2, 
  ShieldAlert, 
  Clock,
  ArrowRight,
  ExternalLink,
  Upload,
  Play
} from 'lucide-react';
import { 
  api, 
  Project, 
  Participant, 
  ConsentRecord, 
  ProposedUse, 
  Review, 
  Task, 
  ReleaseDocument, 
  Communication, 
  TimelineEntry,
  getAuthToken 
} from '@/lib/api';
import { ChoiceBadge, OutcomeBadge } from '@/components/ConsentBadge';

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

export default function ProjectWorkspacePage() {
  const params = useParams();
  const projectId = params?.id as string;

  const [activeTab, setActiveTab] = useState<'overview' | 'participants' | 'consents' | 'documents' | 'proposed-uses' | 'reviews' | 'tasks' | 'communications' | 'timeline'>('overview');
  const [project, setProject] = useState<Project | null>(null);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [consents, setConsents] = useState<ConsentRecord[]>([]);
  const [documents, setDocuments] = useState<ReleaseDocument[]>([]);
  const [proposedUses, setProposedUses] = useState<ProposedUse[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [comms, setComms] = useState<Communication[]>([]);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionError, setActionError] = useState<string | null>(null);

  // Modals & form states
  const [showAddParticipant, setShowAddParticipant] = useState(false);
  const [newPartName, setNewPartName] = useState('');
  const [newPartLang, setNewPartLang] = useState('English');
  const [newPartContact, setNewPartContact] = useState('email');

  const [showAddConsent, setShowAddConsent] = useState(false);
  const [consentPartId, setConsentPartId] = useState('');
  const [consentSourceType, setConsentSourceType] = useState('release_form');
  const [consentExplanation, setConsentExplanation] = useState('Production standard release agreement');
  const [consentChoices, setConsentChoices] = useState<Record<string, string>>({
    interview_inclusion: 'agreed',
    name_attribution: 'agreed',
    likeness_display: 'agreed',
    voice_recording: 'agreed',
    sensitive_topics: 'not_discussed',
    historical_footage: 'agreed',
    personal_photos: 'agreed',
    location_disclosure: 'not_discussed',
    family_mention: 'not_discussed',
    dramatization: 'declined',
    voice_cloning: 'declined',
    promotional_trailers: 'needs_clarification',
    social_media_clips: 'agreed',
    international_broadcast: 'agreed',
    future_syndication: 'not_discussed'
  });

  const [showAddProposedUse, setShowAddProposedUse] = useState(false);
  const [usePartId, setUsePartId] = useState('');
  const [useType, setUseType] = useState('promotional_trailers');
  const [usePlatform, setUsePlatform] = useState('Theatrical & Digital');
  const [useDesc, setUseDesc] = useState('Promotional trailer featuring interview snippet with dynamic background score');

  const [selectedUseFindings, setSelectedUseFindings] = useState<any[] | null>(null);
  const [selectedUseAnalysis, setSelectedUseAnalysis] = useState<any | null>(null);

  // Review decision form
  const [decidingReviewId, setDecidingReviewId] = useState<string | null>(null);
  const [decisionReason, setDecisionReason] = useState('');

  const loadWorkspace = async () => {
    if (!projectId || !getAuthToken()) return;
    setLoading(true);
    setActionError(null);
    try {
      const p = await api.getProject(projectId);
      setProject(p);

      const parts = await api.listParticipants(projectId);
      setParticipants(parts.items || []);
      if (parts.items?.length > 0) {
        setConsentPartId(parts.items[0].id);
        setUsePartId(parts.items[0].id);

        // Load consents for all participants
        const allConsents: ConsentRecord[] = [];
        for (const pt of parts.items) {
          try {
            const cList = await api.getParticipantConsents(pt.id);
            if (cList.items) allConsents.push(...cList.items);
          } catch {
            // ignore
          }
        }
        setConsents(allConsents);
      }

      const docs = await api.listDocuments(projectId);
      setDocuments(docs.items || []);

      const uses = await api.listProposedUses(projectId);
      setProposedUses(uses.items || []);

      const revs = await api.listReviews(projectId);
      setReviews(revs.items || []);

      const t = await api.listTasks(projectId);
      setTasks(t.items || []);

      const c = await api.listCommunications(projectId);
      setComms(c || []);

      const tl = await api.getProjectTimeline(projectId);
      setTimeline(tl.items || []);
    } catch (err: any) {
      setActionError(err.message || 'Error loading workspace');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkspace();
  }, [projectId]);

  // Handlers
  const handleCreateParticipant = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createParticipant(projectId, {
        display_name: newPartName.trim(),
        preferred_language: newPartLang,
        preferred_contact_method: newPartContact,
      });
      setShowAddParticipant(false);
      setNewPartName('');
      await loadWorkspace();
    } catch (err: any) {
      alert(`Failed to add participant: ${err.message}`);
    }
  };

  const handleCreateConsent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!consentPartId) return;
    try {
      const choicesPayload: Record<string, { choice: string }> = {};
      Object.entries(consentChoices).forEach(([cat, val]) => {
        choicesPayload[cat] = { choice: val };
      });

      await api.createConsentRecord(consentPartId, {
        source_type: consentSourceType,
        explanation: consentExplanation,
        choices: choicesPayload,
      });
      setShowAddConsent(false);
      await loadWorkspace();
    } catch (err: any) {
      alert(`Failed to record consent: ${err.message}`);
    }
  };

  const handleCreateProposedUse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!usePartId) return;
    try {
      await api.createProposedUse(projectId, {
        participant_id: usePartId,
        use_type: useType,
        platform: usePlatform,
        context_description: useDesc,
        run_analysis: true, // triggers backend 63-matrix comparison engine immediately!
      });
      setShowAddProposedUse(false);
      await loadWorkspace();
      setActiveTab('proposed-uses');
    } catch (err: any) {
      alert(`Failed to propose use: ${err.message}`);
    }
  };

  const handleRunAnalysis = async (useId: string) => {
    try {
      const result = await api.analyseProposedUse(useId);
      setSelectedUseAnalysis(result);
      const findings = await api.getAgentFindings(useId);
      setSelectedUseFindings(findings);
      await loadWorkspace();
    } catch (err: any) {
      alert(`Analysis failed: ${err.message}`);
    }
  };

  const handleViewFindings = async (useId: string) => {
    try {
      const findings = await api.getAgentFindings(useId);
      setSelectedUseFindings(findings);
    } catch (err: any) {
      alert(`Failed to load findings: ${err.message}`);
    }
  };

  const handleRecordReviewDecision = async (
    review: Review,
    decision: 'approved' | 'approved_with_conditions' | 'rejected'
  ) => {
    if (!decisionReason.trim()) {
      alert('A human decision reason is mandatory for ethical accountability.');
      return;
    }
    try {
      await api.recordHumanDecision(review.id, {
        decision,
        reason: decisionReason.trim(),
        expected_version: review.version,
      });
      setDecidingReviewId(null);
      setDecisionReason('');
      await loadWorkspace();
    } catch (err: any) {
      alert(`Decision failed: ${err.message}`);
    }
  };

  const handleApproveCommunication = async (comm: Communication) => {
    try {
      await api.approveCommunication(comm.id, comm.version);
      await loadWorkspace();
    } catch (err: any) {
      alert(`Approval failed: ${err.message}`);
    }
  };

  const handleTaskStatusToggle = async (task: Task) => {
    const nextStatus = task.status === 'completed' ? 'in_progress' : 'completed';
    try {
      await api.updateTask(task.id, { status: nextStatus });
      await loadWorkspace();
    } catch (err: any) {
      alert(`Update failed: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-400">
        <Film className="h-10 w-10 mx-auto animate-pulse text-emerald-400 mb-3" />
        <p className="text-sm font-medium">Loading documentary workspace securely...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="p-8 text-center rounded-2xl border border-slate-800 bg-slate-900/30 text-slate-400 space-y-3">
        <ShieldAlert className="h-10 w-10 mx-auto text-amber-400" />
        <h2 className="text-lg font-bold text-white">Project Not Found or Unauthorized</h2>
        <p className="text-xs max-w-md mx-auto">
          Ensure you are authenticated with an active project membership role (Owner, Producer, Care Lead, Director).
        </p>
        <Link
          href="/projects"
          className="inline-flex items-center space-x-2 text-xs font-semibold text-emerald-400 hover:underline pt-2"
        >
          <span>&larr; Return to Projects</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900 to-slate-950 p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-xl">
        <div className="space-y-2 max-w-2xl">
          <div className="flex items-center space-x-2">
            <Link href="/projects" className="text-xs text-slate-400 hover:text-emerald-400 transition">
              Projects
            </Link>
            <span className="text-xs text-slate-600">/</span>
            <span className="text-xs text-emerald-400 font-semibold">{project.status}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">{project.title}</h1>
          <p className="text-xs sm:text-sm text-slate-300">
            {project.description || project.purpose || 'Documentary consent coordination and participant care.'}
          </p>
        </div>

        <div className="flex flex-wrap gap-2.5">
          <button
            onClick={() => setShowAddParticipant(true)}
            className="inline-flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition"
          >
            <Users className="h-3.5 w-3.5 text-emerald-400" />
            <span>+ Participant</span>
          </button>
          <button
            onClick={() => setShowAddConsent(true)}
            disabled={participants.length === 0}
            className="inline-flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition disabled:opacity-40"
          >
            <FileCheck className="h-3.5 w-3.5 text-emerald-400" />
            <span>+ Consent Record</span>
          </button>
          <button
            onClick={() => setShowAddProposedUse(true)}
            disabled={participants.length === 0}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition shadow-md shadow-emerald-950/60 disabled:opacity-40"
          >
            <GitCompare className="h-3.5 w-3.5" />
            <span>+ Propose Use</span>
          </button>
        </div>
      </div>

      {actionError && (
        <div className="p-4 rounded-xl border border-rose-800/80 bg-rose-950/30 text-rose-300 text-xs flex items-center space-x-2">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      {/* Tabs Bar */}
      <div className="border-b border-slate-800 flex overflow-x-auto gap-2 text-xs font-medium scrollbar-none">
        {[
          { key: 'overview', label: 'Overview', icon: Film, count: null },
          { key: 'participants', label: 'Participants', icon: Users, count: participants.length },
          { key: 'consents', label: 'Consent Records', icon: FileCheck, count: consents.length },
          { key: 'documents', label: 'Release Docs', icon: FileText, count: documents.length },
          { key: 'proposed-uses', label: 'Proposed Uses', icon: GitCompare, count: proposedUses.length },
          { key: 'reviews', label: 'Human Reviews', icon: CheckSquare, count: reviews.length },
          { key: 'tasks', label: 'Tasks', icon: ListTodo, count: tasks.length },
          { key: 'communications', label: 'Care Outreach', icon: Mail, count: comms.length },
          { key: 'timeline', label: 'Audit Timeline', icon: History, count: timeline.length },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`pb-3 px-3.5 flex items-center space-x-2 border-b-2 whitespace-nowrap transition ${
                isActive
                  ? 'border-emerald-500 text-emerald-400 font-bold'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
              {tab.count !== null && (
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                  isActive ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-slate-800 text-slate-400'
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-1">
              <div className="text-xs text-slate-400">Total Participants</div>
              <div className="text-2xl font-extrabold text-white">{participants.length}</div>
              <div className="text-[11px] text-emerald-400">Active roster members</div>
            </div>
            <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-1">
              <div className="text-xs text-slate-400">Active Consents</div>
              <div className="text-2xl font-extrabold text-white">{consents.length}</div>
              <div className="text-[11px] text-emerald-400">15 canonical categories tracked</div>
            </div>
            <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-1">
              <div className="text-xs text-slate-400">Proposed Uses</div>
              <div className="text-2xl font-extrabold text-white">{proposedUses.length}</div>
              <div className="text-[11px] text-slate-400">Under continuous comparison</div>
            </div>
            <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-1">
              <div className="text-xs text-slate-400">Pending Reviews</div>
              <div className="text-2xl font-extrabold text-amber-400">
                {reviews.filter((r) => r.review_status === 'pending').length}
              </div>
              <div className="text-[11px] text-amber-500">Require human sign-off</div>
            </div>
          </div>

          <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/30 space-y-4">
            <h3 className="text-sm font-bold text-slate-200">Production Governance &amp; Purpose</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-300">
              <div>
                <span className="text-slate-500 block">Themes:</span>
                <span className="font-medium text-slate-200">{project.themes?.join(', ') || 'General Documentary'}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Distribution Plan:</span>
                <span className="font-medium text-slate-200">{project.distribution_plan || 'Pending final agreement'}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Participants */}
      {activeTab === 'participants' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-base font-bold text-white">Participant Roster</h2>
            <button
              onClick={() => setShowAddParticipant(true)}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Add Participant</span>
            </button>
          </div>

          {participants.length === 0 ? (
            <div className="p-8 text-center rounded-xl border border-dashed border-slate-800 text-slate-500 text-xs">
              No participants registered yet. Add a participant to begin tracking releases.
            </div>
          ) : (
            <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-900/40">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="p-3.5">Name</th>
                    <th className="p-3.5">Language</th>
                    <th className="p-3.5">Contact Method</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {participants.map((pt) => (
                    <tr key={pt.id} className="hover:bg-slate-800/30 transition">
                      <td className="p-3.5 font-semibold text-slate-100">{pt.display_name}</td>
                      <td className="p-3.5 text-slate-300">{pt.preferred_language}</td>
                      <td className="p-3.5 text-slate-300">{pt.preferred_contact_method}</td>
                      <td className="p-3.5">
                        <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px] font-mono">
                          {pt.status}
                        </span>
                      </td>
                      <td className="p-3.5 text-right space-x-2">
                        <Link
                          href={`/participant/${pt.id}`}
                          className="inline-flex items-center space-x-1 text-emerald-400 hover:underline font-semibold"
                        >
                          <span>Participant View</span>
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Consent Records */}
      {activeTab === 'consents' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-base font-bold text-white">Recorded Consents</h2>
              <p className="text-xs text-slate-400">Canonical category matrix per participant agreement version.</p>
            </div>
            <button
              onClick={() => setShowAddConsent(true)}
              disabled={participants.length === 0}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold disabled:opacity-50"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Record New Consent</span>
            </button>
          </div>

          {consents.length === 0 ? (
            <div className="p-8 text-center rounded-xl border border-dashed border-slate-800 text-slate-500 text-xs">
              No consent records logged yet. Click &ldquo;Record New Consent&rdquo; to input signed agreements.
            </div>
          ) : (
            <div className="space-y-4">
              {consents.map((c) => {
                const pt = participants.find((p) => p.id === c.participant_id);
                return (
                  <div key={c.id} className="p-5 rounded-xl border border-slate-800 bg-slate-900/50 space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                      <div>
                        <span className="text-xs text-slate-400">Participant:</span>{' '}
                        <span className="font-bold text-slate-100">{pt ? pt.display_name : c.participant_id}</span>
                        <span className="ml-3 px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[10px] font-mono">
                          Source: {c.source_type} (v{c.version})
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 text-[11px] font-mono">
                          {c.status}
                        </span>
                        <span className="text-xs text-slate-500">
                          {new Date(c.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>

                    {c.explanation && (
                      <p className="text-xs text-slate-300 italic bg-slate-950/60 p-2.5 rounded border border-slate-800/80">
                        &ldquo;{c.explanation}&rdquo;
                      </p>
                    )}

                    <div>
                      <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                        15 Canonical Categories:
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 text-xs">
                        {CANONICAL_CATEGORIES.map((cat) => {
                          const choiceData = c.choices?.[cat];
                          const choiceVal = typeof choiceData === 'object' && choiceData ? choiceData.choice : (choiceData || 'not_discussed');
                          return (
                            <div key={cat} className="p-2 rounded bg-slate-950/60 border border-slate-800 flex flex-col justify-between space-y-1">
                              <span className="text-[10px] text-slate-400 truncate" title={cat}>
                                {cat.replace(/_/g, ' ')}
                              </span>
                              <ChoiceBadge choice={choiceVal} />
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Documents */}
      {activeTab === 'documents' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-base font-bold text-white">Release Documents</h2>
              <p className="text-xs text-slate-400">Scanned agreements checked with ClamAV antivirus and encrypted at rest.</p>
            </div>
          </div>

          {documents.length === 0 ? (
            <div className="p-8 text-center rounded-xl border border-dashed border-slate-800 text-slate-500 text-xs">
              No release documents uploaded for this project yet.
            </div>
          ) : (
            <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-900/40">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="p-3.5">Filename</th>
                    <th className="p-3.5">Mime Type</th>
                    <th className="p-3.5">Antivirus Status</th>
                    <th className="p-3.5">Uploaded</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-800/30 transition">
                      <td className="p-3.5 font-medium text-slate-200">{doc.file_name}</td>
                      <td className="p-3.5 text-slate-400 font-mono text-[11px]">{doc.mime_type}</td>
                      <td className="p-3.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${
                          doc.scan_status === 'clean'
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                            : 'bg-rose-950 text-rose-400 border border-rose-800'
                        }`}>
                          {doc.scan_status}
                        </span>
                      </td>
                      <td className="p-3.5 text-slate-500">{new Date(doc.created_at).toLocaleDateString()}</td>
                      <td className="p-3.5 text-right">
                        <button
                          onClick={async () => {
                            try {
                              const ext = await api.extractDocument(doc.id);
                              alert(`Extracted text preview:\n\n${ext.extracted_text.slice(0, 300)}...`);
                            } catch (err: any) {
                              alert(`Extraction failed: ${err.message}`);
                            }
                          }}
                          className="text-xs text-emerald-400 hover:underline font-semibold"
                        >
                          Run OCR
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Proposed Uses & Comparison Engine */}
      {activeTab === 'proposed-uses' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-base font-bold text-white">Proposed Footage &amp; Likeness Uses</h2>
              <p className="text-xs text-slate-400">
                Automated 63-case comparison engine identifies discrepancies, overreach, and unconsented syndication.
              </p>
            </div>
            <button
              onClick={() => setShowAddProposedUse(true)}
              disabled={participants.length === 0}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold disabled:opacity-50"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Propose Use</span>
            </button>
          </div>

          {proposedUses.length === 0 ? (
            <div className="p-8 text-center rounded-xl border border-dashed border-slate-800 text-slate-500 text-xs">
              No proposed uses submitted. Click &ldquo;Propose Use&rdquo; to test a planned footage or promotional use against participant consent.
            </div>
          ) : (
            <div className="space-y-4">
              {proposedUses.map((use) => {
                const pt = participants.find((p) => p.id === use.participant_id);
                return (
                  <div key={use.id} className="p-5 rounded-xl border border-slate-800 bg-slate-900/50 space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                      <div>
                        <span className="text-xs text-slate-400">Participant:</span>{' '}
                        <span className="font-bold text-white">{pt ? pt.display_name : use.participant_id}</span>
                        <span className="ml-3 px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-xs font-mono">
                          {use.use_type}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs px-2.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-mono">
                          Status: {use.status}
                        </span>
                        <button
                          onClick={() => handleRunAnalysis(use.id)}
                          className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-300 border border-emerald-700/60 text-xs font-semibold transition"
                        >
                          <Play className="h-3 w-3" />
                          <span>Re-Analyze</span>
                        </button>
                        <button
                          onClick={() => handleViewFindings(use.id)}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-semibold transition"
                        >
                          Findings
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-300">
                      <div>
                        <span className="text-slate-500 block">Platform:</span>
                        <span>{use.platform || 'Not specified'}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Territory / Scope:</span>
                        <span>{use.territory || 'Not specified'}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Context Description:</span>
                        <span>{use.context_description || 'None provided'}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Advisory findings drawer / modal if loaded */}
          {selectedUseFindings && (
            <div className="p-5 rounded-xl border border-indigo-900/60 bg-indigo-950/20 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-indigo-300 uppercase tracking-wider flex items-center space-x-2">
                  <ShieldAlert className="h-4 w-4 text-indigo-400" />
                  <span>Advisory Agent Findings &amp; Analysis</span>
                </h3>
                <button
                  onClick={() => setSelectedUseFindings(null)}
                  className="text-xs text-indigo-400 hover:text-white"
                >
                  ✕ Close
                </button>
              </div>

              {selectedUseFindings.length === 0 ? (
                <p className="text-xs text-slate-400">No agent findings recorded yet for this proposed use.</p>
              ) : (
                <div className="space-y-2">
                  {selectedUseFindings.map((f, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-200">{f.agent_name}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                          {f.execution_status}
                        </span>
                      </div>
                      <div className="text-slate-400 text-[11px]">
                        {typeof f.output_data === 'object' ? JSON.stringify(f.output_data) : f.output_data}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 6: Human Reviews */}
      {activeTab === 'reviews' && (
        <div className="space-y-4">
          <div>
            <h2 className="text-base font-bold text-white">Human Review Queue</h2>
            <p className="text-xs text-slate-400">
              Only authorized staff can make binding decisions. Automated agents can never approve or decline uses.
            </p>
          </div>

          {reviews.length === 0 ? (
            <div className="p-8 text-center rounded-xl border border-dashed border-slate-800 text-slate-500 text-xs">
              No reviews in queue.
            </div>
          ) : (
            <div className="space-y-4">
              {reviews.map((rev) => (
                <div key={rev.id} className="p-5 rounded-xl border border-slate-800 bg-slate-900/50 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                    <div>
                      <span className="text-xs text-slate-400">Review ID:</span>{' '}
                      <span className="font-mono text-xs text-slate-300">{rev.id}</span>
                      <span className="ml-3 px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-xs font-mono">
                        Status: {rev.review_status}
                      </span>
                    </div>
                    {rev.human_decision && (
                      <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${
                        rev.human_decision === 'approved'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : rev.human_decision === 'rejected'
                          ? 'bg-rose-950 text-rose-400 border border-rose-800'
                          : 'bg-amber-950 text-amber-400 border border-amber-800'
                      }`}>
                        Decision: {rev.human_decision.replace(/_/g, ' ')}
                      </span>
                    )}
                  </div>

                  {rev.decision_reason && (
                    <div className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded border border-slate-800">
                      <span className="text-slate-500 font-semibold block mb-0.5">Decision Rationale:</span>
                      {rev.decision_reason}
                    </div>
                  )}

                  {rev.review_status === 'pending' && (
                    <div className="pt-2">
                      {decidingReviewId === rev.id ? (
                        <div className="p-4 rounded-xl border border-slate-700 bg-slate-950 space-y-3">
                          <label className="block text-xs font-semibold text-slate-200">
                            Mandatory Decision Reason / Conditions *
                          </label>
                          <textarea
                            rows={2}
                            placeholder="State rationale, participant consultation notes, or boundary conditions..."
                            value={decisionReason}
                            onChange={(e) => setDecisionReason(e.target.value)}
                            className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                          />
                          <div className="flex flex-wrap gap-2 justify-end">
                            <button
                              onClick={() => setDecidingReviewId(null)}
                              className="px-3 py-1.5 rounded bg-slate-800 text-slate-400 text-xs font-semibold"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => handleRecordReviewDecision(rev, 'approved')}
                              className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => handleRecordReviewDecision(rev, 'approved_with_conditions')}
                              className="px-3 py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold"
                            >
                              Approve w/ Conditions
                            </button>
                            <button
                              onClick={() => handleRecordReviewDecision(rev, 'rejected')}
                              className="px-3 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold"
                            >
                              Decline Use
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => {
                            setDecidingReviewId(rev.id);
                            setDecisionReason('');
                          }}
                          className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition"
                        >
                          Record Human Decision
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 7: Tasks */}
      {activeTab === 'tasks' && (
        <div className="space-y-4">
          <div>
            <h2 className="text-base font-bold text-white">Actionable Tasks</h2>
            <p className="text-xs text-slate-400">Assigned follow-ups, participant clarification needs, and legal addenda.</p>
          </div>

          {tasks.length === 0 ? (
            <div className="p-8 text-center rounded-xl border border-dashed border-slate-800 text-slate-500 text-xs">
              No outstanding tasks for this project.
            </div>
          ) : (
            <div className="space-y-2">
              {tasks.map((task) => (
                <div
                  key={task.id}
                  className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 flex items-center justify-between hover:bg-slate-900/60 transition"
                >
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => handleTaskStatusToggle(task)}
                      className={`h-5 w-5 rounded border flex items-center justify-center transition ${
                        task.status === 'completed'
                          ? 'bg-emerald-600 border-emerald-500 text-white'
                          : 'border-slate-600 hover:border-emerald-400'
                      }`}
                    >
                      {task.status === 'completed' && <CheckCircle2 className="h-3.5 w-3.5" />}
                    </button>
                    <div>
                      <div className={`text-xs font-semibold ${task.status === 'completed' ? 'line-through text-slate-500' : 'text-slate-100'}`}>
                        {task.title}
                      </div>
                      {task.description && (
                        <div className="text-[11px] text-slate-400 mt-0.5">{task.description}</div>
                      )}
                    </div>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                    task.priority === 'urgent' || task.priority === 'high'
                      ? 'bg-rose-950 text-rose-400 border border-rose-800'
                      : 'bg-slate-800 text-slate-400'
                  }`}>
                    {task.priority}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 8: Care Outreach */}
      {activeTab === 'communications' && (
        <div className="space-y-4">
          <div>
            <h2 className="text-base font-bold text-white">Participant Care Communications</h2>
            <p className="text-xs text-slate-400">
              Draft messages require explicit human approval before they can be sent. The database enforces this via constraint.
            </p>
          </div>

          {comms.length === 0 ? (
            <div className="p-8 text-center rounded-xl border border-dashed border-slate-800 text-slate-500 text-xs">
              No participant care communications recorded.
            </div>
          ) : (
            <div className="space-y-3">
              {comms.map((c) => (
                <div key={c.id} className="p-5 rounded-xl border border-slate-800 bg-slate-900/50 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                    <div>
                      <span className="font-bold text-slate-200 text-xs">{c.subject}</span>
                      <span className="ml-2 px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px] font-mono">
                        Channel: {c.channel}
                      </span>
                    </div>
                    <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-mono ${
                      c.status === 'sent'
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        : c.status === 'approved'
                        ? 'bg-blue-950 text-blue-400 border border-blue-800'
                        : 'bg-amber-950 text-amber-400 border border-amber-800'
                    }`}>
                      {c.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 whitespace-pre-wrap bg-slate-950/70 p-3 rounded border border-slate-800 font-mono text-[11px]">
                    {c.body}
                  </p>

                  {c.status === 'draft' && (
                    <div className="flex justify-end pt-1">
                      <button
                        onClick={() => handleApproveCommunication(c)}
                        className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition"
                      >
                        Approve &amp; Authorize Message
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 9: Timeline */}
      {activeTab === 'timeline' && (
        <div className="space-y-4">
          <div>
            <h2 className="text-base font-bold text-white">Immutable Audit Timeline</h2>
            <p className="text-xs text-slate-400">Cryptographically verifiable, keyset-paginated audit trail of all project events.</p>
          </div>

          {timeline.length === 0 ? (
            <div className="p-8 text-center rounded-xl border border-dashed border-slate-800 text-slate-500 text-xs">
              No audit records retrieved.
            </div>
          ) : (
            <div className="relative pl-6 border-l-2 border-slate-800 space-y-4">
              {timeline.map((entry) => (
                <div key={entry.id} className="relative group">
                  <div className="absolute -left-[31px] top-1 h-3 w-3 rounded-full bg-emerald-500 border-2 border-slate-950" />
                  <div className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/40 text-xs space-y-1">
                    <div className="flex items-center justify-between text-slate-400 text-[11px]">
                      <span className="font-semibold text-emerald-400">{entry.action}</span>
                      <span>{new Date(entry.timestamp).toLocaleString()}</span>
                    </div>
                    <div className="text-slate-300">
                      Entity: <span className="font-mono text-slate-200">{entry.entity_type}</span>{' '}
                      ({entry.entity_id})
                    </div>
                    {entry.reason && (
                      <div className="text-slate-400 italic">Reason: &ldquo;{entry.reason}&rdquo;</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modal: Add Participant */}
      {showAddParticipant && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center space-x-2">
                <Users className="h-5 w-5 text-emerald-400" />
                <span>Register Participant</span>
              </h3>
              <button onClick={() => setShowAddParticipant(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <form onSubmit={handleCreateParticipant} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Display Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Maya Lin"
                  value={newPartName}
                  onChange={(e) => setNewPartName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Preferred Language</label>
                <input
                  type="text"
                  value={newPartLang}
                  onChange={(e) => setNewPartLang(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Preferred Contact Method</label>
                <select
                  value={newPartContact}
                  onChange={(e) => setNewPartContact(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                >
                  <option value="email">Email</option>
                  <option value="phone">Phone / SMS</option>
                  <option value="portal">Participant Portal</option>
                </select>
              </div>
              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowAddParticipant(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newPartName.trim()}
                  className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  Save Participant
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Record Consent */}
      {showAddConsent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-2xl rounded-2xl border border-slate-700 bg-slate-900 p-6 space-y-4 shadow-2xl my-8">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center space-x-2">
                <FileCheck className="h-5 w-5 text-emerald-400" />
                <span>Record Consent Form</span>
              </h3>
              <button onClick={() => setShowAddConsent(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <form onSubmit={handleCreateConsent} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Participant *</label>
                  <select
                    value={consentPartId}
                    onChange={(e) => setConsentPartId(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                  >
                    {participants.map((pt) => (
                      <option key={pt.id} value={pt.id}>{pt.display_name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Source Type *</label>
                  <select
                    value={consentSourceType}
                    onChange={(e) => setConsentSourceType(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                  >
                    <option value="release_form">Signed Release Form</option>
                    <option value="interview">Recorded Interview</option>
                    <option value="verbal_recorded">Verbal Consent</option>
                    <option value="written_correspondence">Written Correspondence</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Agreement Description</label>
                <input
                  type="text"
                  value={consentExplanation}
                  onChange={(e) => setConsentExplanation(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2">
                  Category Agreement Breakdown (15 Canonical Categories)
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-60 overflow-y-auto pr-1">
                  {CANONICAL_CATEGORIES.map((cat) => (
                    <div key={cat} className="p-2 rounded bg-slate-950 border border-slate-800 flex items-center justify-between">
                      <span className="text-[11px] text-slate-300">{cat.replace(/_/g, ' ')}</span>
                      <select
                        value={consentChoices[cat] || 'not_discussed'}
                        onChange={(e) => setConsentChoices({ ...consentChoices, [cat]: e.target.value })}
                        className="text-[11px] px-2 py-1 rounded bg-slate-900 border border-slate-700 text-white"
                      >
                        <option value="agreed">Agreed</option>
                        <option value="declined">Declined</option>
                        <option value="not_discussed">Not Discussed</option>
                        <option value="needs_clarification">Needs Clarification</option>
                      </select>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowAddConsent(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
                >
                  Save Consent Record
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Propose Use */}
      {showAddProposedUse && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center space-x-2">
                <GitCompare className="h-5 w-5 text-emerald-400" />
                <span>Propose Footage / Likeness Use</span>
              </h3>
              <button onClick={() => setShowAddProposedUse(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <form onSubmit={handleCreateProposedUse} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Participant *</label>
                  <select
                    value={usePartId}
                    onChange={(e) => setUsePartId(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                  >
                    {participants.map((pt) => (
                      <option key={pt.id} value={pt.id}>{pt.display_name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Use Type *</label>
                  <select
                    value={useType}
                    onChange={(e) => setUseType(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                  >
                    {CANONICAL_CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>{cat.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Platform / Territory</label>
                <input
                  type="text"
                  value={usePlatform}
                  onChange={(e) => setUsePlatform(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Context Description</label>
                <textarea
                  rows={2}
                  value={useDesc}
                  onChange={(e) => setUseDesc(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowAddProposedUse(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
                >
                  Submit &amp; Run Comparison Engine
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
