const TZ = "Asia/Kathmandu";

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: TZ,
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

/** `datetime-local` value (wall clock in Nepal) -> ISO string with the +05:45 offset. */
export function nepalLocalToIso(local: string): string {
  return `${local}:00+05:45`;
}

export function formatBytes(n: number): string {
  return n < 1024 * 1024 ? `${Math.max(1, Math.round(n / 1024))} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }).format(
    new Date(Date.UTC(y, m - 1, d)),
  );
}

export function addMonths(iso: string, months: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const t = new Date(Date.UTC(y, m - 1 + months, 1));
  const last = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth() + 1, 0)).getUTCDate();
  t.setUTCDate(Math.min(d, last));
  return t.toISOString().slice(0, 10);
}

export function daysLabel(days: number): string {
  if (days < 0) return `${-days} day${days === -1 ? "" : "s"} overdue`;
  if (days === 0) return "today";
  return `in ${days} day${days === 1 ? "" : "s"}`;
}

export const STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  scheduled: "Scheduled",
  queued: "Sending",
  published: "Published",
  cancelled: "Cancelled",
  pending: "Pending",
  sending: "Sending",
  accepted: "Accepted by SMTP",
  failed: "Failed",
  unknown: "Unknown outcome",
  dry_run: "Dry run",
  overdue: "Overdue",
  due7: "Due in 7 days or less",
  due30: "Due in 30 days or less",
  due60: "Due in 60 days or less",
  ok: "OK",
};
