/**
 * SceneSteward API Client
 * Connects directly to the FastAPI backend at NEXT_PUBLIC_API_URL.
 * The backend is the single source of truth for consent evaluation,
 * RLS identity boundary enforcement, and human review state machines.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export interface User {
  id: string;
  email: string;
  full_name: string;
  auth_provider: string;
  account_status: string;
  last_login_at: string | null;
  memberships: Membership[];
}

export interface Membership {
  project_id: string;
  project_title: string;
  role: 'project_owner' | 'producer' | 'director' | 'archivist' | 'care_lead' | 'legal_counsel' | 'viewer' | 'participant';
  membership_status: string;
}

export interface Project {
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

export const CANONICAL_CATEGORIES = [
  'interview_recording',
  'documentary_appearance',
  'name_identification',
  'face_identification',
  'sensitive_personal_details',
  'promotional_clips',
  'festival_submissions',
  'ai_transcription',
  'voice_cloning',
  'synthetic_likeness',
  'third_party_ai_processing',
  'new_audience',
  'new_territory',
  'new_platform',
  'new_story_context',
] as const;

export type CanonicalCategory = (typeof CANONICAL_CATEGORIES)[number];

export interface Participant {
  id: string;
  project_id: string;
  user_id?: string | null;
  display_name: string;
  preferred_language: string;
  preferred_contact_method: string;
  participant_status: string;
  status?: string; // backwards compatibility alias
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConsentChoiceIn {
  category: string;
  choice: 'agreed' | 'declined' | 'not_discussed' | 'needs_clarification' | 'awaiting_confirmation' | 'explained';
  explanation?: string | null;
  evidence_reference?: string | null;
  source_type?: string;
  confidence_if_extracted?: number | null;
}

export interface ConsentChoiceOut {
  id: string;
  category: string;
  choice: string;
  explanation?: string | null;
  evidence_reference?: string | null;
  source_type: string;
  confidence_if_extracted?: number | null;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  created_at: string;
}

export interface ConsentRecord {
  id: string;
  participant_id: string;
  project_id: string;
  source_type: string;
  source_document_id: string | null;
  record_status?: string;
  status?: string; // alias
  explanation: string | null;
  choices: ConsentChoiceOut[] | Record<string, any>;
  confirmed_by_participant_at?: string | null;
  confirmed_at?: string | null;
  version_number?: number;
  version: number;
  created_at: string;
}

export interface ProposedUse {
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
  status: 'draft' | 'submitted' | 'analysed' | 'approved' | 'approved_with_restrictions' | 'declined' | 'awaiting_participant_discussion' | 'withdrawn';
  version: number;
  created_at: string;
  updated_at: string;
}

export interface Finding {
  category: string;
  status: 'MATCHED' | 'DISCREPANCY' | 'MISSING' | 'OVERREACH' | 'FLAGGED';
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  finding_type: string;
  description: string;
  details?: Record<string, any>;
}

export interface Analysis {
  id: string;
  proposed_use_id: string;
  outcome: 'PERMITTED' | 'PARTICIPANT_DECLINED' | 'UNRESOLVED' | 'RESTRICTED' | 'REQUIRES_CARE_REVIEW' | 'REQUIRES_LEGAL_REVIEW';
  risk_score: number;
  findings: Finding[];
  created_at: string;
}

export interface Review {
  id: string;
  project_id: string;
  proposed_use_id: string;
  review_status: 'pending' | 'in_progress' | 'decided' | 'escalated' | 'dismissed';
  human_decision: 'approve' | 'decline' | 'request_changes' | 'needs_participant_discussion' | 'escalate' | string | null;
  decision_reason: string | null;
  decided_by: string | null;
  decided_at: string | null;
  uncertainty: string | null;
  version: number;
  created_at: string;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  status: 'pending' | 'open' | 'in_progress' | 'completed' | 'done' | 'cancelled';
  priority: 'low' | 'medium' | 'normal' | 'high' | 'urgent';
  owner_user_id: string | null;
  due_date: string | null;
  created_at: string;
}

export interface ReleaseDocument {
  id: string;
  project_id: string;
  participant_id: string | null;
  storage_key?: string;
  original_filename: string;
  file_name?: string; // alias
  mime_type: string;
  file_size: number;
  file_size_bytes?: number; // alias
  scan_status: 'clean' | 'infected' | 'skipped' | 'failed' | 'processing' | string;
  extracted_text: string | null;
  created_at: string;
}

export interface Communication {
  id: string;
  project_id: string;
  participant_id: string;
  communication_type: string;
  channel?: string; // alias
  subject: string | null;
  draft_content: string | null;
  body?: string; // alias
  communication_status: string;
  status?: string; // alias
  created_by?: string;
  approved_by: string | null;
  approved_at?: string | null;
  sent_at: string | null;
  requires_response?: boolean;
  version?: number;
  created_at: string;
}

export interface TimelineEntry {
  id: string;
  timestamp: string;
  actor_type: string;
  action: string;
  entity_type: string;
  entity_id: string;
  reason: string | null;
  correlation_id: string | null;
  participant_id: string | null;
}

// Token helper
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('scenesteward_token');
}

export function setAuthToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('scenesteward_token', token);
}

export function removeAuthToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('scenesteward_token');
}

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});
  
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errMessage = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errMessage = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errMessage);
  }

  // Handle empty responses
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  return {} as T;
}

export const api = {
  // Auth
  async loginDev(email: string, name: string): Promise<{ access_token: string }> {
    const res = await apiFetch<{ access_token: string }>('/api/v1/auth/dev-token', {
      method: 'POST',
      body: JSON.stringify({ email, name }),
    });
    setAuthToken(res.access_token);
    return res;
  },

  async getMe(): Promise<User> {
    return apiFetch<User>('/api/v1/auth/me');
  },

  logout(): void {
    removeAuthToken();
  },

  // Projects
  async listProjects(): Promise<{ items: Project[]; total: number }> {
    return apiFetch<{ items: Project[]; total: number }>('/api/v1/projects');
  },

  async createProject(data: {
    title: string;
    description?: string;
    purpose?: string;
    themes?: string[];
    intended_audiences?: string[];
    distribution_plan?: string;
  }): Promise<Project> {
    return apiFetch<Project>('/api/v1/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getProject(projectId: string): Promise<Project> {
    return apiFetch<Project>(`/api/v1/projects/${projectId}`);
  },

  // Participants
  async listParticipants(projectId: string): Promise<{ items: Participant[]; total: number }> {
    return apiFetch<{ items: Participant[]; total: number }>(`/api/v1/projects/${projectId}/participants`);
  },

  async createParticipant(projectId: string, data: {
    display_name: string;
    preferred_language?: string;
    preferred_contact_method?: string;
    linked_user_id?: string;
    notes?: string;
  }): Promise<Participant> {
    return apiFetch<Participant>(`/api/v1/projects/${projectId}/participants`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getParticipant(participantId: string): Promise<Participant> {
    return apiFetch<Participant>(`/api/v1/participants/${participantId}`);
  },

  // Consent
  async getParticipantConsents(participantId: string, token?: string): Promise<{ items: ConsentRecord[]; total: number }> {
    const q = token ? `?token=${encodeURIComponent(token)}` : '';
    return apiFetch<{ items: ConsentRecord[]; total: number }>(`/api/v1/participants/${participantId}/consent-records${q}`);
  },

  async createConsentRecord(participantId: string, data: {
    source_type: string;
    source_document_id?: string | null;
    explanation?: string;
    choices: ConsentChoiceIn[] | Record<string, { choice: string; notes?: string; explanation?: string }>;
  }): Promise<ConsentRecord> {
    const formattedChoices: ConsentChoiceIn[] = Array.isArray(data.choices)
      ? data.choices
      : Object.entries(data.choices).map(([category, item]) => ({
          category,
          choice: (item.choice as any) || 'not_discussed',
          explanation: item.explanation || item.notes || undefined,
          source_type: data.source_type || 'manual',
        }));

    return apiFetch<ConsentRecord>(`/api/v1/participants/${participantId}/consent-records`, {
      method: 'POST',
      body: JSON.stringify({
        source_type: data.source_type,
        source_document_id: data.source_document_id || null,
        explanation: data.explanation || null,
        choices: formattedChoices,
      }),
    });
  },

  async confirmConsentRecord(recordId: string, payload: {
    confirmation_method: string;
    confirmed_by_participant_at: string;
    notes?: string;
  }): Promise<ConsentRecord> {
    return apiFetch<ConsentRecord>(`/api/v1/consent-records/${recordId}/confirm`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Documents
  async listDocuments(projectId: string): Promise<{ items: ReleaseDocument[]; total: number }> {
    const res = await apiFetch<{ items: any[]; total: number }>(`/api/v1/projects/${projectId}/documents`);
    return {
      total: res.total,
      items: (res.items || []).map((doc) => ({
        ...doc,
        file_name: doc.original_filename || doc.file_name,
        file_size_bytes: doc.file_size || doc.file_size_bytes,
      })),
    };
  },

  async createUploadUrl(participantId: string, data: {
    original_filename: string;
    mime_type: string;
    file_size: number;
  }): Promise<{ storage_key: string; upload_url: string; expires_in_seconds: number; max_upload_bytes: number }> {
    return apiFetch(`/api/v1/participants/${participantId}/documents/upload-url`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async completeUpload(participantId: string, data: {
    storage_key: string;
    original_filename: string;
    mime_type: string;
    file_size: number;
    title?: string;
    document_type?: string;
    notes?: string;
  }): Promise<ReleaseDocument> {
    const doc = await apiFetch<any>(`/api/v1/participants/${participantId}/documents/complete-upload`, {
      method: 'POST',
      body: JSON.stringify({
        ...data,
        document_type: data.document_type || 'release_form',
      }),
    });
    return {
      ...doc,
      file_name: doc.original_filename || doc.file_name,
      file_size_bytes: doc.file_size || doc.file_size_bytes,
    };
  },

  async extractDocument(documentId: string): Promise<{ document_id: string; extracted_text: string }> {
    return apiFetch(`/api/v1/documents/${documentId}/extract`, {
      method: 'POST',
    });
  },

  // Proposed Uses
  async listProposedUses(projectId: string): Promise<{ items: ProposedUse[]; total: number }> {
    return apiFetch<{ items: ProposedUse[]; total: number }>(`/api/v1/projects/${projectId}/proposed-uses`);
  },

  async createProposedUse(projectId: string, data: {
    participant_id: string;
    use_type: string;
    platform?: string;
    audience?: string;
    purpose?: string;
    territory?: string;
    context_description?: string;
    run_analysis?: boolean;
  }): Promise<ProposedUse> {
    return apiFetch<ProposedUse>(`/api/v1/projects/${projectId}/proposed-uses`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getProposedUse(useId: string): Promise<ProposedUse> {
    return apiFetch<ProposedUse>(`/api/v1/proposed-uses/${useId}`);
  },

  async analyseProposedUse(useId: string): Promise<{
    proposed_use_id: string;
    outcome: string;
    analysis: Analysis;
    requires_human_review: boolean;
    tasks_created: string[];
    review_id: string | null;
  }> {
    return apiFetch(`/api/v1/proposed-uses/${useId}/analyse`, {
      method: 'POST',
    });
  },

  async getAgentFindings(useId: string): Promise<any[]> {
    return apiFetch(`/api/v1/proposed-uses/${useId}/agent-findings`);
  },

  // Reviews
  async listReviews(projectId: string): Promise<{ items: Review[]; total: number }> {
    return apiFetch<{ items: Review[]; total: number }>(`/api/v1/projects/${projectId}/reviews`);
  },

  async getReview(reviewId: string): Promise<Review> {
    return apiFetch<Review>(`/api/v1/reviews/${reviewId}`);
  },

  async recordHumanDecision(reviewId: string, data: {
    decision: 'approve' | 'decline' | 'request_changes' | 'needs_participant_discussion' | 'escalate' | 'approved' | 'rejected' | 'approved_with_conditions' | string;
    reason: string;
    expected_version: number;
  }): Promise<Review> {
    let normalized = data.decision;
    if (normalized === 'approved') normalized = 'approve';
    if (normalized === 'rejected') normalized = 'decline';
    if (normalized === 'approved_with_conditions') normalized = 'request_changes';

    return apiFetch<Review>(`/api/v1/reviews/${reviewId}/human-decision`, {
      method: 'POST',
      body: JSON.stringify({
        decision: normalized,
        reason: data.reason,
        expected_version: data.expected_version,
      }),
    });
  },

  async requestParticipantDiscussion(reviewId: string, data: {
    reason: string;
    expected_version: number;
  }): Promise<Review> {
    return apiFetch<Review>(`/api/v1/reviews/${reviewId}/request-participant-discussion`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Tasks
  async listTasks(projectId: string): Promise<{ items: Task[]; total: number }> {
    return apiFetch<{ items: Task[]; total: number }>(`/api/v1/projects/${projectId}/tasks`);
  },

  async updateTask(taskId: string, data: {
    status?: string;
    priority?: string;
    due_date?: string;
  }): Promise<Task> {
    return apiFetch<Task>(`/api/v1/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  // Communications
  async listCommunications(projectId: string, participantId?: string): Promise<Communication[]> {
    const q = participantId ? `?participant_id=${participantId}` : '';
    const items = await apiFetch<any[]>(`/api/v1/projects/${projectId}/communications${q}`);
    return (items || []).map((comm) => ({
      ...comm,
      channel: comm.communication_type || comm.channel,
      body: comm.draft_content || comm.body,
      status: comm.communication_status || comm.status,
    }));
  },

  async createDraftCommunication(projectId: string, data: {
    participant_id: string;
    communication_type?: string;
    channel?: string;
    subject: string;
    draft_content?: string;
    body?: string;
    requires_response?: boolean;
  }): Promise<Communication> {
    const commType = data.communication_type || data.channel || 'email';
    const content = data.draft_content || data.body || '';
    const res = await apiFetch<any>(`/api/v1/projects/${projectId}/communications`, {
      method: 'POST',
      body: JSON.stringify({
        participant_id: data.participant_id,
        communication_type: commType,
        subject: data.subject,
        draft_content: content,
      }),
    });
    return {
      ...res,
      channel: res.communication_type || res.channel,
      body: res.draft_content || res.body,
      status: res.communication_status || res.status,
    };
  },

  async approveCommunication(communicationId: string, notes?: string): Promise<Communication> {
    const res = await apiFetch<any>(`/api/v1/communications/${communicationId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ notes: notes || null }),
    });
    return {
      ...res,
      channel: res.communication_type || res.channel,
      body: res.draft_content || res.body,
      status: res.communication_status || res.status,
    };
  },

  async sendCommunication(communicationId: string): Promise<Communication> {
    return apiFetch<Communication>(`/api/v1/communications/${communicationId}/send`, {
      method: 'POST',
    });
  },

  // Participant Portal & Token Security
  async issueParticipantToken(participantId: string): Promise<{
    participant_id: string;
    token: string;
    expires_in: number;
    token_type: string;
  }> {
    return apiFetch(`/api/v1/participants/${participantId}/access-token`, {
      method: 'POST',
    });
  },

  async getParticipantPortalAccess(participantId: string, token: string): Promise<Participant> {
    const res = await apiFetch<Participant>(`/api/v1/participants/${participantId}/portal-access?token=${encodeURIComponent(token)}`);
    return {
      ...res,
      status: res.participant_status || res.status,
    };
  },

  async submitClarificationRequest(
    participantId: string,
    data: {
      concern: string;
      category?: string;
      additional_context?: string;
      request_type?: string;
    },
    token?: string,
  ): Promise<{ participant_id: string; task_id: string; status: string; message: string }> {
    const q = token ? `?token=${encodeURIComponent(token)}` : '';
    return apiFetch(`/api/v1/participants/${participantId}/clarification-requests${q}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Timeline
  async getProjectTimeline(projectId: string): Promise<{ items: TimelineEntry[]; next_cursor: string | null }> {
    return apiFetch(`/api/v1/projects/${projectId}/timeline`);
  },

  async getParticipantTimeline(participantId: string, token?: string): Promise<{ items: TimelineEntry[]; next_cursor: string | null }> {
    const q = token ? `?token=${encodeURIComponent(token)}` : '';
    return apiFetch(`/api/v1/participants/${participantId}/timeline${q}`);
  },

  // Metrics
  async getMetrics(): Promise<any> {
    return apiFetch('/api/v1/metrics');
  },

  // Analytics Engine
  async getAnalyticsOverview(params?: {
    project_id?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<import('./analytics-types').AnalyticsOverview> {
    const query = new URLSearchParams();
    if (params?.project_id) query.set('project_id', params.project_id);
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiFetch(`/api/v1/analytics/overview${qs}`);
  },

  async getProjectsAnalyticsSummary(): Promise<import('./analytics-types').ProjectAnalyticsSummary[]> {
    return apiFetch('/api/v1/analytics/projects');
  },

  async getConsentAnalytics(params?: {
    project_id?: string;
    start_date?: string;
    end_date?: string;
    category?: string;
  }): Promise<import('./analytics-types').ConsentAnalytics> {
    const query = new URLSearchParams();
    if (params?.project_id) query.set('project_id', params.project_id);
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    if (params?.category) query.set('category', params.category);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiFetch(`/api/v1/analytics/consent${qs}`);
  },

  async getConsentCategoriesBreakdown(params?: {
    project_id?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<import('./analytics-types').CategoryMetricDetail[]> {
    const query = new URLSearchParams();
    if (params?.project_id) query.set('project_id', params.project_id);
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiFetch(`/api/v1/analytics/consent/categories${qs}`);
  },

  async getReviewAnalytics(params?: {
    project_id?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<import('./analytics-types').ReviewAnalytics> {
    const query = new URLSearchParams();
    if (params?.project_id) query.set('project_id', params.project_id);
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiFetch(`/api/v1/analytics/reviews${qs}`);
  },

  async getOperationsAnalytics(params?: {
    project_id?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<import('./analytics-types').OperationsAnalytics> {
    const query = new URLSearchParams();
    if (params?.project_id) query.set('project_id', params.project_id);
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiFetch(`/api/v1/analytics/operations${qs}`);
  },

  async getWithdrawalAnalytics(params?: {
    project_id?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<import('./analytics-types').WithdrawalAnalytics> {
    const query = new URLSearchParams();
    if (params?.project_id) query.set('project_id', params.project_id);
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiFetch(`/api/v1/analytics/withdrawals${qs}`);
  },

  async getAdvisoryAnalytics(params?: {
    project_id?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<import('./analytics-types').AdvisoryAnalytics> {
    const query = new URLSearchParams();
    if (params?.project_id) query.set('project_id', params.project_id);
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiFetch(`/api/v1/analytics/advisory${qs}`);
  },

  async getTrendsAnalytics(params?: {
    project_id?: string;
    start_date?: string;
    end_date?: string;
    interval?: 'day' | 'week' | 'month';
  }): Promise<import('./analytics-types').TrendsAnalytics> {
    const query = new URLSearchParams();
    if (params?.project_id) query.set('project_id', params.project_id);
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    if (params?.interval) query.set('interval', params.interval);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiFetch(`/api/v1/analytics/trends${qs}`);
  },

  async exportAnalytics(payload: {
    project_id?: string;
    report_type: string;
    format: 'csv' | 'json';
    start_date?: string;
    end_date?: string;
  }): Promise<import('./analytics-types').ExportResponse> {
    return apiFetch('/api/v1/analytics/exports', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
