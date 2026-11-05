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

export interface Participant {
  id: string;
  project_id: string;
  user_id: string | null;
  display_name: string;
  preferred_language: string;
  preferred_contact_method: string;
  status: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConsentChoice {
  category: string;
  choice: 'agreed' | 'declined' | 'not_discussed' | 'needs_clarification' | 'awaiting_confirmation' | 'explained';
  notes?: string;
  expires_at?: string | null;
}

export interface ConsentRecord {
  id: string;
  participant_id: string;
  project_id: string;
  source_type: 'release_form' | 'interview' | 'verbal_recorded' | 'written_correspondence' | 'system_import';
  source_document_id: string | null;
  status: 'draft' | 'pending_confirmation' | 'confirmed' | 'superseded';
  explanation: string | null;
  choices: Record<string, { choice: string; notes?: string; expires_at?: string | null }>;
  confirmed_by_participant_at: string | null;
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
  human_decision: 'approved' | 'approved_with_conditions' | 'rejected' | 'needs_participant_discussion' | null;
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
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  owner_user_id: string | null;
  due_date: string | null;
  created_at: string;
}

export interface ReleaseDocument {
  id: string;
  project_id: string;
  participant_id: string | null;
  file_name: string;
  mime_type: string;
  file_size_bytes: number;
  scan_status: 'clean' | 'infected' | 'skipped' | 'failed';
  extracted_text: string | null;
  created_at: string;
}

export interface Communication {
  id: string;
  project_id: string;
  participant_id: string;
  channel: 'email' | 'sms' | 'portal';
  subject: string;
  body: string;
  status: 'draft' | 'approved' | 'sent' | 'failed' | 'delivered';
  requires_response: boolean;
  version: number;
  approved_by: string | null;
  approved_at: string | null;
  sent_at: string | null;
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
  async getParticipantConsents(participantId: string): Promise<{ items: ConsentRecord[]; total: number }> {
    return apiFetch<{ items: ConsentRecord[]; total: number }>(`/api/v1/participants/${participantId}/consents`);
  },

  async createConsentRecord(participantId: string, data: {
    source_type: string;
    source_document_id?: string | null;
    explanation?: string;
    choices: Record<string, { choice: string; notes?: string; expires_at?: string | null }>;
  }): Promise<ConsentRecord> {
    return apiFetch<ConsentRecord>(`/api/v1/participants/${participantId}/consent-records`, {
      method: 'POST',
      body: JSON.stringify(data),
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
    return apiFetch<{ items: ReleaseDocument[]; total: number }>(`/api/v1/projects/${projectId}/documents`);
  },

  async createUploadUrl(projectId: string, data: {
    file_name: string;
    mime_type: string;
    file_size_bytes: number;
    participant_id?: string | null;
  }): Promise<{ document_id: string; upload_url: string; storage_key: string }> {
    return apiFetch(`/api/v1/projects/${projectId}/documents/upload-url`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async completeUpload(projectId: string, data: {
    document_id: string;
    storage_key: string;
  }): Promise<ReleaseDocument> {
    return apiFetch<ReleaseDocument>(`/api/v1/projects/${projectId}/documents/complete-upload`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
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
    decision: 'approved' | 'approved_with_conditions' | 'rejected';
    reason: string;
    expected_version: number;
  }): Promise<Review> {
    return apiFetch<Review>(`/api/v1/reviews/${reviewId}/human-decision`, {
      method: 'POST',
      body: JSON.stringify(data),
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
    return apiFetch<Communication[]>(`/api/v1/projects/${projectId}/communications${q}`);
  },

  async createDraftCommunication(projectId: string, data: {
    participant_id: string;
    channel: string;
    subject: string;
    body: string;
    requires_response?: boolean;
  }): Promise<Communication> {
    return apiFetch<Communication>(`/api/v1/projects/${projectId}/communications`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async approveCommunication(communicationId: string, expectedVersion: number): Promise<Communication> {
    return apiFetch<Communication>(`/api/v1/communications/${communicationId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ expected_version: expectedVersion }),
    });
  },

  async sendCommunication(communicationId: string): Promise<Communication> {
    return apiFetch<Communication>(`/api/v1/communications/${communicationId}/send`, {
      method: 'POST',
    });
  },

  // Timeline
  async getProjectTimeline(projectId: string): Promise<{ items: TimelineEntry[]; next_cursor: string | null }> {
    return apiFetch(`/api/v1/projects/${projectId}/timeline`);
  },

  async getParticipantTimeline(participantId: string): Promise<{ items: TimelineEntry[]; next_cursor: string | null }> {
    return apiFetch(`/api/v1/participants/${participantId}/timeline`);
  },

  // Metrics
  async getMetrics(): Promise<any> {
    return apiFetch('/api/v1/metrics');
  },
};
