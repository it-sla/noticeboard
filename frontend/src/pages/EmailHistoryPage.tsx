import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router";
import { btnSecondaryCls, Button, EmptyState, ErrorState, inputCls, PageHeader, Pagination, Spinner, StatusBadge, Table, Td, useToast } from "../components/ui";
import { api, errorMessage, qs } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { Job, Page } from "../types";

const STATUSES = ["pending", "sending", "accepted", "failed", "unknown", "dry_run"];

export function EmailHistoryPage() {
  const [sp] = useSearchParams();
  const qc = useQueryClient();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState(sp.get("status") ?? "");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(1);
  const filters = { search, status, date_from: from, date_to: to };
  const q = useQuery({ queryKey: ["jobs", filters, page], queryFn: () => api.get<Page<Job>>("/email/jobs", { ...filters, page }) });
  const retry = useMutation({
    mutationFn: ({ id, unknown }: { id: number; unknown: boolean }) => api.post(`/email/jobs/${id}/retry`, { include_unknown: unknown }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["jobs"] }); toast("success", "Job requeued"); },
    onError: (e) => toast("error", errorMessage(e)),
  });
  const reset = (set: (v: string) => void) => (v: string) => { set(v); setPage(1); };
  return (
    <>
      <PageHeader title="Email History" subtitle="One row per recipient. Accepted by SMTP is not confirmed inbox delivery."
        actions={<a className={btnSecondaryCls} href={`/api/email/jobs/export${qs(filters)}`}>Export CSV</a>} />
      <div className="mb-4 flex flex-wrap gap-2">
        <input aria-label="Search recipient" placeholder="Search recipient…" className={`${inputCls} max-w-xs`} value={search} onChange={(e) => reset(setSearch)(e.target.value)} />
        <select aria-label="Status" className={`${inputCls} w-auto`} value={status} onChange={(e) => reset(setStatus)(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <input aria-label="From date" type="date" className={`${inputCls} w-auto`} value={from} onChange={(e) => reset(setFrom)(e.target.value)} />
        <input aria-label="To date" type="date" className={`${inputCls} w-auto`} value={to} onChange={(e) => reset(setTo)(e.target.value)} />
      </div>
      {q.isLoading ? <Spinner /> : q.error ? <ErrorState error={q.error} retry={() => q.refetch()} /> : q.data!.items.length === 0 ? (
        <EmptyState title="No email records" hint="Records appear once a notice is published." />
      ) : (
        <>
          <Table head={["Notice", "Recipient", "Status", "Attempts", "Last attempt", "SMTP accepted", "Error", ""]}>
            {q.data!.items.map((j) => (
              <tr key={j.id}>
                <Td>{j.notice_title}</Td>
                <Td>{j.recipient_name}<div className="text-xs text-[#6e6e73]">{j.recipient_email}</div></Td>
                <Td><StatusBadge status={j.status} /></Td>
                <Td>{j.attempt_count}</Td>
                <Td>{formatDateTime(j.last_attempt_at)}</Td>
                <Td>{formatDateTime(j.accepted_at)}</Td>
                <Td className="max-w-xs break-words text-xs text-[#6e6e73]">{j.error}</Td>
                <Td>
                  {j.status === "failed" && <Button variant="ghost" onClick={() => retry.mutate({ id: j.id, unknown: false })}>Retry</Button>}
                  {j.status === "unknown" && (
                    <Button variant="ghost" title="The message may already have been accepted" onClick={() => window.confirm("This message may already have been delivered. Retrying could send a duplicate. Retry anyway?") && retry.mutate({ id: j.id, unknown: true })}>
                      Retry…
                    </Button>
                  )}
                </Td>
              </tr>
            ))}
          </Table>
          <Pagination page={page} pageSize={q.data!.page_size} total={q.data!.total} onPage={setPage} />
        </>
      )}
    </>
  );
}
