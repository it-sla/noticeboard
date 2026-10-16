import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { Card, EmptyState, ErrorState, PageHeader, Spinner, StatusBadge } from "../components/ui";
import { api } from "../lib/api";
import { daysLabel, formatDate, formatDateTime } from "../lib/format";
import type { ExpiryAlerts } from "../types";

interface Summary {
  active_employees: number;
  published_notices: number;
  scheduled_notices: number;
  pending_emails: number;
  smtp_accepted_emails: number;
  failed_emails: number;
  unknown_emails: number;
  dry_run_emails: number;
  broadcast_enabled: boolean;
  email_mode: string;
}
interface NoticeBrief {
  id: number;
  title: string;
  status: string;
  published_at: string | null;
  scheduled_at: string | null;
  created_at: string;
}
interface Activity {
  recent_notices: NoticeBrief[];
  upcoming_scheduled: NoticeBrief[];
  recent_sending: { at: string; outcome: string; notice: string; recipient_email: string }[];
  failed_warnings: { job_id: number; notice: string; recipient_email: string; status: string; error: string | null }[];
}

export function DashboardPage() {
  const summary = useQuery({ queryKey: ["dash-summary"], queryFn: () => api.get<Summary>("/dashboard/summary"), refetchInterval: 5000 });
  const activity = useQuery({ queryKey: ["dash-activity"], queryFn: () => api.get<Activity>("/dashboard/activity"), refetchInterval: 5000 });
  const expiry = useQuery({ queryKey: ["expiry-alerts"], queryFn: () => api.get<ExpiryAlerts>("/expiry/alerts"), refetchInterval: 60_000 });
  if (summary.isLoading || activity.isLoading) return <Spinner />;
  if (summary.error || !summary.data) return <ErrorState error={summary.error} retry={() => summary.refetch()} />;
  const s = summary.data;
  const a = activity.data;
  const cards: [string, number, string?][] = [
    ["Active employees", s.active_employees],
    ["Published notices", s.published_notices],
    ["Scheduled notices", s.scheduled_notices],
    ["Pending emails", s.pending_emails],
    ["SMTP-accepted emails", s.smtp_accepted_emails],
    ["Failed emails", s.failed_emails, s.failed_emails ? "text-red-600" : undefined],
  ];
  return (
    <>
      <PageHeader title="Dashboard" subtitle="Live figures from the database." />
      {(!s.broadcast_enabled || s.email_mode === "dry_run") && (
        <div role="status" className="mb-4 rounded-[11px] border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          {!s.broadcast_enabled && <p>Email broadcasting is <strong>disabled</strong>. A Super Admin can enable it in Settings.</p>}
          {s.email_mode === "dry_run" && <p>Email mode is <strong>dry run</strong>: no real email is sent.</p>}
        </div>
      )}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
        {cards.map(([label, n, tone]) => (
          <div key={label} className="rounded-[18px] border border-hairline bg-white p-4 ">
            <div className={`text-2xl font-semibold ${tone ?? "text-ink"}`}>{n}</div>
            <div className="mt-1 text-xs text-[#6e6e73]">{label}</div>
          </div>
        ))}
      </div>
      {(s.unknown_emails > 0 || s.dry_run_emails > 0) && (
        <p className="mt-2 text-xs text-[#6e6e73]">
          Also: {s.unknown_emails} unknown outcome (needs reconciliation), {s.dry_run_emails} dry-run.
          SMTP acceptance is not confirmed inbox delivery.
        </p>
      )}
      {a && (
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {expiry.data && expiry.data.count > 0 && (
            <Card title={`Expiring soon (${expiry.data.count})`} className="lg:col-span-2">
              <ul className="divide-y divide-[#f0f0f0] text-sm">
                {expiry.data.items.map((i) => (
                  <li key={i.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                    <span><span className="font-semibold text-ink">{i.subject}</span> · {i.item_type}</span>
                    <span className={i.days_left < 0 ? "text-[#d70015]" : "text-[#333333]"}>{formatDate(i.expires_on)} · {daysLabel(i.days_left)}</span>
                  </li>
                ))}
              </ul>
              <Link to="/expiry" className="mt-2 inline-block text-sm text-brand-700 underline">Open Expiry Tracker</Link>
            </Card>
          )}
          {a.failed_warnings.length > 0 && (
            <Card title="Failed email warnings" className="border-red-200 lg:col-span-2">
              <ul className="space-y-1 text-sm">
                {a.failed_warnings.map((f) => (
                  <li key={f.job_id}>
                    <StatusBadge status={f.status} /> {f.recipient_email} — {f.notice}
                    {f.error && <span className="text-[#6e6e73]"> ({f.error})</span>}
                  </li>
                ))}
              </ul>
              <Link to="/email-history?status=failed" className="mt-2 inline-block text-sm text-brand-700 underline">
                Open email history
              </Link>
            </Card>
          )}
          <Card title="Recent notices">
            {a.recent_notices.length === 0 ? (
              <EmptyState title="No notices yet" />
            ) : (
              <ul className="divide-y divide-[#f0f0f0] text-sm">
                {a.recent_notices.map((n) => (
                  <li key={n.id} className="flex items-center justify-between gap-2 py-2">
                    <Link to={`/notices/${n.id}`} className="font-semibold text-brand-700 hover:underline">{n.title}</Link>
                    <StatusBadge status={n.status} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="Upcoming scheduled notices">
            {a.upcoming_scheduled.length === 0 ? (
              <EmptyState title="Nothing scheduled" />
            ) : (
              <ul className="divide-y divide-[#f0f0f0] text-sm">
                {a.upcoming_scheduled.map((n) => (
                  <li key={n.id} className="flex justify-between gap-2 py-2">
                    <Link to={`/notices/${n.id}`} className="font-semibold text-brand-700 hover:underline">{n.title}</Link>
                    <span className="text-[#6e6e73]">{formatDateTime(n.scheduled_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="Recent sending activity" className="lg:col-span-2">
            {a.recent_sending.length === 0 ? (
              <EmptyState title="No sending activity yet" />
            ) : (
              <ul className="divide-y divide-[#f0f0f0] text-sm">
                {a.recent_sending.map((r, i) => (
                  <li key={i} className="flex flex-wrap items-center gap-2 py-2">
                    <StatusBadge status={r.outcome.endsWith("failure") ? "failed" : r.outcome} />
                    <span>{r.recipient_email}</span>
                    <span className="text-[#6e6e73]">— {r.notice}</span>
                    <span className="ml-auto text-[#86868b]">{formatDateTime(r.at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}
    </>
  );
}
