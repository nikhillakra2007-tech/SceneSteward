/**
 * SceneSteward Analytics TypeScript Types
 * Directly maps to backend schemas in app.analytics.schemas.
 */

export interface DateRangeMetadata {
  start_date: string | null;
  end_date: string | null;
  timezone: string;
}

export interface AnalyticsScopeMetadata {
  project_id: string | null;
  project_title: string | null;
  authorized_projects_count: number;
}

export interface CategoryMetricDetail {
  category: string;
  total_applicable: number;
  agreed: number;
  declined: number;
  needs_clarification: number;
  not_discussed: number;
  awaiting_confirmation: number;
  explained: number;
  discussion_coverage: number;
  approval_rate: number;
  resolution_rate: number;
}

export interface ProjectAnalyticsSummary {
  project_id: string;
  project_title: string;
  project_status: string;
  participants_count: number;
  discussion_coverage: number;
  approval_rate: number;
  resolution_rate: number;
  unresolved_categories: number;
  pending_reviews_count: number;
  urgent_tasks_count: number;
  withdrawal_requests_count: number;
}

export interface AnalyticsOverview {
  period: DateRangeMetadata;
  scope: AnalyticsScopeMetadata;
  generated_at: string;
  total_projects: number;
  total_participants: number;
  active_participants: number;
  withdrawn_participants: number;
  discussion_coverage: number;
  approval_rate: number;
  resolution_rate: number;
  unresolved_categories: number;
  pending_human_reviews: number;
  completed_reviews: number;
  withdrawal_requests: number;
  urgent_care_tasks: number;
  open_care_tasks: number;
  overdue_tasks: number;
  avg_review_turnaround_hours: number | null;
  data_completeness: string;
}

export interface ConsentAnalytics {
  period: DateRangeMetadata;
  scope: AnalyticsScopeMetadata;
  total_participants: number;
  total_applicable_choices: number;
  agreed_choices: number;
  declined_choices: number;
  needs_clarification_choices: number;
  not_discussed_choices: number;
  awaiting_confirmation_choices: number;
  explained_choices: number;
  discussion_coverage: number;
  approval_rate: number;
  resolution_rate: number;
  unresolved_categories_count: number;
  categories: CategoryMetricDetail[];
}

export interface ReviewAnalytics {
  period: DateRangeMetadata;
  scope: AnalyticsScopeMetadata;
  total_proposed_uses: number;
  pending_reviews: number;
  completed_reviews: number;
  decisions_breakdown: Record<string, number>;
  use_type_breakdown: Record<string, number>;
  avg_turnaround_hours: number | null;
  median_turnaround_hours: number | null;
}

export interface OperationsAnalytics {
  period: DateRangeMetadata;
  scope: AnalyticsScopeMetadata;
  total_tasks: number;
  open_tasks: number;
  in_progress_tasks: number;
  completed_tasks: number;
  urgent_tasks: number;
  high_priority_tasks: number;
  overdue_tasks: number;
  participant_follow_up_tasks: number;
  unresolved_permission_tasks: number;
  avg_resolution_hours: number | null;
}

export interface WithdrawalAnalytics {
  period: DateRangeMetadata;
  scope: AnalyticsScopeMetadata;
  total_withdrawal_requests: number;
  active_withdrawals_in_period: number;
  pending_care_tasks: number;
  resolved_care_tasks: number;
  avg_resolution_hours: number | null;
  recent_withdrawal_events: Array<{
    id: string;
    project_id: string;
    participant_id: string | null;
    timestamp: string;
    action: string;
  }>;
}

export interface AdvisoryAnalytics {
  period: DateRangeMetadata;
  scope: AnalyticsScopeMetadata;
  total_advisory_runs: number;
  runs_by_agent: Record<string, number>;
  status_distribution: Record<string, number>;
  alignment_rate: number | null;
  alignment_sample_size: number;
  disclaimer: string;
}

export interface TrendDataPoint {
  date: string;
  consent_confirmed: number;
  reviews_decided: number;
  withdrawals_requested: number;
  tasks_completed: number;
  new_participants: number;
}

export interface TrendsAnalytics {
  period: DateRangeMetadata;
  scope: AnalyticsScopeMetadata;
  interval: string;
  series: TrendDataPoint[];
}

export interface ExportResponse {
  report_type: string;
  format: string;
  filename: string;
  generated_at: string;
  content: string;
}

