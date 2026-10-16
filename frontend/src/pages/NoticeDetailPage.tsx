import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useAuth } from "../app/auth";
import { btnSecondaryCls, Button, Card, ConfirmDialog, EmptyState, ErrorState, PageHeader, Pagination, Spinner, StatusBadge, Table, Td, useToast } from "../components/ui";
import { api, errorMessage } from "../lib/api";
import { formatBytes, formatDateTime } from "../lib/format";
import type { Job, Notice, Page } from "../types";

interface Sending {
  notice_status: string;
  total: number;
  counts: Record<string, number>;
  complete: boolean;
}
interface Version {
  id: number;
  version_no: number;
  subject: string;
  created_at: string;
}

export function NoticeDetailPage() {
  const { id } = useParams();
  const { can } = useAuth();
  const qc = useQueryClient();
  const nav = useNavigate();
  const toast = useToast();
  const [cancelOpen, setCancelOpen] = useState(false);
  const [page, setPage] = useState(1);
  const notice = useQuery({ queryKey: ["notice", id], queryFn: () => api.get<Notice>(`/notices/${id}`) });
  const n = notice.data;
  const sent = n && ["queued", "published"].includes(n.status);
  const sending = useQuery({
    queryKey: ["sending", id],
    enabled: !!sent && can("NOTICE_EDITOR"),
    queryFn: () => api.get<Sending>(`/notices/${id}/sending`),
    refetchInterval: (q) => (q.state.data?.complete ? false : 3000),
  });
  const versions = useQuery({ queryKey: ["versions", id], enabled: !!sent, queryFn: () => api.get<Version[]>(`/notices/${id}/versions`) });
  const log = useQuery({
    queryKey: ["recipients", id, page, sending.data?.complete],
    enabled: !!sent && can("ADMIN"),
    queryFn: () => api.get<Page<Job>>(`/notices/${id}/recipients`, { page }),
    refetchInterval: sending.data && !sending.data.complete ? 3000 : false,
  });

  const act = useMutation({
    mutationFn: (fn: () => Promise<unknown>) => fn(),
    onSuccess: () => {
      qc.invalidateQueries();
    },
    onError: (e) => toast("error", errorMessage(e)),
  });

  if (notice.isLoading) return <Spinner />;
  if (notice.error || !n) return <ErrorState error={notice.error} />;
  const failed = (sending.data?.counts.failed ?? 0) + 0;
  return (
    <>
      <PageHeader
        title={n.title}
        subtitle={`${n.category} · ${n.priority} priority`}
        actions={
          <>
            <StatusBadge status={n.status} />
            {n.status === "draft" && can("NOTICE_EDITOR") && (
              <Link className={btnSecondaryCls} to={`/notices/${n.id}/edit`}>Edit</Link>
            )}
            {["draft", "scheduled"].includes(n.status) && can("ADMIN") && (
              <Button variant="danger" onClick={() => setCancelOpen(true)}>Cancel notice</Button>
            )}
            {!["queued", "scheduled"].includes(n.status) && can("ADMIN") && (
              <Button variant="secondary" onClick={() => act.mutate(() => api.post(`/notices/${n.id}/archive`, {}, n.archived_at ? { undo: true } : undefined))}>
                {n.archived_at ? "Unarchive" : "Archive"}
              </Button>
            )}
            {can("NOTICE_EDITOR") && (
              <Button variant="secondary" onClick={() => act.mutate(async () => { const d = await api.post<Notice>(`/notices/${n.id}/duplicate`); nav(`/notices/${d.id}/edit`); })}>
                Duplicate
              </Button>
            )}
          </>
        }
      />
      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2" title="Content">
          <div className="prose-notice text-sm" dangerouslySetInnerHTML={{ __html: n.body_html }} />
          {n.attachments.filter((a) => a.content_type.startsWith("image/")).map((a) => (
            <img key={a.id} src={`/api/attachments/${a.id}/download`} alt={a.original_filename} className="mt-3 max-h-[32rem] w-full rounded border border-hairline object-contain" />
          ))}
          {n.attachments.some((a) => !a.content_type.startsWith("image/")) && (
            <ul className="mt-4 space-y-1 border-t border-[#f0f0f0] pt-3 text-sm">
              {n.attachments.filter((a) => !a.content_type.startsWith("image/")).map((a) => (
                <li key={a.id}>
                  <a className="text-brand-700 underline" href={`/api/attachments/${a.id}/download`}>{a.original_filename}</a>{" "}
                  <span className="text-[#86868b]">({formatBytes(a.size_bytes)})</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Details">
          <dl className="grid grid-cols-[6rem_1fr] gap-y-1 text-sm">
            <dt className="text-[#6e6e73]">Author</dt><dd>{n.created_by_name}</dd>
            <dt className="text-[#6e6e73]">Created</dt><dd>{formatDateTime(n.created_at)}</dd>
            <dt className="text-[#6e6e73]">Scheduled</dt><dd>{formatDateTime(n.scheduled_at)}</dd>
            <dt className="text-[#6e6e73]">Published</dt><dd>{formatDateTime(n.published_at)}</dd>
            <dt className="text-[#6e6e73]">Audience</dt><dd>{n.recipient_mode}</dd>
          </dl>
          {versions.data && versions.data.length > 0 && (
            <p className="mt-3 text-xs text-[#6e6e73]">Approved version {versions.data[0].version_no} is stored unchanged for audit.</p>
          )}
        </Card>
        {sending.data && (
          <Card title="Sending progress" className="xl:col-span-3">
            <div className="mb-2 flex flex-wrap gap-3 text-sm">
              {Object.entries(sending.data.counts).map(([k, v]) => (
                <span key={k}><StatusBadge status={k} /> {v}</span>
              ))}
              <span className="text-[#6e6e73]">of {sending.data.total}</span>
              {sending.data.complete && <strong className="text-green-700">Complete</strong>}
            </div>
            <progress className="h-2 w-full" max={sending.data.total} value={sending.data.total - (sending.data.counts.pending ?? 0) - (sending.data.counts.sending ?? 0)} aria-label="Sending progress" />
            <p className="mt-2 text-xs text-[#6e6e73]">&ldquo;Accepted by SMTP&rdquo; means the mail server took the message; it is not confirmation of inbox delivery.</p>
            {can("ADMIN") && (failed > 0 || (sending.data.counts.unknown ?? 0) > 0) && (
              <div className="mt-3 flex flex-wrap gap-2">
                {failed > 0 && <Button variant="secondary" onClick={() => act.mutate(() => api.post(`/email/notices/${n.id}/retry-failed`, {}))}>Retry failed ({failed})</Button>}
              </div>
            )}
          </Card>
        )}
        {can("ADMIN") && sent && (
          <div className="xl:col-span-3">
            <h2 className="mb-2 text-sm font-semibold">Recipients</h2>
            {log.data && log.data.items.length === 0 ? <EmptyState title="No recipients" /> : (
              <>
                <Table head={["Recipient", "Email", "Status", "Attempts", "Last attempt", "Error"]}>
                  {(log.data?.items ?? []).map((j) => (
                    <tr key={j.id}>
                      <Td>{j.recipient_name}</Td><Td>{j.recipient_email}</Td><Td><StatusBadge status={j.status} /></Td>
                      <Td>{j.attempt_count}</Td><Td>{formatDateTime(j.last_attempt_at)}</Td><Td className="max-w-xs break-words text-xs text-[#6e6e73]">{j.error}</Td>
                    </tr>
                  ))}
                </Table>
                {log.data && <Pagination page={page} pageSize={log.data.page_size} total={log.data.total} onPage={setPage} />}
              </>
            )}
          </div>
        )}
      </div>
      <ConfirmDialog
        open={cancelOpen}
        danger
        title="Cancel this notice?"
        message="A cancelled notice will not be sent. This cannot be undone."
        confirmLabel="Cancel notice"
        onClose={() => setCancelOpen(false)}
        onConfirm={() => { setCancelOpen(false); act.mutate(() => api.post(`/notices/${n.id}/cancel`)); }}
      />
    </>
  );
}
