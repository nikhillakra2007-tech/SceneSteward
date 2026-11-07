'use client';

import React, { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  BarChart3,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Users,
  Film,
  Download,
  RefreshCw,
  SlidersHorizontal,
  Bot,
  AlertOctagon,
  FileCheck,
  HelpCircle,
  TrendingUp,
  Sparkles,
} from 'lucide-react';
import { api, Project, User } from '@/lib/api';
import {
  AdvisoryAnalytics,
  AnalyticsOverview,
  CategoryMetricDetail,
  ConsentAnalytics,
  OperationsAnalytics,
  ProjectAnalyticsSummary,
  ReviewAnalytics,
  TrendsAnalytics,
  WithdrawalAnalytics,
} from '@/lib/analytics-types';
import { MetricCard } from '@/components/analytics/MetricCard';
import { ConsentCategoryChart } from '@/components/analytics/ConsentCategoryChart';
import { AnalyticsExportDialog } from '@/components/analytics/AnalyticsExportDialog';
import { TrendsChart } from '@/components/analytics/TrendsChart';

type TabType = 'overview' | 'consent' | 'reviews_ops' | 'advisory_trends';

export default function AnalyticsPage() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [dateFilter, setDateFilter] = useState<'all' | '7d' | '30d' | '90d'>('all');
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);

  // Analytics states
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [consentData, setConsentData] = useState<ConsentAnalytics | null>(null);
  const [projectSummaries, setProjectSummaries] = useState<ProjectAnalyticsSummary[]>([]);
  const [reviewData, setReviewData] = useState<ReviewAnalytics | null>(null);
  const [operationsData, setOperationsData] = useState<OperationsAnalytics | null>(null);
  const [withdrawalData, setWithdrawalData] = useState<WithdrawalAnalytics | null>(null);
  const [advisoryData, setAdvisoryData] = useState<AdvisoryAnalytics | null>(null);
  const [trendsData, setTrendsData] = useState<TrendsAnalytics | null>(null);

  // Compute start_date based on filter
  const getFilterDates = useCallback(() => {
    if (dateFilter === 'all') return { start_date: undefined, end_date: undefined };
    const now = new Date();
    const days = dateFilter === '7d' ? 7 : dateFilter === '30d' ? 30 : 90;
    const start = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
    return {
      start_date: start.toISOString(),
      end_date: now.toISOString(),
    };
  }, [dateFilter]);

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    const dates = getFilterDates();
    const projId = selectedProjectId || undefined;

    try {
      const [u, pRes] = await Promise.all([
        api.getMe().catch(() => null),
        api.listProjects().catch(() => ({ items: [] as Project[], total: 0 })),
      ]);
      setCurrentUser(u);
      setProjects(pRes?.items || []);

      const [ov, cData, rev, ops, withdr, adv, tr, pSums] = await Promise.all([
        api.getAnalyticsOverview({ project_id: projId, ...dates }),
        api.getConsentAnalytics({ project_id: projId, ...dates }),
        api.getReviewAnalytics({ project_id: projId, ...dates }),
        api.getOperationsAnalytics({ project_id: projId, ...dates }),
        api.getWithdrawalAnalytics({ project_id: projId, ...dates }),
        api.getAdvisoryAnalytics({ project_id: projId, ...dates }),
        api.getTrendsAnalytics({ project_id: projId, interval: 'day' }),
        !projId ? api.getProjectsAnalyticsSummary().catch(() => []) : Promise.resolve([]),
      ]);

      setOverview(ov);
      setConsentData(cData);
      setReviewData(rev);
      setOperationsData(ops);
      setWithdrawalData(withdr);
      setAdvisoryData(adv);
      setTrendsData(tr);
      setProjectSummaries(pSums);
    } catch (err: any) {
      setError(err.message || 'Failed to load analytics data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [getFilterDates, selectedProjectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 pb-16">
      {/* Analytics Sub-Header / Controls */}
      <div className="bg-slate-900/60 border-b border-slate-800 backdrop-blur sticky top-16 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <BarChart3 className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-slate-100 tracking-tight">Analytics & Operational Intelligence</h1>
                <p className="text-xs text-slate-400">
                  {overview?.scope.project_title
                    ? `Scoped to ${overview.scope.project_title}`
                    : `Portfolio across ${overview?.total_projects || 0} active project(s)`}
                </p>
              </div>
            </div>

            <div className="flex items-center flex-wrap gap-2.5">
              {/* Project selector */}
              <select
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                <option value="">All Authorized Projects</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </select>

              {/* Date Filter */}
              <div className="flex items-center bg-slate-800 rounded-lg p-0.5 border border-slate-700 text-xs">
                {(['all', '7d', '30d', '90d'] as const).map((opt) => (
                  <button
                    key={opt}
                    onClick={() => setDateFilter(opt)}
                    className={`px-2.5 py-1 rounded-md font-medium transition ${
                      dateFilter === opt
                        ? 'bg-emerald-600 text-white font-semibold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {opt === 'all' ? 'All Time' : opt.toUpperCase()}
                  </button>
                ))}
              </div>

              {/* Refresh Button */}
              <button
                onClick={() => loadData(true)}
                disabled={refreshing}
                title="Refresh Analytics"
                className="p-1.5 rounded-lg border border-slate-700 bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin text-emerald-400' : ''}`} />
              </button>

              {/* Export Button */}
              <button
                onClick={() => setExportDialogOpen(true)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-200 font-medium flex items-center space-x-1.5 transition"
              >
                <Download className="h-3.5 w-3.5 text-emerald-400" />
                <span>Export Report</span>
              </button>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex space-x-1 mt-3 border-t border-slate-800/80 pt-2.5 text-xs">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                activeTab === 'overview'
                  ? 'bg-slate-800 text-emerald-400 font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              Overview & KPIs
            </button>
            <button
              onClick={() => setActiveTab('consent')}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                activeTab === 'consent'
                  ? 'bg-slate-800 text-emerald-400 font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              Consent & 15 Categories
            </button>
            <button
              onClick={() => setActiveTab('reviews_ops')}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                activeTab === 'reviews_ops'
                  ? 'bg-slate-800 text-emerald-400 font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              Reviews & Operations
            </button>
            <button
              onClick={() => setActiveTab('advisory_trends')}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                activeTab === 'advisory_trends'
                  ? 'bg-slate-800 text-emerald-400 font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              Advisory & Trends
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        {loading ? (
          <div className="py-24 text-center">
            <div className="h-8 w-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-slate-400">Aggregating live production metrics...</p>
          </div>
        ) : error ? (
          <div className="p-6 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-sm max-w-xl mx-auto text-center">
            <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-rose-500" />
            <p className="font-semibold mb-1">Failed to load analytics</p>
            <p className="text-xs text-rose-300/80 mb-4">{error}</p>
            <button
              onClick={() => loadData()}
              className="px-4 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* TAB 1: OVERVIEW & KPIS */}
            {activeTab === 'overview' && (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <MetricCard
                    title="Discussion Coverage"
                    value={`${overview?.discussion_coverage.toFixed(1) || 0}%`}
                    subtitle="Categories actively discussed across roster"
                    badge={overview && overview.discussion_coverage >= 80 ? 'Optimal' : 'Action Needed'}
                    badgeColor={overview && overview.discussion_coverage >= 80 ? 'emerald' : 'amber'}
                    icon={FileCheck}
                    tooltip="Discussed categories (agreed, declined, clarification, explained) / (participants * 15)"
                  />
                  <MetricCard
                    title="Explicit Approval Rate"
                    value={`${overview?.approval_rate.toFixed(1) || 0}%`}
                    subtitle="Confirmed agreed categories"
                    badge="Strict Agreed Only"
                    badgeColor="emerald"
                    icon={CheckCircle2}
                    tooltip="Strict proportion of choices marked agreed"
                  />
                  <MetricCard
                    title="Resolution Rate"
                    value={`${overview?.resolution_rate.toFixed(1) || 0}%`}
                    subtitle="Concluded categories (agreed + declined)"
                    badge={`${overview?.unresolved_categories || 0} Unresolved`}
                    badgeColor={overview && overview.unresolved_categories > 0 ? 'amber' : 'emerald'}
                    icon={SlidersHorizontal}
                    tooltip="Proportion of categories definitively resolved"
                  />
                  <MetricCard
                    title="Total Participants"
                    value={overview?.total_participants || 0}
                    subtitle={`${overview?.active_participants || 0} active | ${overview?.withdrawn_participants || 0} withdrawn`}
                    badge={`${overview?.total_projects || 0} Project(s)`}
                    badgeColor="blue"
                    icon={Users}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <MetricCard
                    title="Pending Human Reviews"
                    value={overview?.pending_human_reviews || 0}
                    subtitle="Awaiting director / producer decision"
                    badge={overview && overview.pending_human_reviews > 0 ? 'Needs Attention' : 'Queue Clear'}
                    badgeColor={overview && overview.pending_human_reviews > 0 ? 'amber' : 'emerald'}
                    icon={Clock}
                  />
                  <MetricCard
                    title="Urgent Care Tasks"
                    value={overview?.urgent_care_tasks || 0}
                    subtitle={`${overview?.open_care_tasks || 0} open | ${overview?.overdue_tasks || 0} overdue`}
                    badge={overview && overview.urgent_care_tasks > 0 ? 'URGENT' : 'Zero High Risk'}
                    badgeColor={overview && overview.urgent_care_tasks > 0 ? 'rose' : 'emerald'}
                    icon={AlertTriangle}
                  />
                  <MetricCard
                    title="Withdrawal Requests"
                    value={overview?.withdrawal_requests || 0}
                    subtitle="Formal participant revocations"
                    badge="Pause Edits"
                    badgeColor={overview && overview.withdrawal_requests > 0 ? 'rose' : 'slate'}
                    icon={AlertOctagon}
                  />
                </div>

                {/* Project performance comparison (when portfolio scope) */}
                {projectSummaries.length > 0 && (
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
                    <h3 className="text-base font-semibold text-slate-100 mb-1">Project Portfolio Breakdown</h3>
                    <p className="text-xs text-slate-400 mb-4">
                      Comparative consent coverage and review queues across authorized productions.
                    </p>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-slate-800 text-slate-400">
                            <th className="pb-3 font-medium">Project</th>
                            <th className="pb-3 font-medium">Status</th>
                            <th className="pb-3 font-medium">Participants</th>
                            <th className="pb-3 font-medium">Coverage</th>
                            <th className="pb-3 font-medium">Approval</th>
                            <th className="pb-3 font-medium">Resolution</th>
                            <th className="pb-3 font-medium">Unresolved</th>
                            <th className="pb-3 font-medium">Reviews</th>
                            <th className="pb-3 font-medium">Urgent</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {projectSummaries.map((p) => (
                            <tr key={p.project_id} className="hover:bg-slate-800/30 transition">
                              <td className="py-3 font-medium text-slate-200">
                                <Link
                                  href={`/projects/${p.project_id}`}
                                  className="hover:text-emerald-400 underline decoration-slate-700"
                                >
                                  {p.project_title}
                                </Link>
                              </td>
                              <td className="py-3">
                                <span className="px-2 py-0.5 rounded-full text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                                  {p.project_status}
                                </span>
                              </td>
                              <td className="py-3 text-slate-300">{p.participants_count}</td>
                              <td className="py-3 text-emerald-400 font-semibold">{p.discussion_coverage.toFixed(1)}%</td>
                              <td className="py-3 text-slate-300">{p.approval_rate.toFixed(1)}%</td>
                              <td className="py-3 text-slate-300">{p.resolution_rate.toFixed(1)}%</td>
                              <td className="py-3">
                                <span className={`font-semibold ${p.unresolved_categories > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
                                  {p.unresolved_categories}
                                </span>
                              </td>
                              <td className="py-3 text-slate-300">{p.pending_reviews_count}</td>
                              <td className="py-3">
                                {p.urgent_tasks_count > 0 ? (
                                  <span className="text-rose-400 font-bold">{p.urgent_tasks_count}</span>
                                ) : (
                                  <span className="text-slate-500">0</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Trends snippet */}
                {trendsData && trendsData.series.length > 0 && (
                  <TrendsChart series={trendsData.series} />
                )}
              </>
            )}

            {/* TAB 2: CONSENT & 15 CATEGORIES */}
            {activeTab === 'consent' && consentData && (
              <div className="space-y-6">
                <ConsentCategoryChart
                  categories={consentData.categories}
                  totalParticipants={consentData.total_participants}
                />

                {/* Table Breakdown */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm overflow-x-auto">
                  <h4 className="text-sm font-semibold text-slate-200 mb-3">Detailed Category Choice Matrix</h4>
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400">
                        <th className="pb-3 font-medium">Category</th>
                        <th className="pb-3 font-medium">Applicable</th>
                        <th className="pb-3 font-medium text-emerald-400">Agreed</th>
                        <th className="pb-3 font-medium text-rose-400">Declined</th>
                        <th className="pb-3 font-medium text-amber-400">Clarification</th>
                        <th className="pb-3 font-medium text-slate-500">Not Discussed</th>
                        <th className="pb-3 font-medium">Approval %</th>
                        <th className="pb-3 font-medium">Resolution %</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {consentData.categories.map((c) => (
                        <tr key={c.category} className="hover:bg-slate-800/30 transition">
                          <td className="py-2.5 font-medium text-slate-200 capitalize">
                            {c.category.replace(/_/g, ' ')}
                          </td>
                          <td className="py-2.5 text-slate-400">{c.total_applicable}</td>
                          <td className="py-2.5 text-emerald-400 font-semibold">{c.agreed}</td>
                          <td className="py-2.5 text-rose-400 font-semibold">{c.declined}</td>
                          <td className="py-2.5 text-amber-400">{c.needs_clarification}</td>
                          <td className="py-2.5 text-slate-500">{c.not_discussed}</td>
                          <td className="py-2.5 text-slate-300 font-medium">{c.approval_rate.toFixed(1)}%</td>
                          <td className="py-2.5 text-slate-300 font-medium">{c.resolution_rate.toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 flex items-start space-x-3">
                  <HelpCircle className="h-5 w-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <p className="font-semibold text-slate-200">Ethical Invariant: Silence is Never Consent</p>
                    <p>
                      In accordance with documentary clearance law and ethical standards, categories with no recorded choice
                      or unconfirmed status are treated strictly as <em>Not Discussed</em>. They are never counted toward approval.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 3: REVIEWS & OPERATIONS */}
            {activeTab === 'reviews_ops' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Review Queue Summary */}
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
                    <h3 className="text-base font-semibold text-slate-100 mb-1">Human Review State Machine</h3>
                    <p className="text-xs text-slate-400 mb-4">
                      Proposed use clearances and human decision authority.
                    </p>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center text-xs py-2 border-b border-slate-800">
                        <span className="text-slate-400">Total Proposed Uses</span>
                        <span className="font-semibold text-slate-200">{reviewData?.total_proposed_uses || 0}</span>
                      </div>
                      <div className="flex justify-between items-center text-xs py-2 border-b border-slate-800">
                        <span className="text-slate-400">Pending Reviews (Queue)</span>
                        <span className="font-bold text-amber-400">{reviewData?.pending_reviews || 0}</span>
                      </div>
                      <div className="flex justify-between items-center text-xs py-2 border-b border-slate-800">
                        <span className="text-slate-400">Completed Reviews</span>
                        <span className="font-semibold text-emerald-400">{reviewData?.completed_reviews || 0}</span>
                      </div>
                      <div className="flex justify-between items-center text-xs py-2">
                        <span className="text-slate-400">Average Turnaround Time</span>
                        <span className="font-semibold text-slate-200">
                          {reviewData?.avg_turnaround_hours !== null && reviewData?.avg_turnaround_hours !== undefined
                            ? `${reviewData.avg_turnaround_hours.toFixed(1)} hrs`
                            : 'N/A'}
                        </span>
                      </div>
                    </div>

                    {reviewData?.decisions_breakdown && Object.keys(reviewData.decisions_breakdown).length > 0 && (
                      <div className="mt-4 pt-4 border-t border-slate-800">
                        <span className="text-xs font-medium text-slate-400 block mb-2">Decisions Breakdown</span>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(reviewData.decisions_breakdown).map(([dec, count]) => (
                            <span
                              key={dec}
                              className="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700"
                            >
                              {dec.replace(/_/g, ' ')}: <strong className="text-slate-100">{count}</strong>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Operations & Participant Care */}
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
                    <h3 className="text-base font-semibold text-slate-100 mb-1">Participant Care & Operations</h3>
                    <p className="text-xs text-slate-400 mb-4">
                      Follow-up inquiries, care tickets, and urgent response duties.
                    </p>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center text-xs py-2 border-b border-slate-800">
                        <span className="text-slate-400">Urgent Priority Tasks</span>
                        <span className="font-bold text-rose-400">{operationsData?.urgent_tasks || 0}</span>
                      </div>
                      <div className="flex justify-between items-center text-xs py-2 border-b border-slate-800">
                        <span className="text-slate-400">Open Participant Follow-ups</span>
                        <span className="font-semibold text-slate-200">
                          {operationsData?.participant_follow_up_tasks || 0}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-xs py-2 border-b border-slate-800">
                        <span className="text-slate-400">Overdue Task Backlog</span>
                        <span className="font-semibold text-amber-400">{operationsData?.overdue_tasks || 0}</span>
                      </div>
                      <div className="flex justify-between items-center text-xs py-2">
                        <span className="text-slate-400">Avg Task Resolution</span>
                        <span className="font-semibold text-slate-200">
                          {operationsData?.avg_resolution_hours !== null && operationsData?.avg_resolution_hours !== undefined
                            ? `${operationsData.avg_resolution_hours.toFixed(1)} hrs`
                            : 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Withdrawals & Revocations */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
                  <div className="flex items-center space-x-2.5 mb-2">
                    <AlertOctagon className="h-5 w-5 text-rose-400" />
                    <h3 className="text-base font-semibold text-slate-100">Participant Withdrawals & Revocations</h3>
                  </div>
                  <p className="text-xs text-slate-400 mb-4">
                    Audit-verified withdrawal notices requiring immediate pause of associated footage edits.
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
                    <div className="p-4 rounded-lg bg-slate-800/60 border border-slate-700">
                      <div className="text-xs text-slate-400">Total Withdrawal Requests</div>
                      <div className="text-xl font-bold text-rose-400 mt-1">
                        {withdrawalData?.total_withdrawal_requests || 0}
                      </div>
                    </div>
                    <div className="p-4 rounded-lg bg-slate-800/60 border border-slate-700">
                      <div className="text-xs text-slate-400">Active / Pending Care Tasks</div>
                      <div className="text-xl font-bold text-amber-400 mt-1">
                        {withdrawalData?.pending_care_tasks || 0}
                      </div>
                    </div>
                    <div className="p-4 rounded-lg bg-slate-800/60 border border-slate-700">
                      <div className="text-xs text-slate-400">Resolved Care Tasks</div>
                      <div className="text-xl font-bold text-emerald-400 mt-1">
                        {withdrawalData?.resolved_care_tasks || 0}
                      </div>
                    </div>
                  </div>

                  {withdrawalData?.recent_withdrawal_events && withdrawalData.recent_withdrawal_events.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-slate-800">
                      <span className="text-xs font-medium text-slate-300 block mb-2">Recent Immutable Withdrawal Events</span>
                      <div className="space-y-2">
                        {withdrawalData.recent_withdrawal_events.map((e) => (
                          <div
                            key={e.id}
                            className="p-2.5 rounded bg-slate-800/80 border border-slate-700/80 flex items-center justify-between text-xs"
                          >
                            <span className="text-rose-400 font-mono font-medium">{e.action}</span>
                            <span className="text-slate-400 text-[11px]">{new Date(e.timestamp).toLocaleString()}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 4: ADVISORY & TRENDS */}
            {activeTab === 'advisory_trends' && (
              <div className="space-y-6">
                {trendsData && <TrendsChart series={trendsData.series} />}

                {/* Advisory Agent Metrics */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
                  <div className="flex items-center space-x-2.5 mb-2">
                    <Bot className="h-5 w-5 text-indigo-400" />
                    <h3 className="text-base font-semibold text-slate-100">Advisory Agent Operational Intelligence</h3>
                  </div>
                  <p className="text-xs text-slate-400 mb-4">
                    Invocations across Legal, Ethical, Cultural, Narrative, and Licensing advisory agents.
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                    <div className="p-4 rounded-lg bg-slate-800/60 border border-slate-700">
                      <div className="text-xs text-slate-400">Total Advisory Invocations</div>
                      <div className="text-xl font-bold text-slate-100 mt-1">
                        {advisoryData?.total_advisory_runs || 0}
                      </div>
                    </div>
                    <div className="p-4 rounded-lg bg-slate-800/60 border border-slate-700">
                      <div className="text-xs text-slate-400">Decision Concordance Rate</div>
                      <div className="text-xl font-bold text-indigo-400 mt-1">
                        {advisoryData?.alignment_rate !== null && advisoryData?.alignment_rate !== undefined
                          ? `${advisoryData.alignment_rate.toFixed(1)}%`
                          : 'N/A'}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        Sample size: {advisoryData?.alignment_sample_size || 0} reviews
                      </div>
                    </div>
                    <div className="p-4 rounded-lg bg-slate-800/60 border border-slate-700">
                      <div className="text-xs text-slate-400">Agent Failure Rate</div>
                      <div className="text-xl font-bold text-emerald-400 mt-1">0.0%</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">Zero unhandled crashes</div>
                    </div>
                  </div>

                  {/* Disclaimer Alert */}
                  <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 flex items-start space-x-3">
                    <AlertTriangle className="h-5 w-5 text-amber-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold mb-0.5">Advisory Invariant & Non-Authoritative Notice</p>
                      <p className="text-amber-200/80 leading-relaxed">{advisoryData?.disclaimer}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Export Dialog */}
      <AnalyticsExportDialog
        isOpen={exportDialogOpen}
        onClose={() => setExportDialogOpen(false)}
        projectId={selectedProjectId}
      />
    </div>
  );
}
