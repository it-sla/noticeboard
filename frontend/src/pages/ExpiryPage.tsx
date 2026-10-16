import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { btnSecondaryCls, Button, ConfirmDialog, Dialog, EmptyState, ErrorState, Field, inputCls, PageHeader, Pagination, Spinner, StatusBadge, Table, Td, useToast } from "../components/ui";
import { api, errorMessage, qs } from "../lib/api";
import { addMonths, daysLabel, formatDate } from "../lib/format";
import type { ExpiryCategory, ExpiryItem, ExpiryStatus, ExpirySummary, Page, Renewal } from "../types";

const CATEGORIES: { value: ExpiryCategory; label: string }[] = [
  { value: "vehicle", label: "Vehicle" },
  { value: "staff", label: "Staff / Driver" },
  { value: "company", label: "Company" },
  { value: "equipment", label: "Equipment / Other" },
];
const CAT_LABEL = Object.fromEntries(CATEGORIES.map((c) => [c.value, c.label]));
const TILES: { key: ExpiryStatus; label: string; tone: string }[] = [
  { key: "overdue", label: "Overdue", tone: "text-[#d70015]" },
  { key: "due7", label: "Within 7 days", tone: "text-[#d70015]" },
  { key: "due30", label: "Within 30 days", tone: "text-amber-700" },
  { key: "due60", label: "Within 60 days", tone: "text-ink" },
  { key: "ok", label: "OK", tone: "text-green-700" },
];
const invalidate = (qc: ReturnType<typeof useQueryClient>) => {
  for (const k of ["expiry-items", "expiry-summary", "expiry-alerts"]) qc.invalidateQueries({ queryKey: [k] });
};

interface FormState {
  category: ExpiryCategory;
  item_type: string;
  subject: string;
  reference_no: string;
  issued_on: string;
  expires_on: string;
  reminder_days: string;
  notes: string;
}
const EMPTY: FormState = { category: "vehicle", item_type: "", subject: "", reference_no: "", issued_on: "", expires_on: "", reminder_days: "60, 30, 14, 7, 1", notes: "" };

function ItemDialog({ item, onClose }: { item: ExpiryItem | "new" | null; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [f, setF] = useState<FormState>(EMPTY);
  const [err, setErr] = useState<Partial<Record<keyof FormState, string>>>({});
  const presets = useQuery({ queryKey: ["expiry-presets"], queryFn: () => api.get<Record<string, string[]>>("/expiry/presets") });
  useEffect(() => {
    if (item === null) return;
    setErr({});
    setF(
      item === "new"
        ? EMPTY
        : { category: item.category, item_type: item.item_type, subject: item.subject, reference_no: item.reference_no ?? "", issued_on: item.issued_on ?? "", expires_on: item.expires_on, reminder_days: item.reminder_days.join(", "), notes: item.notes ?? "" },
    );
  }, [item]);
  const save = useMutation({
    mutationFn: () => {
      const days = f.reminder_days.split(/[,\s]+/).filter(Boolean).map(Number);
      const body = { category: f.category, item_type: f.item_type.trim(), subject: f.subject.trim(), reference_no: f.reference_no.trim() || null, issued_on: f.issued_on || null, expires_on: f.expires_on, reminder_days: days, notes: f.notes.trim() || null };
      return item === "new" ? api.post("/expiry/items", body) : api.patch(`/expiry/items/${(item as ExpiryItem).id}`, body);
    },
    onSuccess: () => { invalidate(qc); toast("success", "Saved"); onClose(); },
    onError: (e) => toast("error", errorMessage(e)),
  });
  const submit = () => {
    const e: typeof err = {};
    if (!f.subject.trim()) e.subject = "Required";
    if (!f.item_type.trim()) e.item_type = "Required";
    if (!f.expires_on) e.expires_on = "Expiry date is required";
    const days = f.reminder_days.split(/[,\s]+/).filter(Boolean);
    if (days.some((d) => !/^\d+$/.test(d))) e.reminder_days = "Use numbers separated by commas, e.g. 60, 30, 7";
    setErr(e);
    if (Object.keys(e).length === 0) save.mutate();
  };
  const types = presets.data?.[f.category] ?? [];
  return (
    <Dialog open={item !== null} title={item === "new" ? "Add item" : "Edit item"} onClose={onClose}
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={submit} disabled={save.isPending}>Save</Button></>}>
      <form className="space-y-3" noValidate onSubmit={(e) => { e.preventDefault(); submit(); }}>
        <Field label="Category">
          {(p) => <select {...p} className={inputCls} value={f.category} onChange={(e) => setF({ ...f, category: e.target.value as ExpiryCategory })}>{CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}</select>}
        </Field>
        <Field label="Type" error={err.item_type} hint="Pick a suggestion or type your own.">
          {(p) => (<><input {...p} list="expiry-types" className={inputCls} value={f.item_type} onChange={(e) => setF({ ...f, item_type: e.target.value })} /><datalist id="expiry-types">{types.map((t) => <option key={t} value={t} />)}</datalist></>)}
        </Field>
        <Field label={f.category === "vehicle" ? "Vehicle (plate number)" : "Belongs to"} error={err.subject}>
          {(p) => <input {...p} className={inputCls} value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} />}
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Reference / number">{(p) => <input {...p} className={inputCls} value={f.reference_no} onChange={(e) => setF({ ...f, reference_no: e.target.value })} />}</Field>
          <Field label="Issued on">{(p) => <input {...p} type="date" className={inputCls} value={f.issued_on} onChange={(e) => setF({ ...f, issued_on: e.target.value })} />}</Field>
        </div>
        <Field label="Expires on" error={err.expires_on}>{(p) => <input {...p} type="date" className={inputCls} value={f.expires_on} onChange={(e) => setF({ ...f, expires_on: e.target.value })} />}</Field>
        <Field label="Remind me (days before)" error={err.reminder_days} hint="Admins get an email when a date is reached.">
          {(p) => <input {...p} className={inputCls} value={f.reminder_days} onChange={(e) => setF({ ...f, reminder_days: e.target.value })} />}
        </Field>
        <Field label="Notes">{(p) => <textarea {...p} rows={2} className={inputCls} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} />}</Field>
        <button type="submit" hidden />
      </form>
    </Dialog>
  );
}

function RenewDialog({ item, onClose }: { item: ExpiryItem | null; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [date, setDate] = useState("");
  const [cost, setCost] = useState("");
  const [note, setNote] = useState("");
  useEffect(() => { if (item) { setDate(addMonths(item.expires_on, 12)); setCost(""); setNote(""); } }, [item]);
  const renew = useMutation({
    mutationFn: () => api.post(`/expiry/items/${item!.id}/renew`, { new_expires_on: date, cost: cost || null, note: note || null }),
    onSuccess: () => { invalidate(qc); toast("success", "Renewed"); onClose(); },
    onError: (e) => toast("error", errorMessage(e)),
  });
  return (
    <Dialog open={item !== null} title="Renew" onClose={onClose}
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={() => renew.mutate()} disabled={!date || renew.isPending}>Save renewal</Button></>}>
      {item && (
        <div className="space-y-3">
          <p><strong>{item.subject}</strong> · {item.item_type}<br />Currently expires {formatDate(item.expires_on)}.</p>
          <Field label="New expiry date">{(p) => <input {...p} type="date" className={inputCls} value={date} onChange={(e) => setDate(e.target.value)} />}</Field>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setDate(addMonths(item.expires_on, 6))}>+6 months</Button>
            <Button variant="secondary" onClick={() => setDate(addMonths(item.expires_on, 12))}>+1 year</Button>
          </div>
          <Field label="Cost (optional)">{(p) => <input {...p} type="number" min="0" step="0.01" className={inputCls} value={cost} onChange={(e) => setCost(e.target.value)} />}</Field>
          <Field label="Note (optional)">{(p) => <input {...p} className={inputCls} value={note} onChange={(e) => setNote(e.target.value)} />}</Field>
        </div>
      )}
    </Dialog>
  );
}

function HistoryDialog({ item, onClose }: { item: ExpiryItem | null; onClose: () => void }) {
  const q = useQuery({ queryKey: ["expiry-history", item?.id], enabled: !!item, queryFn: () => api.get<Renewal[]>(`/expiry/items/${item!.id}/history`) });
  return (
    <Dialog open={item !== null} title={`Renewal history${item ? ` · ${item.subject}` : ""}`} onClose={onClose} footer={<Button variant="secondary" onClick={onClose}>Close</Button>}>
      {q.isLoading ? <Spinner /> : q.data && q.data.length === 0 ? <p>No renewals recorded yet.</p> : (
        <ul className="divide-y divide-[#f0f0f0]">
          {(q.data ?? []).map((r) => (
            <li key={r.id} className="py-2">
              {formatDate(r.old_expires_on)} → <strong>{formatDate(r.new_expires_on)}</strong>
              {r.cost && <span> · cost {r.cost}</span>}
              {r.note && <div className="text-[#6e6e73]">{r.note}</div>}
            </li>
          ))}
        </ul>
      )}
    </Dialog>
  );
}

export function ExpiryPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [archived, setArchived] = useState(false);
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<ExpiryItem | "new" | null>(null);
  const [renewing, setRenewing] = useState<ExpiryItem | null>(null);
  const [history, setHistory] = useState<ExpiryItem | null>(null);
  const [archiving, setArchiving] = useState<ExpiryItem | null>(null);
  const filters = { category, status, search, archived };
  const summary = useQuery({ queryKey: ["expiry-summary"], queryFn: () => api.get<ExpirySummary>("/expiry/summary") });
  const q = useQuery({ queryKey: ["expiry-items", filters, page], queryFn: () => api.get<Page<ExpiryItem>>("/expiry/items", { ...filters, page }) });
  const archive = useMutation({
    mutationFn: (i: ExpiryItem) => api.del(`/expiry/items/${i.id}`),
    onSuccess: () => { invalidate(qc); setArchiving(null); toast("success", "Archived"); },
    onError: (e) => toast("error", errorMessage(e)),
  });
  const reset = (set: (v: string) => void) => (v: string) => { set(v); setPage(1); };
  return (
    <>
      <PageHeader title="Expiry Tracker" subtitle="Vehicle papers, licences, contracts and renewals. Admins are emailed before dates arrive."
        actions={<><a className={btnSecondaryCls} href={`/api/expiry/export${qs({ category, status, search })}`}>Export CSV</a><Button onClick={() => setEditing("new")}>Add item</Button></>} />
      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-5">
        {TILES.map((t) => (
          <button key={t.key} type="button" aria-pressed={status === t.key} onClick={() => reset(setStatus)(status === t.key ? "" : t.key)}
            className={`rounded-[18px] border bg-white p-4 text-left ${status === t.key ? "border-brand-700" : "border-hairline"}`}>
            <div className={`text-2xl font-semibold ${t.tone}`}>{summary.data?.[t.key] ?? "–"}</div>
            <div className="mt-1 text-xs text-[#6e6e73]">{t.label}</div>
          </button>
        ))}
      </div>
      <div className="mb-4 flex flex-wrap gap-2">
        <input aria-label="Search items" placeholder="Search plate, type, number…" className={`${inputCls} max-w-xs rounded-full`} value={search} onChange={(e) => reset(setSearch)(e.target.value)} />
        <select aria-label="Category" className={`${inputCls} w-auto`} value={category} onChange={(e) => reset(setCategory)(e.target.value)}>
          <option value="">All categories</option>
          {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={archived} onChange={(e) => { setArchived(e.target.checked); setPage(1); }} /> Archived</label>
      </div>
      {q.isLoading ? <Spinner /> : q.error ? <ErrorState error={q.error} retry={() => q.refetch()} /> : q.data!.items.length === 0 ? (
        <EmptyState title="Nothing here yet" hint="Add vehicle registrations, insurance, licences and other renewals." action={<Button onClick={() => setEditing("new")}>Add item</Button>} />
      ) : (
        <>
          <Table head={["Subject", "Type", "Category", "Expires", "Status", ""]}>
            {q.data!.items.map((i) => (
              <tr key={i.id}>
                <Td><div className="font-semibold text-ink">{i.subject}</div>{i.reference_no && <div className="text-xs text-[#6e6e73]">{i.reference_no}</div>}</Td>
                <Td>{i.item_type}</Td>
                <Td>{CAT_LABEL[i.category]}</Td>
                <Td>{formatDate(i.expires_on)}<div className={`text-xs ${i.days_left < 0 ? "text-[#d70015]" : "text-[#6e6e73]"}`}>{daysLabel(i.days_left)}</div></Td>
                <Td><StatusBadge status={i.status} /></Td>
                <Td className="space-x-1 whitespace-nowrap text-right">
                  {!i.is_archived && <Button variant="ghost" onClick={() => setRenewing(i)}>Renew</Button>}
                  <Button variant="ghost" onClick={() => setHistory(i)}>History</Button>
                  <Button variant="ghost" onClick={() => setEditing(i)}>Edit</Button>
                  {i.is_archived
                    ? <Button variant="ghost" onClick={() => api.patch(`/expiry/items/${i.id}`, { is_archived: false }).then(() => invalidate(qc))}>Restore</Button>
                    : <Button variant="ghost" onClick={() => setArchiving(i)}>Archive</Button>}
                </Td>
              </tr>
            ))}
          </Table>
          <Pagination page={page} pageSize={q.data!.page_size} total={q.data!.total} onPage={setPage} />
        </>
      )}
      <ItemDialog item={editing} onClose={() => setEditing(null)} />
      <RenewDialog item={renewing} onClose={() => setRenewing(null)} />
      <HistoryDialog item={history} onClose={() => setHistory(null)} />
      <ConfirmDialog open={!!archiving} title="Archive this item?" message={`${archiving?.subject} · ${archiving?.item_type} will stop appearing in reminders. Its history is kept and you can restore it.`}
        confirmLabel="Archive" danger busy={archive.isPending} onClose={() => setArchiving(null)} onConfirm={() => archiving && archive.mutate(archiving)} />
    </>
  );
}
