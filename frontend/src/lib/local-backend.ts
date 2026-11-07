/**
 * SceneSteward local workspace engine.
 *
 * The hosted site runs entirely in the browser: every API call the frontend
 * makes is served here from a localStorage-backed store. No network requests,
 * no external services. Data never leaves the visitor's device.
 *
 * The consent-comparison rules are a TypeScript port of the deterministic
 * engine in backend/app/services/consent_comparison.py (ENGINE_VERSION 1.0.0).
 */

export const ENGINE_VERSION = '1.0.0';
const STORE_KEY = 'scenesteward_local_db_v1';

// ---------------------------------------------------------------------------
// Store shape
// ---------------------------------------------------------------------------

export interface LocalUser {
  id: string;
  email: string;
  full_name: string;
  auth_provider: string;
  account_status: string;
  last_login_at: string | null;
  role: string;
}

export interface LocalProject {
  id: string;
  title: string;
  description: string | null;
  purpose: string | null;
  themes: string[];
  intended_audiences: string[];
  distribution_plan: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface LocalParticipant {
  id: string;
  project_id: string;
  user_id: string | null;
  display_name: string;
  preferred_language: string;
  preferred_contact_method: string;
  participant_status: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface LocalChoice {
  id: string;
  category: string;
  choice: string;
  explanation: string | null;
  evidence_reference: string | null;
  source_type: string;
  confidence_if_extracted: number | null;
  confirmed_by: string | null;
  confirmed_at: string | null;
  created_at: string;
}

export interface LocalConsentRecord {
  id: string;
  participant_id: string;
  project_id: string;
  source_type: string;
  source_document_id: string | null;
  record_status: string;
  explanation: string | null;
  choices: LocalChoice[];
  confirmed_by_participant_at: string | null;
  confirmed_at: string | null;
  version_number: number;
  created_at: string;
}

export interface LocalDocument {
  id: string;
  project_id: string;
  participant_id: string | null;
  storage_key: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  scan_status: string;
  extracted_text: string | null;
  created_at: string;
}

export interface LocalProposedUse {
  id: string;
  project_id: string;
  participant_id: string;
  story_element_id: string | null;
  use_type: string;
  platform: string | null;
  audience: string | null;
  purpose: string | null;
  territory: string | null;
  context_description: string | null;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface LocalAnalysis {
  id: string;
  proposed_use_id: string;
  outcome: string;
  findings: any[];
  created_at: string;
}

export interface LocalReview {
  id: string;
  project_id: string;
  proposed_use_id: string;
  review_status: string;
  human_decision: string | null;
  decision_reason: string | null;
  decided_by: string | null;
  decided_at: string | null;
  uncertainty: string | null;
  version: number;
  created_at: string;
}

export interface LocalTask {
  id: string;
  project_id: string;
  participant_id: string | null;
  task_type: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  owner_user_id: string | null;
  due_date: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface LocalCommunication {
  id: string;
  project_id: string;
  participant_id: string;
  communication_type: string;
  subject: string | null;
  draft_content: string | null;
  communication_status: string;
  created_by: string | null;
  approved_by: string | null;
  approved_at: string | null;
  sent_at: string | null;
  version: number;
  created_at: string;
}

export interface LocalAgentRun {
  id: string;
  proposed_use_id: string;
  agent_name: string;
  execution_status: string;
  output_data: any;
  created_at: string;
}

export interface LocalTimelineEntry {
  id: string;
  project_id: string | null;
  participant_id: string | null;
  timestamp: string;
  actor_type: string;
  action: string;
  entity_type: string;
  entity_id: string;
  reason: string | null;
  correlation_id: string | null;
}

interface Store {
  users: LocalUser[];
  sessions: Record<string, string>; // token -> userId
  projects: LocalProject[];
  participants: LocalParticipant[];
  consentRecords: LocalConsentRecord[];
  documents: LocalDocument[];
  proposedUses: LocalProposedUse[];
  analyses: LocalAnalysis[];
  reviews: LocalReview[];
  tasks: LocalTask[];
  communications: LocalCommunication[];
  agentRuns: LocalAgentRun[];
  timeline: LocalTimelineEntry[];
  participantTokens: Record<string, { participant_id: string; expires_at: string }>;
}

// ---------------------------------------------------------------------------
// Store helpers
// ---------------------------------------------------------------------------

function uuid(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

function nowIso(): string {
  return new Date().toISOString();
}

function daysAgo(n: number, hour = 10): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  d.setHours(hour, 12, 0, 0);
  return d.toISOString();
}

let cache: Store | null = null;

function loadStore(): Store {
  if (cache) return cache;
  if (typeof window === 'undefined') {
    return emptyStore();
  }
  try {
    const raw = window.localStorage.getItem(STORE_KEY);
    if (raw) {
      cache = JSON.parse(raw) as Store;
      return cache;
    }
  } catch {
    // corrupted store -> reseed
  }
  cache = seedStore();
  persist();
  return cache;
}

function persist() {
  if (typeof window === 'undefined' || !cache) return;
  try {
    window.localStorage.setItem(STORE_KEY, JSON.stringify(cache));
  } catch {
    // storage full or unavailable; the in-memory copy keeps the session working
  }
}

function emptyStore(): Store {
  return {
    users: [], sessions: {}, projects: [], participants: [], consentRecords: [],
    documents: [], proposedUses: [], analyses: [], reviews: [], tasks: [],
    communications: [], agentRuns: [], timeline: [], participantTokens: {},
  };
}

export class LocalApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function record(
  s: Store,
  e: {
    project_id?: string | null;
    participant_id?: string | null;
    actor_type?: string;
    action: string;
    entity_type: string;
    entity_id: string;
    reason?: string | null;
    timestamp?: string;
  },
) {
  s.timeline.push({
    id: uuid(),
    project_id: e.project_id ?? null,
    participant_id: e.participant_id ?? null,
    timestamp: e.timestamp ?? nowIso(),
    actor_type: e.actor_type ?? 'user',
    action: e.action,
    entity_type: e.entity_type,
    entity_id: e.entity_id,
    reason: e.reason ?? null,
    correlation_id: null,
  });
}

// ---------------------------------------------------------------------------
// Seed data: a fictional documentary workspace so the product is explorable
// the moment someone signs in. All people and films are invented.
// ---------------------------------------------------------------------------

function seedStore(): Store {
  const s = emptyStore();

  const project: LocalProject = {
    id: uuid(),
    title: 'The Weight of Water',
    description:
      'A feature documentary following a coastal fishing family through one monsoon season, and the choices they face as the sea changes around them.',
    purpose: 'Festival premiere followed by educational screenings',
    themes: ['environment', 'family', 'livelihood'],
    intended_audiences: ['festival audiences', 'educational institutions'],
    distribution_plan: 'Festival circuit first; online release discussed separately with participants.',
    status: 'active',
    created_at: daysAgo(12),
    updated_at: daysAgo(2),
  };
  s.projects.push(project);

  const maria: LocalParticipant = {
    id: uuid(), project_id: project.id, user_id: null,
    display_name: 'Maria Alvarez', preferred_language: 'English',
    preferred_contact_method: 'email', participant_status: 'active',
    notes: 'Fisher and family matriarch. Comfortable on camera; asked that her voice never be recreated by software.',
    created_at: daysAgo(11), updated_at: daysAgo(9),
  };
  const david: LocalParticipant = {
    id: uuid(), project_id: project.id, user_id: null,
    display_name: 'David Okafor', preferred_language: 'English',
    preferred_contact_method: 'phone', participant_status: 'active',
    notes: 'Marine biologist interviewed for context. Happy with promotional clips; private about family details.',
    created_at: daysAgo(10), updated_at: daysAgo(6),
  };
  const priya: LocalParticipant = {
    id: uuid(), project_id: project.id, user_id: null,
    display_name: 'Priya Sharma', preferred_language: 'Hindi',
    preferred_contact_method: 'email', participant_status: 'active',
    notes: 'Community organiser. Release form sent; confirmation still pending.',
    created_at: daysAgo(4), updated_at: daysAgo(1),
  };
  s.participants.push(maria, david, priya);

  function makeChoices(
    recordId: string,
    source: string,
    when: string,
    map: Record<string, { choice: string; explanation?: string }>,
  ): LocalChoice[] {
    return Object.entries(map).map(([category, v]) => ({
      id: uuid(), category, choice: v.choice,
      explanation: v.explanation ?? null, evidence_reference: null,
      source_type: source, confidence_if_extracted: null,
      confirmed_by: null, confirmed_at: when, created_at: when,
    }));
  }

  const mariaRecordId = uuid();
  const mariaRecord: LocalConsentRecord = {
    id: mariaRecordId, participant_id: maria.id, project_id: project.id,
    source_type: 'release_form', source_document_id: null,
    record_status: 'confirmed',
    explanation: 'Signed release form discussed in person on day one of filming.',
    choices: makeChoices(mariaRecordId, 'release_form', daysAgo(9), {
      interview_recording: { choice: 'agreed' },
      documentary_appearance: { choice: 'agreed' },
      name_identification: { choice: 'agreed' },
      face_identification: { choice: 'agreed' },
      festival_submissions: { choice: 'agreed', explanation: 'Happy for the film to play at festivals.' },
      new_audience: { choice: 'agreed' },
      voice_cloning: { choice: 'declined', explanation: 'Do not recreate my voice with software.' },
      synthetic_likeness: { choice: 'declined' },
      promotional_clips: { choice: 'not_discussed' },
      new_platform: { choice: 'not_discussed' },
      new_territory: { choice: 'not_discussed' },
      ai_transcription: { choice: 'explained', explanation: 'Explained how transcription works; no decision yet.' },
      sensitive_personal_details: { choice: 'needs_clarification' },
      third_party_ai_processing: { choice: 'awaiting_confirmation' },
      new_story_context: { choice: 'not_discussed' },
    }),
    confirmed_by_participant_at: daysAgo(9), confirmed_at: daysAgo(9),
    version_number: 1, created_at: daysAgo(9),
  };

  const davidRecordId = uuid();
  const davidRecord: LocalConsentRecord = {
    id: davidRecordId, participant_id: david.id, project_id: project.id,
    source_type: 'interview', source_document_id: null,
    record_status: 'confirmed',
    explanation: 'Recorded conversation after his interview; choices read back and confirmed.',
    choices: makeChoices(davidRecordId, 'interview', daysAgo(6), {
      interview_recording: { choice: 'agreed' },
      documentary_appearance: { choice: 'agreed' },
      name_identification: { choice: 'agreed' },
      face_identification: { choice: 'agreed' },
      promotional_clips: { choice: 'agreed', explanation: 'Fine with short clips for promotion.' },
      new_platform: { choice: 'agreed' },
      sensitive_personal_details: { choice: 'declined', explanation: 'Keep family details out of the film.' },
      festival_submissions: { choice: 'not_discussed' },
      new_audience: { choice: 'not_discussed' },
      new_territory: { choice: 'not_discussed' },
      ai_transcription: { choice: 'not_discussed' },
      voice_cloning: { choice: 'not_discussed' },
      synthetic_likeness: { choice: 'not_discussed' },
      third_party_ai_processing: { choice: 'not_discussed' },
      new_story_context: { choice: 'not_discussed' },
    }),
    confirmed_by_participant_at: daysAgo(6), confirmed_at: daysAgo(6),
    version_number: 1, created_at: daysAgo(6),
  };

  const priyaRecordId = uuid();
  const priyaRecord: LocalConsentRecord = {
    id: priyaRecordId, participant_id: priya.id, project_id: project.id,
    source_type: 'release_form', source_document_id: null,
    record_status: 'awaiting_confirmation',
    explanation: 'Release form drafted from the location conversation; sent for her review.',
    choices: makeChoices(priyaRecordId, 'release_form', daysAgo(1), {
      interview_recording: { choice: 'agreed' },
      documentary_appearance: { choice: 'awaiting_confirmation' },
      name_identification: { choice: 'awaiting_confirmation' },
      face_identification: { choice: 'awaiting_confirmation' },
      festival_submissions: { choice: 'not_discussed' },
      promotional_clips: { choice: 'not_discussed' },
      new_audience: { choice: 'not_discussed' },
      new_platform: { choice: 'not_discussed' },
      new_territory: { choice: 'not_discussed' },
      ai_transcription: { choice: 'not_discussed' },
      voice_cloning: { choice: 'not_discussed' },
      synthetic_likeness: { choice: 'not_discussed' },
      sensitive_personal_details: { choice: 'not_discussed' },
      third_party_ai_processing: { choice: 'not_discussed' },
      new_story_context: { choice: 'not_discussed' },
    }),
    confirmed_by_participant_at: null, confirmed_at: null,
    version_number: 1, created_at: daysAgo(1),
  };
  s.consentRecords.push(mariaRecord, davidRecord, priyaRecord);

  s.documents.push(
    {
      id: uuid(), project_id: project.id, participant_id: maria.id,
      storage_key: 'seed/maria-release.pdf', original_filename: 'maria-alvarez-release-form.pdf',
      mime_type: 'application/pdf', file_size: 248_112, scan_status: 'clean',
      extracted_text:
        'Release form - Maria Alvarez. The participant agrees to interview recording, appearance in the documentary, use of her name and face, and festival submissions. The participant does not consent to voice cloning or synthetic likeness.',
      created_at: daysAgo(9),
    },
    {
      id: uuid(), project_id: project.id, participant_id: david.id,
      storage_key: 'seed/david-consent-notes.txt', original_filename: 'david-okafor-consent-notes.txt',
      mime_type: 'text/plain', file_size: 1_204, scan_status: 'clean',
      extracted_text:
        'Consent notes - David Okafor. Agreed: interview recording, documentary appearance, name, face, promotional clips, new platforms. Declined: sensitive personal details.',
      created_at: daysAgo(6),
    },
  );

  record(s, { project_id: project.id, actor_type: 'system', action: 'project.created', entity_type: 'project', entity_id: project.id, timestamp: daysAgo(12) });
  for (const [p, when] of [[maria, daysAgo(11)], [david, daysAgo(10)], [priya, daysAgo(4)]] as const) {
    record(s, { project_id: project.id, participant_id: p.id, actor_type: 'user', action: 'participant.created', entity_type: 'participant', entity_id: p.id, timestamp: when });
  }
  record(s, { project_id: project.id, participant_id: maria.id, actor_type: 'user', action: 'consent_record.confirmed', entity_type: 'consent_record', entity_id: mariaRecord.id, timestamp: daysAgo(9) });
  record(s, { project_id: project.id, participant_id: david.id, actor_type: 'user', action: 'consent_record.confirmed', entity_type: 'consent_record', entity_id: davidRecord.id, timestamp: daysAgo(6) });
  record(s, { project_id: project.id, participant_id: priya.id, actor_type: 'user', action: 'consent_record.created', entity_type: 'consent_record', entity_id: priyaRecord.id, timestamp: daysAgo(1) });

  // Seeded proposed uses with completed analyses, reviews and tasks.
  const mkUse = (participantId: string, useType: string, platform: string, desc: string, when: string): LocalProposedUse => ({
    id: uuid(), project_id: project.id, participant_id: participantId,
    story_element_id: null, use_type: useType, platform,
    audience: null, purpose: null, territory: null, context_description: desc,
    status: 'submitted', version: 1, created_at: when, updated_at: when,
  });

  const pu1 = mkUse(maria.id, 'festival_submission', 'Documentary film festivals',
    'Submitting the finished film to international documentary festivals.', daysAgo(8));
  s.proposedUses.push(pu1);
  record(s, { project_id: project.id, participant_id: maria.id, actor_type: 'user', action: 'proposed_use.created', entity_type: 'proposed_use', entity_id: pu1.id, timestamp: daysAgo(8) });
  const a1 = runAnalysis(s, pu1, null, daysAgo(8));
  a1.review.human_decision = 'approve';
  a1.review.decision_reason = 'Festivals are exactly what Maria agreed to; the final cut matches the record.';
  a1.review.decided_by = 'Olivia Director';
  a1.review.decided_at = daysAgo(5);
  a1.review.review_status = 'decided';
  a1.review.version = 2;
  pu1.status = 'approved';
  pu1.version += 1;
  pu1.updated_at = daysAgo(5);
  record(s, { project_id: project.id, participant_id: maria.id, actor_type: 'user', action: 'review.decided', entity_type: 'review', entity_id: a1.review.id, reason: 'approve: festivals match the confirmed record', timestamp: daysAgo(5) });
  for (const t of a1.tasks) { t.status = 'done'; t.completed_at = daysAgo(5); }
  record(s, { project_id: project.id, participant_id: maria.id, actor_type: 'user', action: 'task.completed', entity_type: 'task', entity_id: a1.tasks[a1.tasks.length - 1].id, timestamp: daysAgo(5) });

  const pu2 = mkUse(maria.id, 'social_campaign', 'YouTube and Instagram',
    'Two-minute trailer cut for YouTube and a 30-second teaser for Instagram to reach a wider audience.', daysAgo(2));
  s.proposedUses.push(pu2);
  record(s, { project_id: project.id, participant_id: maria.id, actor_type: 'user', action: 'proposed_use.created', entity_type: 'proposed_use', entity_id: pu2.id, timestamp: daysAgo(2) });
  runAnalysis(s, pu2, null, daysAgo(2));

  const pu3 = mkUse(maria.id, 'voice_reconstruction', 'Edit suite',
    'Repair two damaged interview lines using an AI voice reconstruction tool.', daysAgo(1));
  s.proposedUses.push(pu3);
  record(s, { project_id: project.id, participant_id: maria.id, actor_type: 'user', action: 'proposed_use.created', entity_type: 'proposed_use', entity_id: pu3.id, timestamp: daysAgo(1) });
  runAnalysis(s, pu3, null, daysAgo(1));

  return s;
}

// ---------------------------------------------------------------------------
// Consent comparison engine (port of backend consent_comparison.py)
// ---------------------------------------------------------------------------

const NOT_AGREED = new Set(['not_discussed', 'needs_clarification', 'awaiting_confirmation', 'explained']);

const USE_TYPE_MAP: Record<string, string[]> = {
  interview_excerpt_promotion: ['promotional_clips', 'interview_recording', 'new_audience'],
  promotional_trailer: ['promotional_clips'],
  promotional_clip: ['promotional_clips'],
  promo_clip: ['promotional_clips'],
  festival_submission: ['festival_submissions', 'new_audience', 'new_territory'],
  festival_entry: ['festival_submissions', 'new_audience'],
  voice_reconstruction: ['voice_cloning', 'third_party_ai_processing'],
  voice_cloning: ['voice_cloning'],
  synthetic_likeness: ['synthetic_likeness'],
  ai_transcription: ['ai_transcription', 'third_party_ai_processing'],
  third_party_ai: ['third_party_ai_processing'],
  theatrical_release: ['new_audience', 'new_territory', 'new_platform'],
  broadcast: ['new_audience', 'new_platform', 'new_territory'],
  streaming_release: ['new_platform', 'new_audience', 'new_territory'],
  social_campaign: ['promotional_clips', 'new_platform', 'new_audience'],
  documentary_screening: ['documentary_appearance', 'new_audience', 'festival_submissions'],
  interview: ['interview_recording'],
  name_release: ['name_identification'],
};

const KEYWORD_RULES: Array<[RegExp, string]> = [
  [/\b(trailer|promo|advert|marketing|campaign)\w*\b/i, 'promotional_clips'],
  [/\bfestival\w*\b/i, 'festival_submissions'],
  [/\bvoice[\s-]?(clon|reconstruct|synth|generat)\w*\b/i, 'voice_cloning'],
  [/\b(synthetic|deepfake|face[\s-]?swap|likeness alteration|ai[\s-]?generat\w* (voice|face|image))\w*\b/i, 'synthetic_likeness'],
  [/\b(transcri|speech[\s-]?to[\s-]?text)\w*\b/i, 'ai_transcription'],
  [/\b(third[\s-]?party ai|external ai|ai processing|ai vendor)\b/i, 'third_party_ai_processing'],
  [/\bname\b/i, 'name_identification'],
  [/\b(face|identifiable|recogni[sz]able)\w*\b/i, 'face_identification'],
  [/\bsensitive\b/i, 'sensitive_personal_details'],
  [/\b(interview|conversation)\w*\b/i, 'interview_recording'],
  [/(\b(wider|general|larger|mass)\b.{0,30}\baudience\b|\bnew audience\b)/i, 'new_audience'],
  [/\b(international|worldwide|global|europe|north america|territory|territories)\b/i, 'new_territory'],
  [/\b(youtube|tiktok|instagram|facebook|x\.com|twitter|streaming|netflix|vimeo|social media|podcast)\b/i, 'new_platform'],
  [/\b(re-?edit|reframe|recontextual|out of context|new context|additional context|montaged?)\b/i, 'new_story_context'],
  [/\b(documentary appearance|appears? in the film|on[\s-]?camera)\b/i, 'documentary_appearance'],
];

interface NormalizedUse {
  relevant: string[];
  matched: Record<string, string[]>;
}

function normalizeProposedUse(use: {
  use_type?: string | null; platform?: string | null; audience?: string | null;
  purpose?: string | null; territory?: string | null; context_description?: string | null;
}): NormalizedUse {
  const relevant = new Set<string>();
  const matched: Record<string, string[]> = {};
  const key = (use.use_type || '').trim().toLowerCase().replace(/[\s-]+/g, '_');
  for (const cat of USE_TYPE_MAP[key] || []) {
    relevant.add(cat);
    (matched[cat] = matched[cat] || []).push(`use_type:${use.use_type}`);
  }
  const blob = [use.use_type, use.platform, use.audience, use.purpose, use.territory, use.context_description]
    .map((x) => x || '').join(' \n ').toLowerCase();
  for (const [pattern, category] of KEYWORD_RULES) {
    const hits = Array.from(blob.matchAll(new RegExp(pattern.source, pattern.flags.includes('g') ? pattern.flags : pattern.flags + 'g'))).map((m) => m[0]);
    if (hits.length) {
      relevant.add(category);
      (matched[category] = matched[category] || []).push(...hits.slice(0, 3).map((h) => `keyword:${h}`));
    }
  }
  if (blob.includes('sensitive') && (relevant.has('promotional_clips') || relevant.has('festival_submissions'))) {
    relevant.add('sensitive_personal_details');
    (matched['sensitive_personal_details'] = matched['sensitive_personal_details'] || []).push('keyword:sensitive+promotion');
  }
  return { relevant: Array.from(relevant).sort(), matched };
}

interface ComparisonResult {
  outcome: string;
  findings: any[];
  matched_consent_record_ids: string[];
}

function compareWithConfirmedRecord(
  latest: LocalConsentRecord | null,
  history: LocalConsentRecord[],
  normalized: NormalizedUse,
): ComparisonResult {
  const findings: any[] = [];
  if (!normalized.relevant.length) {
    return {
      outcome: 'UNRESOLVED',
      findings: [{
        category: null,
        finding: 'Could not determine which consent categories apply to this proposed use.',
        choice: null, source_references: [], confidence: 'low',
        uncertainty: 'use_type and context provide no recognisable category signals',
      }],
      matched_consent_record_ids: [],
    };
  }

  const choices: Record<string, LocalChoice> = {};
  if (latest) for (const c of latest.choices) choices[c.category] = c;
  const matchedIds = [
    ...(latest ? [latest.id] : []),
    ...history.filter((r) => !latest || r.id !== latest.id).map((r) => r.id),
  ];
  const confirmedChain = [
    ...(latest ? [latest] : []),
    ...history.filter((r) => !latest || r.id !== latest.id),
  ].sort((a, b) => a.version_number - b.version_number);

  const declined: string[] = [];
  const conflicts: string[] = [];
  const unsettled: string[] = [];

  for (const category of normalized.relevant) {
    const recorded = confirmedChain
      .map((r) => ({ version: r.version_number, choice: r.choices.find((c) => c.category === category) }))
      .filter((x) => x.choice);
    const distinct = new Set(recorded.map((x) => x.choice!.choice));
    if (distinct.size > 1 && recorded.some((x) => x.choice!.choice === 'agreed') && recorded.some((x) => x.choice!.choice === 'declined')) {
      conflicts.push(category);
    }

    const row = choices[category];
    if (!row) {
      findings.push({
        category,
        finding: 'No confirmed participant choice was found for this category.',
        choice: null, source_references: [], confidence: 'high',
        uncertainty: 'The available confirmed record does not address this use',
      });
      unsettled.push(category);
      continue;
    }
    const ref = latest ? `consent_record:${latest.id}#choice:${row.id}` : null;
    const evidence = [ref, row.evidence_reference].filter(Boolean);
    if (row.choice === 'declined') {
      declined.push(category);
      findings.push({
        category,
        finding: 'The participant has EXPLICITLY DECLINED this category in the confirmed record.',
        choice: 'declined', source_references: evidence, confidence: 'high', uncertainty: null,
      });
    } else if (row.choice === 'agreed') {
      findings.push({
        category,
        finding: 'The latest confirmed record shows explicit agreement for this category.',
        choice: 'agreed', source_references: evidence, confidence: 'high', uncertainty: null,
      });
    } else {
      unsettled.push(category);
      const label: Record<string, string> = {
        not_discussed: 'Not discussed with the participant',
        needs_clarification: 'Participant asked for clarification; no agreement recorded',
        awaiting_confirmation: 'Awaiting participant confirmation',
        explained: 'Explained to the participant; no agreement recorded',
      };
      findings.push({
        category,
        finding: `${label[row.choice] || row.choice}. This is NOT agreement.`,
        choice: row.choice, source_references: evidence, confidence: 'high',
        uncertainty: 'A recorded conversation exists but contains no consent for this use',
      });
    }
  }

  let outcome: string;
  if (declined.length) {
    outcome = 'PARTICIPANT_DECLINED';
  } else if (conflicts.length) {
    outcome = 'HUMAN_REVIEW_REQUIRED';
    for (const category of conflicts) {
      findings.push({
        category,
        finding: 'Confirmed versions disagree on this category; human review must reconcile them.',
        choice: null,
        source_references: [`consent_record_versions:${confirmedChain.map((r) => r.version_number).join(',')}`],
        confidence: 'medium',
        uncertainty: 'Deterministic reconciliation is not possible from the stored evidence',
      });
    }
  } else if (unsettled.length) {
    outcome = 'NEEDS_DISCUSSION';
  } else {
    outcome = 'RECORDED_CHOICE_MATCH';
  }
  return { outcome, findings, matched_consent_record_ids: matchedIds };
}

// ---------------------------------------------------------------------------
// Advisory agents (deterministic, mirror backend offline implementations)
// ---------------------------------------------------------------------------

const PIPELINE_ORDER = [
  'consent_analyst',
  'story_change_analyst',
  'participant_advocate',
  'ethics_reviewer',
  'production_coordinator',
];

function agentOutput(
  agent: string,
  projectId: string,
  participantId: string,
  useId: string,
  result: string,
  findings: any[],
  recommended: string[],
) {
  return {
    agent,
    run_id: uuid(),
    project_id: projectId,
    participant_id: participantId,
    proposed_use_id: useId,
    result,
    findings,
    recommended_actions: recommended,
    requires_human_review: true,
  };
}

function runAgents(
  s: Store,
  use: LocalProposedUse,
  participant: LocalParticipant,
  latest: LocalConsentRecord | null,
  engineFindings: any[],
  engineOutcome: string,
  timestamp?: string,
): LocalAgentRun[] {
  const buckets = { declined: [] as any[], unsettled: [] as any[], agreed: [] as any[] };
  for (const f of engineFindings) {
    if (f.choice === 'declined') buckets.declined.push(f);
    else if (f.choice === 'agreed') buckets.agreed.push(f);
    else buckets.unsettled.push(f);
  }
  const runs: LocalAgentRun[] = [];
  const mk = (agent: string, output: any) => {
    const run: LocalAgentRun = {
      id: uuid(), proposed_use_id: use.id, agent_name: agent,
      execution_status: 'succeeded', output_data: output,
      created_at: timestamp ?? nowIso(),
    };
    runs.push(run);
    s.agentRuns.push(run);
    return run;
  };

  // Consent analyst: restates the confirmed record against the engine findings.
  const caFindings = engineFindings.map((f) => ({
    category: f.category,
    finding: f.finding,
    choice: f.choice ?? null,
    source_references: f.source_references || [],
    confidence: f.confidence || 'high',
    uncertainty: f.uncertainty ?? null,
  }));
  const caRecommended: string[] = [
    'A person must confirm each recorded statement before treating it as a participant decision.',
  ];
  if (buckets.declined.length) {
    caRecommended.push('Do not proceed with declined categories; record the refusal and discuss alternatives with the participant.');
  }
  for (const f of buckets.unsettled.slice(0, 6)) {
    caRecommended.push(`Category not settled: ${f.category} — ask the participant directly.`);
  }
  mk('consent_analyst', agentOutput('consent_analyst', use.project_id, participant.id, use.id, engineOutcome, caFindings, caRecommended));

  // Story change analyst: checks for re-contextualisation signals.
  const scFindings: any[] = [];
  const contextBlob = `${use.use_type} ${use.platform || ''} ${use.context_description || ''}`.toLowerCase();
  if (/re-?edit|reframe|out of context|new context|montage/.test(contextBlob)) {
    scFindings.push({
      category: 'new_story_context',
      finding: 'The proposed use re-contextualises recorded material; treat as a new story context requiring explicit agreement.',
      choice: null, source_references: [], confidence: 'medium',
      uncertainty: 'Re-contextualisation detected from the use description',
    });
  } else {
    scFindings.push({
      category: null,
      finding: 'No story-context change detected between the confirmed record and this proposed use.',
      choice: null, source_references: [], confidence: 'high', uncertainty: null,
    });
  }
  mk('story_change_analyst', agentOutput('story_change_analyst', use.project_id, participant.id, use.id,
    scFindings.length > 1 || scFindings[0].category ? 'NEEDS_DISCUSSION' : engineOutcome,
    scFindings,
    scFindings[0].category
      ? ['Show the participant exactly how the edit changes the meaning of their contribution before any use.']
      : ['No re-contextualisation concerns; keep the recorded context attached to the footage.']));

  // Participant advocate: plain-language summary for the participant.
  const paFindings: any[] = [{
    category: null,
    finding: latest
      ? `${participant.display_name} has a confirmed record (version ${latest.version_number}). This use touches ${buckets.agreed.length} agreed, ${buckets.unsettled.length} unsettled and ${buckets.declined.length} declined categories.`
      : `${participant.display_name} has no confirmed consent record. Nothing may proceed until choices are recorded and confirmed.`,
    choice: null, source_references: [], confidence: 'high', uncertainty: null,
  }];
  mk('participant_advocate', agentOutput('participant_advocate', use.project_id, participant.id, use.id, engineOutcome, paFindings, [
    'Contact the participant in their preferred language before any unsettled use.',
    'Offer a clear way to ask questions or withdraw, and record the outcome as a new consent version.',
  ]));

  // Ethics reviewer: risk framing.
  const risk = buckets.declined.length ? 'HIGH' : buckets.unsettled.length ? 'MEDIUM' : 'LOW';
  mk('ethics_reviewer', agentOutput('ethics_reviewer', use.project_id, participant.id, use.id, engineOutcome, [{
    category: null,
    finding: `Ethical risk assessed as ${risk}. Silence or absence of a record is never consent; a written human rationale is required for any decision.`,
    choice: null, source_references: [], confidence: 'high', uncertainty: null,
  }], [
    risk === 'LOW'
      ? 'Proceed to human review; record the decision rationale in writing.'
      : 'Hold publication until every unsettled or declined category is resolved with the participant.',
  ]));

  // Production coordinator: concrete next steps (drives the draft message).
  const actions: string[] = [];
  for (const f of buckets.unsettled.slice(0, 4)) {
    actions.push(`Discuss "${String(f.category).replace(/_/g, ' ')}" with ${participant.display_name} and record their answer.`);
  }
  for (const f of buckets.declined.slice(0, 4)) {
    actions.push(`Remove "${String(f.category).replace(/_/g, ' ')}" from the plan; ${participant.display_name} declined it.`);
  }
  if (!actions.length) actions.push('Confirm the final cut matches what was agreed, then archive the review.');
  mk('production_coordinator', agentOutput('production_coordinator', use.project_id, participant.id, use.id, engineOutcome, engineFindings, actions));

  return runs;
}

// ---------------------------------------------------------------------------
// Analysis workflow (port of backend proposed_use_analysis.py)
// ---------------------------------------------------------------------------

function latestConfirmed(s: Store, participantId: string): LocalConsentRecord | null {
  const confirmed = s.consentRecords
    .filter((r) => r.participant_id === participantId && r.record_status === 'confirmed')
    .sort((a, b) => b.version_number - a.version_number);
  return confirmed[0] || null;
}

function confirmedHistory(s: Store, participantId: string): LocalConsentRecord[] {
  return s.consentRecords
    .filter((r) => r.participant_id === participantId && r.record_status === 'confirmed')
    .sort((a, b) => b.version_number - a.version_number);
}

function runAnalysis(
  s: Store,
  use: LocalProposedUse,
  actorUserId: string | null,
  timestamp?: string,
): { analysis: LocalAnalysis; review: LocalReview; tasks: LocalTask[] } {
  const participant = s.participants.find((p) => p.id === use.participant_id);
  if (!participant) throw new LocalApiError(404, 'Participant not found');

  const latest = latestConfirmed(s, participant.id);
  const history = confirmedHistory(s, participant.id);
  const normalized = normalizeProposedUse(use);
  const result = compareWithConfirmedRecord(latest, history, normalized);

  const analysis: LocalAnalysis = {
    id: uuid(), proposed_use_id: use.id, outcome: result.outcome,
    findings: result.findings, created_at: timestamp ?? nowIso(),
  };
  s.analyses.push(analysis);

  use.status = 'analysis_complete';
  use.version += 1;
  use.updated_at = timestamp ?? nowIso();

  const missing = Array.from(new Set(result.findings.filter((f) => f.choice == null && f.category).map((f) => f.category as string))).sort();
  const declined = Array.from(new Set(result.findings.filter((f) => f.choice === 'declined' && f.category).map((f) => f.category as string))).sort();
  const evidenceRefs = Array.from(new Set(result.findings.flatMap((f) => f.source_references || []))).sort();

  const review: LocalReview = {
    id: uuid(), project_id: use.project_id, proposed_use_id: use.id,
    review_status: 'pending', human_decision: null, decision_reason: null,
    decided_by: null, decided_at: null,
    uncertainty: result.outcome === 'RECORDED_CHOICE_MATCH' ? null : 'Proposed use exceeds or outruns the confirmed record',
    version: 1, created_at: timestamp ?? nowIso(),
  };
  s.reviews.push(review);

  const createdTasks: LocalTask[] = [];
  const addTask = (t: Partial<LocalTask> & { title: string }) => {
    const task: LocalTask = {
      id: uuid(), project_id: use.project_id, participant_id: participant.id,
      task_type: t.task_type || 'general', title: t.title,
      description: t.description ?? null, status: 'open',
      priority: t.priority || 'normal', owner_user_id: null,
      due_date: null, created_at: timestamp ?? nowIso(), completed_at: null,
    };
    s.tasks.push(task);
    createdTasks.push(task);
  };
  if (missing.length) {
    addTask({
      task_type: 'unresolved_permission', priority: 'high',
      title: `Discuss with participant before use: ${missing.slice(0, 4).join(', ')}`,
      description: 'Confirmed consent does not cover this proposed use. Hold a discussion; record outcomes as a NEW consent version.',
    });
  }
  if (declined.length) {
    addTask({
      task_type: 'unresolved_permission', priority: 'urgent',
      title: `BLOCKED — participant declined: ${declined.slice(0, 4).join(', ')}`,
      description: 'Remove the refused categories from the plan. Do not attempt to re-secure consent for this version.',
    });
  }
  addTask({
    task_type: 'review',
    priority: result.outcome !== 'RECORDED_CHOICE_MATCH' ? 'high' : 'normal',
    title: `Human review required — proposed use ${result.outcome}`,
    description: 'Review the analysis, talk with the participant if needed, then record a formal decision in SceneSteward.',
  });

  record(s, {
    project_id: use.project_id, participant_id: participant.id,
    actor_type: actorUserId ? 'user' : 'system',
    action: 'proposed_use.analysed', entity_type: 'proposed_use', entity_id: use.id,
    reason: `outcome=${result.outcome}`, timestamp,
  });

  runAgents(s, use, participant, latest, result.findings, result.outcome, timestamp);

  // Draft participant communication (never sent automatically).
  const coordinator = s.agentRuns[s.agentRuns.length - 1];
  const actions: string[] = coordinator?.output_data?.recommended_actions || [];
  const draft =
    'Draft for a participant conversation (NOT sent — human approval required before sending):\n\n' +
    'Thank you for sharing your story with us. Before we can go ahead with the planned use, ' +
    'we want to check in with you. The production would like to discuss:\n\n' +
    actions.slice(0, 8).map((a, i) => `  ${i + 1}. ${a}`).join('\n') +
    '\n\nYou may agree, decline, or ask for more information about any of these. ' +
    'Nothing will go ahead without your clear, recorded decision.';
  s.communications.push({
    id: uuid(), project_id: use.project_id, participant_id: participant.id,
    communication_type: 'email',
    subject: 'A conversation about how your story will be used',
    draft_content: draft, communication_status: 'draft',
    created_by: actorUserId, approved_by: null, approved_at: null, sent_at: null,
    version: 1, created_at: timestamp ?? nowIso(),
  });

  return { analysis, review, tasks: createdTasks };
}

// ---------------------------------------------------------------------------
// Request router: serves every /api/v1/* endpoint the frontend calls.
// ---------------------------------------------------------------------------

const ROLE_BY_PRESET: Record<string, string> = {
  'olivia@example.com': 'project_owner',
  'claire@example.com': 'care_lead',
  'marcus@example.com': 'producer',
  'elena@example.com': 'legal_counsel',
};

function userFromToken(s: Store, auth: string | null): LocalUser {
  if (!auth) throw new LocalApiError(401, 'Not authenticated');
  const token = auth.replace(/^Bearer\s+/i, '');
  const userId = s.sessions[token];
  const user = userId ? s.users.find((u) => u.id === userId) : null;
  if (!user) throw new LocalApiError(401, 'Not authenticated');
  return user;
}

function participantTokenOk(s: Store, participantId: string, token: string | null): boolean {
  if (!token) return false;
  const entry = s.participantTokens[token];
  if (!entry || entry.participant_id !== participantId) return false;
  return new Date(entry.expires_at).getTime() > Date.now();
}

function membershipView(s: Store, u: LocalUser) {
  return s.projects.map((p) => ({
    project_id: p.id,
    project_title: p.title,
    role: u.role as any,
    membership_status: 'active',
  }));
}

export async function handleLocalRequest(
  method: string,
  endpoint: string,
  body: any,
  authHeader: string | null,
): Promise<any> {
  const s = loadStore();
  const url = new URL(endpoint, 'https://local.invalid');
  const path = url.pathname.replace(/\/+$/, '') || '/';
  const q = (k: string) => url.searchParams.get(k);
  const seg = path.split('/').filter(Boolean); // ['api','v1',...]
  const rest = seg.slice(2); // after api/v1
  const M = method.toUpperCase();

  function fail(status: number, msg: string): never {
    throw new LocalApiError(status, msg);
  }

  // ---- auth ----
  if (rest[0] === 'auth' && rest[1] === 'dev-token' && M === 'POST') {
    const email = String(body?.email || '').trim().toLowerCase();
    const name = String(body?.name || '').trim() || email.split('@')[0];
    const role = String(body?.role || ROLE_BY_PRESET[email] || 'project_owner');
    if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) fail(422, 'A valid email address is required.');
    let user = s.users.find((u) => u.email === email);
    if (!user) {
      user = {
        id: uuid(), email, full_name: name, auth_provider: 'local',
        account_status: 'active', last_login_at: nowIso(), role,
      };
      s.users.push(user);
    } else {
      user.full_name = name;
      user.role = role;
      user.last_login_at = nowIso();
    }
    const token = uuid();
    s.sessions[token] = user.id;
    persist();
    return { access_token: token };
  }
  if (rest[0] === 'auth' && rest[1] === 'me' && M === 'GET') {
    const u = userFromToken(s, authHeader);
    return { ...u, memberships: membershipView(s, u) };
  }

  // ---- participant portal (token-auth) ----
  if (rest[0] === 'participants' && rest[2] === 'portal-access' && M === 'GET') {
    const p = s.participants.find((x) => x.id === rest[1]);
    if (!p || !participantTokenOk(s, p.id, q('token'))) fail(403, 'This portal link is invalid or has expired.');
    return { ...p, status: p.participant_status };
  }

  if (rest[0] === 'participants' && rest[2] === 'access-token' && M === 'POST') {
    userFromToken(s, authHeader);
    const p = s.participants.find((x) => x.id === rest[1]);
    if (!p) fail(404, 'Participant not found');
    const token = uuid().replace(/-/g, '');
    const expires = new Date(Date.now() + 7 * 24 * 3600 * 1000);
    s.participantTokens[token] = { participant_id: p.id, expires_at: expires.toISOString() };
    record(s, { project_id: p.project_id, participant_id: p.id, action: 'participant.token_issued', entity_type: 'participant', entity_id: p.id });
    persist();
    return { participant_id: p.id, token, expires_in: 7 * 24 * 3600, token_type: 'portal' };
  }

  if (rest[0] === 'participants' && rest[2] === 'clarification-requests' && M === 'POST') {
    const p = s.participants.find((x) => x.id === rest[1]);
    if (!p) fail(404, 'Participant not found');
    const tokenParam = q('token');
    if (!participantTokenOk(s, p.id, tokenParam)) {
      userFromToken(s, authHeader); // staff path
    }
    const concern = String(body?.concern || '').trim();
    if (!concern) fail(422, 'Please enter your question or notice.');
    const isWithdrawal = body?.request_type === 'withdrawal';
    const task: LocalTask = {
      id: uuid(), project_id: p.project_id, participant_id: p.id,
      task_type: 'participant_follow_up',
      title: isWithdrawal ? `Withdrawal request from ${p.display_name}` : `Question from ${p.display_name}`,
      description: concern + (body?.category ? `\n\nCategory: ${body.category}` : ''),
      status: 'open', priority: isWithdrawal ? 'urgent' : 'high',
      owner_user_id: null, due_date: null, created_at: nowIso(), completed_at: null,
    };
    s.tasks.push(task);
    if (isWithdrawal) {
      p.participant_status = 'withdrawn';
      p.updated_at = nowIso();
    }
    record(s, {
      project_id: p.project_id, participant_id: p.id, actor_type: 'user',
      action: isWithdrawal ? 'participant.withdrawal_requested' : 'participant.clarification_requested',
      entity_type: 'task', entity_id: task.id,
    });
    persist();
    return {
      participant_id: p.id, task_id: task.id, status: 'received',
      message: isWithdrawal
        ? 'Your withdrawal request has been recorded and the production team has been notified.'
        : 'Your question has been sent to the production team. They will follow up with you directly.',
    };
  }

  // ---- everything below requires a signed-in user ----
  const user = userFromToken(s, authHeader);

  // projects
  if (rest[0] === 'projects' && rest.length === 1 && M === 'GET') {
    const items = [...s.projects].sort((a, b) => b.created_at.localeCompare(a.created_at));
    return { items, total: items.length };
  }
  if (rest[0] === 'projects' && rest.length === 1 && M === 'POST') {
    const title = String(body?.title || '').trim();
    if (!title) fail(422, 'A project title is required.');
    const p: LocalProject = {
      id: uuid(), title,
      description: body?.description ?? null,
      purpose: body?.purpose ?? null,
      themes: Array.isArray(body?.themes) ? body.themes : [],
      intended_audiences: Array.isArray(body?.intended_audiences) ? body.intended_audiences : [],
      distribution_plan: body?.distribution_plan ?? null,
      status: 'active', created_at: nowIso(), updated_at: nowIso(),
    };
    s.projects.push(p);
    record(s, { project_id: p.id, action: 'project.created', entity_type: 'project', entity_id: p.id });
    persist();
    return p;
  }
  if (rest[0] === 'projects' && rest.length === 2 && M === 'GET') {
    const p = s.projects.find((x) => x.id === rest[1]);
    if (!p) fail(404, 'Project not found');
    return p;
  }

  // participants
  if (rest[0] === 'projects' && rest[2] === 'participants' && M === 'GET') {
    const items = s.participants.filter((p) => p.project_id === rest[1]);
    return { items, total: items.length };
  }
  if (rest[0] === 'projects' && rest[2] === 'participants' && M === 'POST') {
    const proj = s.projects.find((x) => x.id === rest[1]);
    if (!proj) fail(404, 'Project not found');
    const name = String(body?.display_name || '').trim();
    if (!name) fail(422, 'A display name is required.');
    const p: LocalParticipant = {
      id: uuid(), project_id: proj.id, user_id: body?.linked_user_id ?? null,
      display_name: name,
      preferred_language: body?.preferred_language || 'English',
      preferred_contact_method: body?.preferred_contact_method || 'email',
      participant_status: 'active', notes: body?.notes ?? null,
      created_at: nowIso(), updated_at: nowIso(),
    };
    s.participants.push(p);
    record(s, { project_id: proj.id, participant_id: p.id, action: 'participant.created', entity_type: 'participant', entity_id: p.id });
    persist();
    return p;
  }
  if (rest[0] === 'participants' && rest.length === 2 && M === 'GET') {
    const p = s.participants.find((x) => x.id === rest[1]);
    if (!p) fail(404, 'Participant not found');
    return { ...p, status: p.participant_status };
  }

  // consent records
  if (rest[0] === 'participants' && rest[2] === 'consent-records' && M === 'GET') {
    const p = s.participants.find((x) => x.id === rest[1]);
    if (!p) fail(404, 'Participant not found');
    const tokenParam = q('token');
    if (tokenParam && !participantTokenOk(s, p.id, tokenParam)) fail(403, 'This portal link is invalid or has expired.');
    const items = s.consentRecords
      .filter((r) => r.participant_id === p.id)
      .sort((a, b) => b.version_number - a.version_number)
      .map((r) => ({ ...r, version: r.version_number, status: r.record_status }));
    return { items, total: items.length };
  }
  if (rest[0] === 'participants' && rest[2] === 'consent-records' && M === 'POST') {
    const p = s.participants.find((x) => x.id === rest[1]);
    if (!p) fail(404, 'Participant not found');
    const choiceIn: any[] = Array.isArray(body?.choices) ? body.choices : [];
    if (!choiceIn.length) fail(422, 'At least one consent choice is required.');
    const version = Math.max(0, ...s.consentRecords.filter((r) => r.participant_id === p.id).map((r) => r.version_number)) + 1;
    const when = nowIso();
    const rec: LocalConsentRecord = {
      id: uuid(), participant_id: p.id, project_id: p.project_id,
      source_type: body?.source_type || 'manual',
      source_document_id: body?.source_document_id ?? null,
      record_status: 'awaiting_confirmation',
      explanation: body?.explanation ?? null,
      choices: choiceIn.map((c) => ({
        id: uuid(), category: String(c.category), choice: String(c.choice || 'not_discussed'),
        explanation: c.explanation ?? null, evidence_reference: c.evidence_reference ?? null,
        source_type: c.source_type || body?.source_type || 'manual',
        confidence_if_extracted: c.confidence_if_extracted ?? null,
        confirmed_by: null, confirmed_at: null, created_at: when,
      })),
      confirmed_by_participant_at: null, confirmed_at: null,
      version_number: version, created_at: when,
    };
    s.consentRecords.push(rec);
    record(s, { project_id: p.project_id, participant_id: p.id, action: 'consent_record.created', entity_type: 'consent_record', entity_id: rec.id });
    persist();
    return { ...rec, version: rec.version_number, status: rec.record_status };
  }
  if (rest[0] === 'consent-records' && rest[2] === 'confirm' && M === 'POST') {
    const rec = s.consentRecords.find((r) => r.id === rest[1]);
    if (!rec) fail(404, 'Consent record not found');
    for (const other of s.consentRecords) {
      if (other.participant_id === rec.participant_id && other.id !== rec.id && other.record_status === 'confirmed') {
        other.record_status = 'superseded';
      }
    }
    rec.record_status = 'confirmed';
    rec.confirmed_at = nowIso();
    rec.confirmed_by_participant_at = body?.confirmed_by_participant_at || nowIso();
    for (const c of rec.choices) {
      c.confirmed_by = user.full_name;
      c.confirmed_at = rec.confirmed_at;
    }
    record(s, { project_id: rec.project_id, participant_id: rec.participant_id, action: 'consent_record.confirmed', entity_type: 'consent_record', entity_id: rec.id, reason: body?.notes ?? null });
    persist();
    return { ...rec, version: rec.version_number, status: rec.record_status };
  }

  // documents
  if (rest[0] === 'projects' && rest[2] === 'documents' && M === 'GET') {
    const items = s.documents.filter((d) => d.project_id === rest[1]);
    return { items, total: items.length };
  }
  if (rest[0] === 'participants' && rest[2] === 'documents' && rest[3] === 'upload-url' && M === 'POST') {
    const p = s.participants.find((x) => x.id === rest[1]);
    if (!p) fail(404, 'Participant not found');
    const storageKey = `local/${uuid()}`;
    return { storage_key: storageKey, upload_url: `local://upload/${storageKey}`, expires_in_seconds: 3600, max_upload_bytes: 10 * 1024 * 1024 };
  }
  if (rest[0] === 'participants' && rest[2] === 'documents' && rest[3] === 'complete-upload' && M === 'POST') {
    const p = s.participants.find((x) => x.id === rest[1]);
    if (!p) fail(404, 'Participant not found');
    const doc: LocalDocument = {
      id: uuid(), project_id: p.project_id, participant_id: p.id,
      storage_key: body?.storage_key || `local/${uuid()}`,
      original_filename: body?.original_filename || 'document',
      mime_type: body?.mime_type || 'application/octet-stream',
      file_size: body?.file_size || 0,
      scan_status: 'clean',
      extracted_text: typeof body?.extracted_text === 'string' ? body.extracted_text : null,
      created_at: nowIso(),
    };
    s.documents.push(doc);
    record(s, { project_id: p.project_id, participant_id: p.id, action: 'document.uploaded', entity_type: 'document', entity_id: doc.id });
    persist();
    return doc;
  }
  if (rest[0] === 'documents' && rest[2] === 'extract' && M === 'POST') {
    const doc = s.documents.find((d) => d.id === rest[1]);
    if (!doc) fail(404, 'Document not found');
    record(s, { project_id: doc.project_id, participant_id: doc.participant_id, action: 'document.extracted', entity_type: 'document', entity_id: doc.id });
    persist();
    return {
      document_id: doc.id,
      extracted_text: doc.extracted_text || 'No embedded text could be read from this file. Scanned images need a manual review.',
    };
  }

  // proposed uses
  if (rest[0] === 'projects' && rest[2] === 'proposed-uses' && M === 'GET') {
    const items = s.proposedUses.filter((u) => u.project_id === rest[1]);
    return { items, total: items.length };
  }
  if (rest[0] === 'projects' && rest[2] === 'proposed-uses' && M === 'POST') {
    const proj = s.projects.find((x) => x.id === rest[1]);
    if (!proj) fail(404, 'Project not found');
    const participant = s.participants.find((p) => p.id === body?.participant_id && p.project_id === proj.id);
    if (!participant) fail(404, 'Participant not found');
    const useType = String(body?.use_type || '').trim();
    if (!useType) fail(422, 'A use type is required.');
    const use: LocalProposedUse = {
      id: uuid(), project_id: proj.id, participant_id: participant.id,
      story_element_id: null, use_type: useType,
      platform: body?.platform ?? null, audience: body?.audience ?? null,
      purpose: body?.purpose ?? null, territory: body?.territory ?? null,
      context_description: body?.context_description ?? null,
      status: 'submitted', version: 1, created_at: nowIso(), updated_at: nowIso(),
    };
    s.proposedUses.push(use);
    record(s, { project_id: proj.id, participant_id: participant.id, action: 'proposed_use.created', entity_type: 'proposed_use', entity_id: use.id });
    if (body?.run_analysis) runAnalysis(s, use, user.id);
    persist();
    return use;
  }
  if (rest[0] === 'proposed-uses' && rest.length === 2 && M === 'GET') {
    const use = s.proposedUses.find((u) => u.id === rest[1]);
    if (!use) fail(404, 'Proposed use not found');
    return use;
  }
  if (rest[0] === 'proposed-uses' && rest[2] === 'analyse' && M === 'POST') {
    const use = s.proposedUses.find((u) => u.id === rest[1]);
    if (!use) fail(404, 'Proposed use not found');
    const { analysis, review, tasks } = runAnalysis(s, use, user.id);
    persist();
    const riskMap: Record<string, number> = { PARTICIPANT_DECLINED: 0.9, HUMAN_REVIEW_REQUIRED: 0.7, NEEDS_DISCUSSION: 0.5, UNRESOLVED: 0.4, RECORDED_CHOICE_MATCH: 0.1 };
    return {
      proposed_use_id: use.id,
      outcome: analysis.outcome,
      analysis: { id: analysis.id, proposed_use_id: use.id, outcome: analysis.outcome, risk_score: riskMap[analysis.outcome] ?? 0.5, findings: analysis.findings, created_at: analysis.created_at },
      requires_human_review: true,
      tasks_created: tasks.map((t) => t.id),
      review_id: review.id,
    };
  }
  if (rest[0] === 'proposed-uses' && rest[2] === 'agent-findings' && M === 'GET') {
    return s.agentRuns
      .filter((r) => r.proposed_use_id === rest[1])
      .map((r) => ({ agent_name: r.agent_name, execution_status: r.execution_status, output_data: r.output_data, created_at: r.created_at }));
  }

  // reviews
  if (rest[0] === 'projects' && rest[2] === 'reviews' && M === 'GET') {
    const items = s.reviews.filter((r) => r.project_id === rest[1]);
    return { items, total: items.length };
  }
  if (rest[0] === 'reviews' && rest.length === 2 && M === 'GET') {
    const r = s.reviews.find((x) => x.id === rest[1]);
    if (!r) fail(404, 'Review not found');
    return r;
  }
  if (rest[0] === 'reviews' && rest[2] === 'human-decision' && M === 'POST') {
    const r = s.reviews.find((x) => x.id === rest[1]);
    if (!r) fail(404, 'Review not found');
    if (typeof body?.expected_version === 'number' && body.expected_version !== r.version) {
      fail(409, 'This review changed since you opened it. Reload and try again.');
    }
    const reason = String(body?.reason || '').trim();
    if (!reason) fail(422, 'A written reason is required for every human decision.');
    const decision = String(body?.decision || '');
    r.human_decision = decision;
    r.decision_reason = reason;
    r.decided_by = user.full_name;
    r.decided_at = nowIso();
    r.review_status = decision === 'escalate' ? 'escalated' : 'decided';
    r.version += 1;
    const use = s.proposedUses.find((u) => u.id === r.proposed_use_id);
    if (use) {
      if (decision === 'approve') use.status = 'approved';
      else if (decision === 'decline') use.status = 'declined';
      else if (decision === 'needs_participant_discussion') use.status = 'awaiting_participant_discussion';
      use.version += 1;
      use.updated_at = nowIso();
    }
    record(s, { project_id: r.project_id, participant_id: use?.participant_id, action: 'review.decided', entity_type: 'review', entity_id: r.id, reason: `${decision}: ${reason}` });
    persist();
    return r;
  }
  if (rest[0] === 'reviews' && rest[2] === 'request-participant-discussion' && M === 'POST') {
    const r = s.reviews.find((x) => x.id === rest[1]);
    if (!r) fail(404, 'Review not found');
    r.human_decision = 'needs_participant_discussion';
    r.decision_reason = String(body?.reason || '') || null;
    r.decided_by = user.full_name;
    r.decided_at = nowIso();
    r.review_status = 'decided';
    r.version += 1;
    const use = s.proposedUses.find((u) => u.id === r.proposed_use_id);
    if (use) { use.status = 'awaiting_participant_discussion'; use.version += 1; use.updated_at = nowIso(); }
    record(s, { project_id: r.project_id, action: 'review.decided', entity_type: 'review', entity_id: r.id, reason: r.decision_reason });
    persist();
    return r;
  }

  // tasks
  if (rest[0] === 'projects' && rest[2] === 'tasks' && M === 'GET') {
    const items = s.tasks.filter((t) => t.project_id === rest[1]);
    return { items, total: items.length };
  }
  if (rest[0] === 'tasks' && M === 'PATCH') {
    const t = s.tasks.find((x) => x.id === rest[1]);
    if (!t) fail(404, 'Task not found');
    if (body?.status) t.status = body.status;
    if (body?.priority) t.priority = body.priority;
    if (body?.due_date !== undefined) t.due_date = body.due_date;
    if ((body?.status === 'done' || body?.status === 'completed') && !t.completed_at) {
      t.completed_at = nowIso();
      record(s, { project_id: t.project_id, participant_id: t.participant_id, action: 'task.completed', entity_type: 'task', entity_id: t.id });
    }
    persist();
    return t;
  }

  // communications
  if (rest[0] === 'projects' && rest[2] === 'communications' && M === 'GET') {
    let items = s.communications.filter((c) => c.project_id === rest[1]);
    if (q('participant_id')) items = items.filter((c) => c.participant_id === q('participant_id'));
    return items;
  }
  if (rest[0] === 'projects' && rest[2] === 'communications' && M === 'POST') {
    const proj = s.projects.find((x) => x.id === rest[1]);
    if (!proj) fail(404, 'Project not found');
    const participant = s.participants.find((p) => p.id === body?.participant_id);
    if (!participant) fail(404, 'Participant not found');
    const comm: LocalCommunication = {
      id: uuid(), project_id: proj.id, participant_id: participant.id,
      communication_type: body?.communication_type || 'email',
      subject: body?.subject ?? null,
      draft_content: body?.draft_content ?? '',
      communication_status: 'draft', created_by: user.id,
      approved_by: null, approved_at: null, sent_at: null,
      version: 1, created_at: nowIso(),
    };
    s.communications.push(comm);
    record(s, { project_id: proj.id, participant_id: participant.id, action: 'communication.drafted', entity_type: 'communication', entity_id: comm.id });
    persist();
    return comm;
  }
  if (rest[0] === 'communications' && rest[2] === 'approve' && M === 'POST') {
    const c = s.communications.find((x) => x.id === rest[1]);
    if (!c) fail(404, 'Communication not found');
    c.communication_status = 'approved';
    c.approved_by = user.full_name;
    c.approved_at = nowIso();
    c.version += 1;
    record(s, { project_id: c.project_id, participant_id: c.participant_id, action: 'communication.approved', entity_type: 'communication', entity_id: c.id, reason: body?.notes ?? null });
    persist();
    return c;
  }
  if (rest[0] === 'communications' && rest[2] === 'send' && M === 'POST') {
    const c = s.communications.find((x) => x.id === rest[1]);
    if (!c) fail(404, 'Communication not found');
    if (c.communication_status !== 'approved') fail(409, 'A communication must be approved before it can be sent.');
    c.communication_status = 'sent';
    c.sent_at = nowIso();
    c.version += 1;
    record(s, { project_id: c.project_id, participant_id: c.participant_id, action: 'communication.sent', entity_type: 'communication', entity_id: c.id });
    persist();
    return c;
  }

  // timeline
  if (rest[0] === 'projects' && rest[2] === 'timeline' && M === 'GET') {
    const items = s.timeline
      .filter((t) => t.project_id === rest[1])
      .sort((a, b) => b.timestamp.localeCompare(a.timestamp));
    return { items, next_cursor: null };
  }
  if (rest[0] === 'participants' && rest[2] === 'timeline' && M === 'GET') {
    const p = s.participants.find((x) => x.id === rest[1]);
    if (!p) fail(404, 'Participant not found');
    const tokenParam = q('token');
    if (tokenParam && !participantTokenOk(s, p.id, tokenParam)) fail(403, 'This portal link is invalid or has expired.');
    const items = s.timeline
      .filter((t) => t.participant_id === p.id)
      .sort((a, b) => b.timestamp.localeCompare(a.timestamp));
    return { items, next_cursor: null };
  }

  // metrics
  if (rest[0] === 'metrics' && M === 'GET') {
    return {
      projects: s.projects.length,
      participants: s.participants.length,
      consent_records: s.consentRecords.length,
      proposed_uses: s.proposedUses.length,
      pending_reviews: s.reviews.filter((r) => r.review_status === 'pending').length,
      open_tasks: s.tasks.filter((t) => !['done', 'completed', 'cancelled'].includes(t.status)).length,
    };
  }

  // analytics
  if (rest[0] === 'analytics') {
    return analytics(s, rest.slice(1), q, M, body);
  }

  fail(404, `Unknown endpoint: ${M} ${path}`);
}

// ---------------------------------------------------------------------------
// Analytics: computed from the local store
// ---------------------------------------------------------------------------

const CANONICAL = [
  'interview_recording', 'documentary_appearance', 'name_identification', 'face_identification',
  'sensitive_personal_details', 'promotional_clips', 'festival_submissions', 'ai_transcription',
  'voice_cloning', 'synthetic_likeness', 'third_party_ai_processing', 'new_audience',
  'new_territory', 'new_platform', 'new_story_context',
];

function latestConfirmedPerParticipant(s: Store, projectId?: string): LocalConsentRecord[] {
  const out: LocalConsentRecord[] = [];
  const participants = s.participants.filter((p) => !projectId || p.project_id === projectId);
  for (const p of participants) {
    const latest = latestConfirmed(s, p.id);
    if (latest) out.push(latest);
  }
  return out;
}

function choiceCounts(records: LocalConsentRecord[]) {
  const counts: Record<string, number> = { agreed: 0, declined: 0, needs_clarification: 0, not_discussed: 0, awaiting_confirmation: 0, explained: 0 };
  let total = 0;
  for (const r of records) {
    for (const c of r.choices) {
      total += 1;
      if (counts[c.choice] !== undefined) counts[c.choice] += 1;
      else counts.not_discussed += 1;
    }
  }
  return { counts, total };
}

function rates(counts: Record<string, number>, total: number) {
  const settled = (counts.agreed || 0) + (counts.declined || 0);
  return {
    discussion_coverage: total ? Math.round(((total - (counts.not_discussed || 0)) / total) * 1000) / 10 : 0,
    approval_rate: settled ? Math.round(((counts.agreed || 0) / settled) * 1000) / 10 : 0,
    resolution_rate: total ? Math.round((settled / total) * 1000) / 10 : 0,
    unresolved: total - settled,
  };
}

function analytics(
  s: Store,
  rest: string[],
  q: (k: string) => string | null,
  M: string,
  body: any,
): any {
  const projectId = q('project_id') || undefined;
  const projects = projectId ? s.projects.filter((p) => p.id === projectId) : s.projects;
  const project = projectId ? projects[0] : null;
  const participants = s.participants.filter((p) => !projectId || p.project_id === projectId);
  const reviews = s.reviews.filter((r) => !projectId || r.project_id === projectId);
  const tasks = s.tasks.filter((t) => !projectId || t.project_id === projectId);
  const uses = s.proposedUses.filter((u) => !projectId || u.project_id === projectId);
  const timeline = s.timeline.filter((t) => !projectId || t.project_id === projectId);
  const records = latestConfirmedPerParticipant(s, projectId);
  const { counts, total } = choiceCounts(records);
  const r = rates(counts, total);

  const period = {
    start_date: q('start_date'), end_date: q('end_date'), timezone: 'UTC',
  };
  const scope = {
    project_id: projectId ?? null,
    project_title: project ? project.title : null,
    authorized_projects_count: s.projects.length,
  };
  const decidedReviews = reviews.filter((x) => x.review_status === 'decided' || x.review_status === 'escalated');
  const turnarounds = decidedReviews
    .filter((x) => x.decided_at)
    .map((x) => (new Date(x.decided_at as string).getTime() - new Date(x.created_at).getTime()) / 3_600_000);
  const avgTurn = turnarounds.length ? Math.round((turnarounds.reduce((a, b) => a + b, 0) / turnarounds.length) * 10) / 10 : null;
  const openTasks = tasks.filter((t) => !['done', 'completed', 'cancelled'].includes(t.status));
  const overdue = openTasks.filter((t) => t.due_date && new Date(t.due_date).getTime() < Date.now());
  const withdrawals = timeline.filter((t) => t.action === 'participant.withdrawal_requested');

  const head = rest[0];
  const sub = rest[1];

  if (head === 'overview') {
    return {
      period, scope, generated_at: nowIso(),
      total_projects: projects.length,
      total_participants: participants.length,
      active_participants: participants.filter((p) => p.participant_status === 'active').length,
      withdrawn_participants: participants.filter((p) => p.participant_status === 'withdrawn').length,
      discussion_coverage: r.discussion_coverage,
      approval_rate: r.approval_rate,
      resolution_rate: r.resolution_rate,
      unresolved_categories: r.unresolved,
      pending_human_reviews: reviews.filter((x) => x.review_status === 'pending' || x.review_status === 'in_progress').length,
      completed_reviews: decidedReviews.length,
      withdrawal_requests: withdrawals.length,
      urgent_care_tasks: openTasks.filter((t) => t.priority === 'urgent').length,
      open_care_tasks: openTasks.filter((t) => t.task_type === 'participant_follow_up').length,
      overdue_tasks: overdue.length,
      avg_review_turnaround_hours: avgTurn,
      data_completeness: 'complete',
    };
  }

  if (head === 'projects' && !sub) {
    return s.projects.map((p) => {
      const pRecords = latestConfirmedPerParticipant(s, p.id);
      const { counts: c, total: t } = choiceCounts(pRecords);
      const rr = rates(c, t);
      const pReviews = s.reviews.filter((x) => x.project_id === p.id);
      const pTasks = s.tasks.filter((x) => x.project_id === p.id && !['done', 'completed', 'cancelled'].includes(x.status));
      return {
        project_id: p.id,
        project_title: p.title,
        project_status: p.status,
        participants_count: s.participants.filter((x) => x.project_id === p.id).length,
        discussion_coverage: rr.discussion_coverage,
        approval_rate: rr.approval_rate,
        resolution_rate: rr.resolution_rate,
        unresolved_categories: rr.unresolved,
        pending_reviews_count: pReviews.filter((x) => x.review_status === 'pending' || x.review_status === 'in_progress').length,
        urgent_tasks_count: pTasks.filter((x) => x.priority === 'urgent').length,
        withdrawal_requests_count: s.timeline.filter((x) => x.project_id === p.id && x.action === 'participant.withdrawal_requested').length,
      };
    });
  }

  if (head === 'consent' && sub === 'categories') {
    return CANONICAL.map((cat) => {
      const catChoices = records.flatMap((rec) => rec.choices.filter((c) => c.category === cat));
      const c: Record<string, number> = { agreed: 0, declined: 0, needs_clarification: 0, not_discussed: 0, awaiting_confirmation: 0, explained: 0 };
      for (const ch of catChoices) c[ch.choice] = (c[ch.choice] || 0) + 1;
      const totalCat = catChoices.length;
      const settled = c.agreed + c.declined;
      return {
        category: cat,
        total_applicable: totalCat,
        agreed: c.agreed, declined: c.declined, needs_clarification: c.needs_clarification,
        not_discussed: c.not_discussed, awaiting_confirmation: c.awaiting_confirmation, explained: c.explained,
        discussion_coverage: totalCat ? Math.round(((totalCat - c.not_discussed) / totalCat) * 1000) / 10 : 0,
        approval_rate: settled ? Math.round((c.agreed / settled) * 1000) / 10 : 0,
        resolution_rate: totalCat ? Math.round((settled / totalCat) * 1000) / 10 : 0,
      };
    });
  }

  if (head === 'consent') {
    const categories = analytics(s, ['consent', 'categories'], q, M, body);
    return {
      period, scope,
      total_participants: participants.length,
      total_applicable_choices: total,
      agreed_choices: counts.agreed,
      declined_choices: counts.declined,
      needs_clarification_choices: counts.needs_clarification,
      not_discussed_choices: counts.not_discussed,
      awaiting_confirmation_choices: counts.awaiting_confirmation,
      explained_choices: counts.explained,
      discussion_coverage: r.discussion_coverage,
      approval_rate: r.approval_rate,
      resolution_rate: r.resolution_rate,
      unresolved_categories_count: r.unresolved,
      categories,
    };
  }

  if (head === 'reviews') {
    const decisions: Record<string, number> = {};
    for (const x of decidedReviews) if (x.human_decision) decisions[x.human_decision] = (decisions[x.human_decision] || 0) + 1;
    const useTypes: Record<string, number> = {};
    for (const u of uses) useTypes[u.use_type] = (useTypes[u.use_type] || 0) + 1;
    const sorted = [...turnarounds].sort((a, b) => a - b);
    const median = sorted.length ? Math.round(sorted[Math.floor(sorted.length / 2)] * 10) / 10 : null;
    return {
      period, scope,
      total_proposed_uses: uses.length,
      pending_reviews: reviews.filter((x) => x.review_status === 'pending' || x.review_status === 'in_progress').length,
      completed_reviews: decidedReviews.length,
      decisions_breakdown: decisions,
      use_type_breakdown: useTypes,
      avg_turnaround_hours: avgTurn,
      median_turnaround_hours: median,
    };
  }

  if (head === 'operations') {
    return {
      period, scope,
      total_tasks: tasks.length,
      open_tasks: openTasks.length,
      in_progress_tasks: tasks.filter((t) => t.status === 'in_progress').length,
      completed_tasks: tasks.filter((t) => ['done', 'completed'].includes(t.status)).length,
      urgent_tasks: tasks.filter((t) => t.priority === 'urgent').length,
      high_priority_tasks: tasks.filter((t) => t.priority === 'high').length,
      overdue_tasks: overdue.length,
      participant_follow_up_tasks: tasks.filter((t) => t.task_type === 'participant_follow_up').length,
      unresolved_permission_tasks: tasks.filter((t) => t.task_type === 'unresolved_permission').length,
      avg_resolution_hours: null,
    };
  }

  if (head === 'withdrawals') {
    const resolvedCare = tasks.filter((t) => t.task_type === 'participant_follow_up' && ['done', 'completed'].includes(t.status)).length;
    return {
      period, scope,
      total_withdrawal_requests: withdrawals.length,
      active_withdrawals_in_period: withdrawals.length,
      pending_care_tasks: openTasks.filter((t) => t.task_type === 'participant_follow_up').length,
      resolved_care_tasks: resolvedCare,
      avg_resolution_hours: null,
      recent_withdrawal_events: withdrawals.slice(0, 10).map((w) => ({
        id: w.id, project_id: w.project_id, participant_id: w.participant_id,
        timestamp: w.timestamp, action: w.action,
      })),
    };
  }

  if (head === 'advisory') {
    const runs = s.agentRuns.filter((run) => {
      const use = s.proposedUses.find((u) => u.id === run.proposed_use_id);
      return use && (!projectId || use.project_id === projectId);
    });
    const byAgent: Record<string, number> = {};
    const byStatus: Record<string, number> = {};
    for (const run of runs) {
      byAgent[run.agent_name] = (byAgent[run.agent_name] || 0) + 1;
      byStatus[run.execution_status] = (byStatus[run.execution_status] || 0) + 1;
    }
    return {
      period, scope,
      total_advisory_runs: runs.length,
      runs_by_agent: byAgent,
      status_distribution: byStatus,
      alignment_rate: null,
      alignment_sample_size: 0,
      disclaimer: 'Agent findings are advisory only. Human review governs all decisions.',
    };
  }

  if (head === 'trends') {
    const interval = q('interval') || 'day';
    const end = q('end_date') ? new Date(q('end_date') as string) : new Date();
    const start = q('start_date') ? new Date(q('start_date') as string) : new Date(end.getTime() - 14 * 24 * 3600 * 1000);
    const buckets: Record<string, { consent_confirmed: number; reviews_decided: number; withdrawals_requested: number; tasks_completed: number; new_participants: number }> = {};
    const key = (d: Date) => d.toISOString().slice(0, 10);
    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + (interval === 'week' ? 7 : interval === 'month' ? 30 : 1))) {
      buckets[key(d)] = { consent_confirmed: 0, reviews_decided: 0, withdrawals_requested: 0, tasks_completed: 0, new_participants: 0 };
    }
    const bump = (ts: string | null, field: string) => {
      if (!ts) return;
      const k = key(new Date(ts));
      if (buckets[k]) (buckets[k] as any)[field] += 1;
    };
    for (const t of timeline) {
      if (t.action === 'consent_record.confirmed') bump(t.timestamp, 'consent_confirmed');
      if (t.action === 'review.decided') bump(t.timestamp, 'reviews_decided');
      if (t.action === 'participant.withdrawal_requested') bump(t.timestamp, 'withdrawals_requested');
      if (t.action === 'task.completed') bump(t.timestamp, 'tasks_completed');
      if (t.action === 'participant.created') bump(t.timestamp, 'new_participants');
    }
    return {
      period, scope, interval,
      series: Object.entries(buckets).map(([date, v]) => ({ date, ...v })),
    };
  }

  if (head === 'exports' && M === 'POST') {
    const format = body?.format === 'csv' ? 'csv' : 'json';
    const reportType = body?.report_type || 'overview';
    const data = analytics(s, [reportType === 'overview' ? 'overview' : reportType], q, 'GET', null);
    const content = format === 'json'
      ? JSON.stringify(data, null, 2)
      : Object.entries(data as Record<string, any>)
          .filter(([, v]) => typeof v !== 'object')
          .map(([k, v]) => `${k},${v}`)
          .join('\n');
    return {
      report_type: reportType,
      format,
      filename: `scenesteward-${reportType}-report.${format}`,
      generated_at: nowIso(),
      content,
    };
  }

  throw new LocalApiError(404, `Unknown analytics endpoint: ${rest.join('/')}`);
}
