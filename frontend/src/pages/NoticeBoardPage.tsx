import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { useAuth } from "../app/auth";
import { btnPrimaryCls, Button, EmptyState, ErrorState, inputCls, PageHeader, Pagination, Spinner, StatusBadge, Table, Td, useToast } from "../components/ui";
import { api, errorMessage } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { CATEGORIES, type NoticeListItem, type Page } from "../types";

export function NoticeBoardPage() {
  const { can } = useAuth();
  const nav = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [archived, setArchived] = useState(false);
  const [page, setPage] = useState(1);
  const q = useQuery({
    queryKey: ["notices", search, status, category, archived, page],
    queryFn: () => api.get<Page<NoticeListItem>>("/notices", { search, status, category, archived, page }),
  });
  const dup = useMutation({
    mutationFn: (id: number) => api.post<{ id: number }>(`/notices/${id}/duplicate`),
    onSuccess: (n) => {
      qc.invalidateQueries({ queryKey: ["notices"] });
      toast("success", "Notice duplicated as a draft");
      nav(`/notices/${n.id}/edit`);
    },
    onError: (e) => toast("error", errorMessage(e)),
  });
  const reset = <T,>(set: (v: T) => void) => (v: T) => {
    set(v);
    setPage(1);
  };
  return (
    <>
      <PageHeader
        title="Notice Board"
        subtitle={can("NOTICE_EDITOR") ? "All notices and their status." : "Published notices."}
        actions={can("NOTICE_EDITOR") && <Link to="/notices/new/edit" className={btnPrimaryCls}>Create notice</Link>}
      />
      <div className="mb-4 flex flex-wrap gap-2">
        <input aria-label="Search notices" placeholder="Search title…" className={`${inputCls} max-w-xs`} value={search} onChange={(e) => reset(setSearch)(e.target.value)} />
        {can("NOTICE_EDITOR") && (
          <select aria-label="Status" className={`${inputCls} w-auto`} value={status} onChange={(e) => reset(setStatus)(e.target.value)}>
            <option value="">All statuses</option>
            {["draft", "scheduled", "queued", "published", "cancelled"].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        )}
        <select aria-label="Category" className={`${inputCls} w-auto`} value={category} onChange={(e) => reset(setCategory)(e.target.value)}>
          <option value="">All categories</option>
          {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={archived} onChange={(e) => reset(setArchived)(e.target.checked)} /> Archived
        </label>
      </div>
      {q.isLoading ? (
        <Spinner />
      ) : q.error ? (
        <ErrorState error={q.error} retry={() => q.refetch()} />
      ) : q.data!.items.length === 0 ? (
        <EmptyState title="No notices found" hint="Try different filters." />
      ) : (
        <>
          <Table head={["Title", "Category", "Status", "Author", "Date", ""]}>
            {q.data!.items.map((n) => (
              <tr key={n.id}>
                <Td><Link className="font-semibold text-brand-700 hover:underline" to={`/notices/${n.id}`}>{n.title}</Link></Td>
                <Td>{n.category}</Td>
                <Td><StatusBadge status={n.status} /></Td>
                <Td>{n.created_by_name}</Td>
                <Td>{formatDateTime(n.published_at ?? n.scheduled_at ?? n.created_at)}</Td>
                <Td>{can("NOTICE_EDITOR") && <Button variant="ghost" onClick={() => dup.mutate(n.id)} disabled={dup.isPending}>Duplicate</Button>}</Td>
              </tr>
            ))}
          </Table>
          <Pagination page={page} pageSize={q.data!.page_size} total={q.data!.total} onPage={setPage} />
        </>
      )}
    </>
  );
}
