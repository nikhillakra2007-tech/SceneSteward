'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import { 
  UserCheck, 
  ShieldCheck, 
  FileCheck, 
  Lock, 
  AlertCircle, 
  CheckCircle2, 
  MessageSquare, 
  ArrowLeft,
  Globe,
  AlertTriangle,
  Send
} from 'lucide-react';
import { 
  api, 
  Participant, 
  ConsentRecord, 
  TimelineEntry,
  CANONICAL_CATEGORIES 
} from '@/lib/api';
import { ChoiceBadge } from '@/components/ConsentBadge';
import { useToast } from '@/components/Toast';

type Language = 'en' | 'hi';

const DICTIONARY: Record<Language, {
  portalBadge: string;
  projectWorkspace: string;
  dignityGuaranteeTitle: string;
  dignityGuaranteeBody: string;
  languageLabel: string;
  contactLabel: string;
  statusLabel: string;
  currentConsentTitle: string;
  versionLabel: string;
  noConsentRecord: string;
  categoriesHeader: string;
  tabQuestion: string;
  tabWithdrawal: string;
  formTitle: string;
  formSubtitle: string;
  categorySelectPlaceholder: string;
  withdrawalWarning: string;
  questionPlaceholder: string;
  withdrawalPlaceholder: string;
  submitButtonQuestion: string;
  submitButtonWithdrawal: string;
  submissionSuccessQuestion: string;
  submissionSuccessWithdrawal: string;
  timelineTitle: string;
  timelineSubtitle: string;
  noTimeline: string;
  categoryNames: Record<string, string>;
}> = {
  en: {
    portalBadge: 'Participant Dignity & Consent Portal',
    projectWorkspace: 'Project Workspace',
    dignityGuaranteeTitle: 'Non-Transitive Consent Invariant',
    dignityGuaranteeBody: 'Under our documentary ethics guarantee: agreement to one use is never agreement to another use. Silence is never agreement.',
    languageLabel: 'Preferred Language',
    contactLabel: 'Contact Method',
    statusLabel: 'Participant Status',
    currentConsentTitle: 'Your Current Consent Record',
    versionLabel: 'Version',
    noConsentRecord: 'No formal consent record logged yet.',
    categoriesHeader: 'Evaluated Consent Categories',
    tabQuestion: 'Ask Question / Clarify',
    tabWithdrawal: 'Formal Consent Withdrawal',
    formTitle: 'Participant Agency & Communication',
    formSubtitle: 'You have the right to ask questions, request clarifications, or withdraw consent for any category before picture lock.',
    categorySelectPlaceholder: 'Select category (optional)',
    withdrawalWarning: 'ATTENTION: Submitting a withdrawal request will immediately notify the production legal team to pause associated footage and contact you.',
    questionPlaceholder: 'e.g., How will my interview be framed in the historical segment?',
    withdrawalPlaceholder: 'e.g., I wish to withdraw my appearance from promotional clips and festival submissions immediately...',
    submitButtonQuestion: 'Submit Inquiry',
    submitButtonWithdrawal: 'Submit Formal Withdrawal',
    submissionSuccessQuestion: 'Thank you. Your clarification request has been securely submitted to the Participant Care team.',
    submissionSuccessWithdrawal: 'Your withdrawal notice has been recorded. The production team has been notified to pause use immediately.',
    timelineTitle: 'Your Accountability Timeline',
    timelineSubtitle: 'Immutable event audit trail of every action concerning your consent records.',
    noTimeline: 'No historical events recorded yet.',
    categoryNames: {
      interview_recording: 'Interview Recording',
      documentary_appearance: 'Documentary Appearance',
      name_identification: 'Name Identification',
      face_identification: 'Face Identification',
      sensitive_personal_details: 'Sensitive Personal Details',
      promotional_clips: 'Promotional Clips & Trailers',
      festival_submissions: 'Festival Submissions',
      ai_transcription: 'AI Transcription',
      voice_cloning: 'Voice Cloning & Synthesis',
      synthetic_likeness: 'Synthetic Likeness & Deepfakes',
      third_party_ai_processing: 'Third-Party AI Processing',
      new_audience: 'New / Wider Audience',
      new_territory: 'New Territory / Global Rights',
      new_platform: 'New Platform (Streaming/Social)',
      new_story_context: 'New Story Context / Re-edit',
    },
  },
  hi: {
    portalBadge: 'प्रतिभागी गरिमा और सहमति पोर्टल',
    projectWorkspace: 'परियोजना कार्यक्षेत्र',
    dignityGuaranteeTitle: 'अहस्तांतरणीय सहमति गारंटी',
    dignityGuaranteeBody: 'हमारी वृत्तचित्र नैतिकता गारंटी के तहत: एक उपयोग के लिए सहमति कभी भी दूसरे उपयोग के लिए सहमति नहीं बनती। चुप्पी कभी सहमति नहीं है।',
    languageLabel: 'पसंदीदा भाषा',
    contactLabel: 'संपर्क माध्यम',
    statusLabel: 'प्रतिभागी स्थिति',
    currentConsentTitle: 'आपका वर्तमान सहमति रिकॉर्ड',
    versionLabel: 'संस्करण',
    noConsentRecord: 'अभी तक कोई औपचारिक सहमति रिकॉर्ड दर्ज नहीं किया गया है।',
    categoriesHeader: 'मूल्यांकित सहमति श्रेणियां',
    tabQuestion: 'प्रश्न पूछें / स्पष्टीकरण',
    tabWithdrawal: 'औपचारिक सहमति वापसी',
    formTitle: 'प्रतिभागी स्वायत्तता और संवाद',
    formSubtitle: 'आपको अंतिम संपादन से पहले किसी भी श्रेणी के बारे में प्रश्न पूछने या अपनी सहमति वापस लेने का पूर्ण अधिकार है।',
    categorySelectPlaceholder: 'श्रेणी चुनें (वैकल्पिक)',
    withdrawalWarning: 'ध्यान दें: सहमति वापसी का अनुरोध सबमिट करने पर उत्पादन टीम को तुरंत आपकी फुटेज का उपयोग रोकने की सूचना दी जाएगी।',
    questionPlaceholder: 'उदा. वृत्तचित्र में मेरे साक्षात्कार का उपयोग किस संदर्भ में किया जा रहा है?',
    withdrawalPlaceholder: 'उदा. मैं प्रचार क्लिप और सोशल मीडिया से अपनी उपस्थिति तुरंत वापस लेना चाहता/चाहती हूँ...',
    submitButtonQuestion: 'पूछताछ भेजें',
    submitButtonWithdrawal: 'औपचारिक वापसी दर्ज करें',
    submissionSuccessQuestion: 'धन्यवाद। आपका अनुरोध प्रतिभागी देखभाल दल को सुरक्षित रूप से भेज दिया गया है।',
    submissionSuccessWithdrawal: 'आपकी वापसी सूचना दर्ज कर ली गई है। उत्पादन दल को उपयोग तुरंत रोकने का निर्देश दिया गया है।',
    timelineTitle: 'जवाबदेही घटनाक्रम',
    timelineSubtitle: 'आपके सहमति रिकॉर्ड से संबंधित प्रत्येक कार्रवाई का अपरिवर्तनीय ऑडिट ट्रेल।',
    noTimeline: 'अभी तक कोई ऐतिहासिक घटना दर्ज नहीं की गई है।',
    categoryNames: {
      interview_recording: 'साक्षात्कार रिकॉर्डिंग',
      documentary_appearance: 'वृत्तचित्र में उपस्थिति',
      name_identification: 'नाम पहचान',
      face_identification: 'चेहरा पहचान',
      sensitive_personal_details: 'संवेदनशील व्यक्तिगत विवरण',
      promotional_clips: 'प्रचार क्लिप और ट्रेलर',
      festival_submissions: 'फिल्म समारोह प्रविष्टियां',
      ai_transcription: 'एआई प्रतिलेखन',
      voice_cloning: 'आवाज क्लोनिंग / संश्लेषण',
      synthetic_likeness: 'सिंथेटिक प्रतिरूप / डीपफेक',
      third_party_ai_processing: 'तृतीय-पक्ष एआई प्रसंस्करण',
      new_audience: 'नए / व्यापक दर्शक',
      new_territory: 'नया क्षेत्र / वैश्विक अधिकार',
      new_platform: 'नया मंच (स्ट्रीमिंग / सोशल मीडिया)',
      new_story_context: 'नया कहानी संदर्भ / पुनर्संपादन',
    },
  },
};

export default function ParticipantPortalPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const participantId = params?.id as string;
  const token = searchParams.get('token');

  const [lang, setLang] = useState<Language>('en');
  const t = DICTIONARY[lang];

  const { success, error: toastError } = useToast();
  const [participant, setParticipant] = useState<Participant | null>(null);
  const [consents, setConsents] = useState<ConsentRecord[]>([]);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [formMode, setFormMode] = useState<'clarification' | 'withdrawal'>('clarification');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [messageText, setMessageText] = useState('');
  const [submittedMessage, setSubmittedMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      if (!participantId) return;
      setLoading(true);
      setError(null);
      try {
        if (token) {
          const pt = await api.getParticipantPortalAccess(participantId, token);
          setParticipant(pt);
          if (pt.preferred_language?.toLowerCase().includes('hi') || pt.preferred_language?.toLowerCase().includes('hindi')) {
            setLang('hi');
          }
          const cList = await api.getParticipantConsents(participantId, token);
          setConsents(cList.items || []);
          const tl = await api.getParticipantTimeline(participantId, token);
          setTimeline(tl.items || []);
        } else {
          const pt = await api.getParticipant(participantId);
          setParticipant(pt);
          const cList = await api.getParticipantConsents(participantId);
          setConsents(cList.items || []);
          const tl = await api.getParticipantTimeline(participantId);
          setTimeline(tl.items || []);
        }
      } catch (err: any) {
        setError(err.message || 'Error loading participant record');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [participantId, token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!messageText.trim()) {
      setFormError('Please enter your question or notice before submitting.');
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      const res = await api.submitClarificationRequest(
        participantId,
        {
          concern: messageText.trim(),
          category: selectedCategory || undefined,
          request_type: formMode,
        },
        token || undefined,
      );
      const msg = res.message || (formMode === 'withdrawal' ? t.submissionSuccessWithdrawal : t.submissionSuccessQuestion);
      setSubmittedMessage(msg);
      success(msg);
      setMessageText('');
    } catch (err: any) {
      setFormError(err.message || 'Submission failed');
      toastError(err.message || 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  const getChoiceForCategory = (choices: any, cat: string) => {
    if (Array.isArray(choices)) {
      const found = choices.find((ch: any) => ch.category === cat);
      if (found) return found.choice;
    } else if (choices && typeof choices === 'object') {
      const data = choices[cat];
      return typeof data === 'object' && data ? data.choice : (data || 'not_discussed');
    }
    return 'not_discussed';
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
    <div className="max-w-4xl mx-auto space-y-8 px-4 sm:px-6">
      {/* Top Header & Language Selector */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-emerald-950/80 border border-emerald-800 text-emerald-400 text-xs font-semibold">
          <ShieldCheck className="h-4 w-4" />
          <span>{t.portalBadge}</span>
        </div>

        <div className="flex items-center space-x-3">
          {/* Language Switcher */}
          <div className="flex items-center space-x-1 bg-slate-900 border border-slate-800 rounded-lg p-1 text-xs">
            <Globe className="h-3.5 w-3.5 text-slate-400 ml-1.5 mr-0.5" />
            <button
              type="button"
              onClick={() => setLang('en')}
              className={`px-2 py-0.5 rounded font-medium transition ${lang === 'en' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'}`}
            >
              English
            </button>
            <button
              type="button"
              onClick={() => setLang('hi')}
              className={`px-2 py-0.5 rounded font-medium transition ${lang === 'hi' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'}`}
            >
              हिन्दी
            </button>
          </div>

          <Link
            href={`/projects/${participant.project_id}`}
            className="text-xs text-slate-400 hover:text-emerald-400 inline-flex items-center space-x-1"
          >
            <ArrowLeft className="h-3 w-3" />
            <span>{t.projectWorkspace}</span>
          </Link>
        </div>
      </div>

      {/* Participant Profile Banner */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-6 sm:p-8 space-y-4">
        <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight text-slate-50">{participant.display_name}</h1>
        
        {/* Core Dignity Guarantee */}
        <div className="p-4 rounded-xl border border-emerald-800/60 bg-emerald-950/40 text-emerald-300 text-xs leading-relaxed space-y-1">
          <p className="font-semibold text-emerald-200">{t.dignityGuaranteeTitle}</p>
          <p>{t.dignityGuaranteeBody}</p>
        </div>

        <div className="pt-2 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-400">
          <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
            <span className="text-slate-500 block text-[11px]">{t.languageLabel}</span>
            <span className="text-slate-200 font-semibold">{participant.preferred_language || 'Standard'}</span>
          </div>
          <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
            <span className="text-slate-500 block text-[11px]">{t.contactLabel}</span>
            <span className="text-slate-200 font-semibold">{participant.preferred_contact_method || 'Verified on file'}</span>
          </div>
          <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
            <span className="text-slate-500 block text-[11px]">{t.statusLabel}</span>
            <span className="text-emerald-400 font-semibold font-mono">{participant.participant_status || participant.status}</span>
          </div>
        </div>
      </div>

      {/* Consent Record Breakdown across 15 Canonical Categories */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 flex-wrap gap-2">
          <div>
            <h2 className="font-display text-lg font-semibold text-slate-50 flex items-center space-x-2">
              <FileCheck className="h-5 w-5 text-emerald-400" />
              <span>{t.currentConsentTitle}</span>
            </h2>
            <p className="text-xs text-slate-400">
              {latestConsent 
                ? `${t.versionLabel} ${latestConsent.version_number || latestConsent.version} (${latestConsent.source_type})` 
                : t.noConsentRecord}
            </p>
          </div>
          {latestConsent && (
            <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">
              {latestConsent.record_status || latestConsent.status}
            </span>
          )}
        </div>

        {latestConsent ? (
          <div className="space-y-4">
            {latestConsent.explanation && (
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 italic">
                &ldquo;{latestConsent.explanation}&rdquo;
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {CANONICAL_CATEGORIES.map((cat) => {
                const choiceVal = getChoiceForCategory(latestConsent.choices, cat);
                const localizedName = t.categoryNames[cat] || cat.replace(/_/g, ' ');
                return (
                  <div key={cat} className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/90 flex flex-col justify-between space-y-2 hover:border-slate-700 transition">
                    <span className="text-xs font-semibold text-slate-200">
                      {localizedName}
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
          <p className="text-xs text-slate-500 italic">{t.noConsentRecord}</p>
        )}
      </div>

      {/* Participant Agency, Clarification & Withdrawal Form */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 flex-wrap gap-2">
          <div>
            <h2 className="font-display text-lg font-semibold text-slate-50 flex items-center space-x-2">
              <MessageSquare className="h-5 w-5 text-emerald-400" />
              <span>{t.formTitle}</span>
            </h2>
            <p className="text-xs text-slate-400">{t.formSubtitle}</p>
          </div>

          {/* Form Mode Selector */}
          <div className="flex rounded-lg bg-slate-950 border border-slate-800 p-0.5 text-xs">
            <button
              type="button"
              onClick={() => { setFormMode('clarification'); setSubmittedMessage(null); }}
              className={`px-3 py-1 rounded font-medium transition ${formMode === 'clarification' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'}`}
            >
              {t.tabQuestion}
            </button>
            <button
              type="button"
              onClick={() => { setFormMode('withdrawal'); setSubmittedMessage(null); }}
              className={`px-3 py-1 rounded font-medium transition ${formMode === 'withdrawal' ? 'bg-amber-600 text-white' : 'text-slate-400 hover:text-white'}`}
            >
              {t.tabWithdrawal}
            </button>
          </div>
        </div>

        {formMode === 'withdrawal' && (
          <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-800/80 text-amber-200 text-xs flex items-start space-x-2.5">
            <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <p>{t.withdrawalWarning}</p>
          </div>
        )}

        {submittedMessage ? (
          <div className="p-4 rounded-xl border border-emerald-800/80 bg-emerald-950/30 text-emerald-300 text-xs flex items-center space-x-2">
            <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
            <span>{submittedMessage}</span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {formError && (
              <div className="p-3 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-300 text-xs flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                {t.categoriesHeader}
              </label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-emerald-500"
              >
                <option value="">{t.categorySelectPlaceholder}</option>
                {CANONICAL_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {t.categoryNames[cat] || cat.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                {formMode === 'withdrawal' ? t.tabWithdrawal : t.tabQuestion}
              </label>
              <textarea
                rows={4}
                placeholder={formMode === 'withdrawal' ? t.withdrawalPlaceholder : t.questionPlaceholder}
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={!messageText.trim() || submitting}
                className={`px-5 py-2.5 rounded-lg text-white text-xs font-semibold flex items-center space-x-1.5 disabled:opacity-50 transition ${
                  formMode === 'withdrawal'
                    ? 'bg-amber-600 hover:bg-amber-500'
                    : 'bg-emerald-600 hover:bg-emerald-500'
                }`}
              >
                <Send className="h-3.5 w-3.5" />
                <span>
                  {submitting
                    ? 'Submitting...'
                    : formMode === 'withdrawal'
                    ? t.submitButtonWithdrawal
                    : t.submitButtonQuestion}
                </span>
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Personal Audit Timeline */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
        <h2 className="font-display text-lg font-semibold text-slate-50 flex items-center space-x-2">
          <Lock className="h-5 w-5 text-emerald-400" />
          <span>{t.timelineTitle}</span>
        </h2>
        <p className="text-xs text-slate-400">{t.timelineSubtitle}</p>

        {timeline.length === 0 ? (
          <p className="text-xs text-slate-500 italic">{t.noTimeline}</p>
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
