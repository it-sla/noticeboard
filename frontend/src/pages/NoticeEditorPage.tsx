import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation, useNavigate, useParams } from "react-router";
import { z } from "zod";
import { useAuth } from "../app/auth";
import { PublishDialog } from "../components/PublishDialog";
import { RecipientPicker, type Selection } from "../components/RecipientPicker";
import { RichTextEditor } from "../components/RichTextEditor";
import { Button, Card, ErrorState, Field, inputCls, PageHeader, Spinner, useToast } from "../components/ui";
import { api, ApiError, errorMessage } from "../lib/api";
import { formatBytes, nepalLocalToIso } from "../lib/format";
import { CATEGORIES, PRIORITIES, type Attachment, type Notice, type Preview } from "../types";

const schema = z.object({
  title: z.string().trim().min(1, "Title is required").max(300),
  category: z.enum(CATEGORIES),
  priority: z.enum(PRIORITIES),
});
type Form = z.infer<typeof schema>;

export function NoticeEditorPage() {
  // /notices/new/edit creates a draft, then redirects to /notices/:id/edit. The router may remount
  // this page on that redirect, so anything needed afterwards travels in location.state.
  const { id: routeId } = useParams();
  const id = routeId === "new" ? undefined : routeId;
  const nav = useNavigate();
  const location = useLocation();
  const qc = useQueryClient();
  const toast = useToast();
  const { can } = useAuth();
  const [noticeId, setNoticeId] = useState<number | null>(id ? Number(id) : null);
  const existing = useQuery({
    queryKey: ["notice", id],
    enabled: !!id,
    queryFn: () => api.get<Notice>(`/notices/${id}`),
  });
  const form = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: { title: "", category: "General Announcement", priority: "normal" },
  });
  const [body, setBody] = useState("");
  const [bodyError, setBodyError] = useState("");
  const [sel, setSel] = useState<Selection>({ recipient_mode: "all", department_ids: [], employee_ids: [] });
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [testTo, setTestTo] = useState("");
  const [when, setWhen] = useState("");
  const loaded = useRef(false);

  useEffect(() => {
    const n = existing.data;
    if (!n || loaded.current) return;
    loaded.current = true;
    form.reset({ title: n.title, category: n.category, priority: n.priority });
    setBody(n.body_html);
    setSel({ recipient_mode: n.recipient_mode, department_ids: n.department_ids, employee_ids: n.employee_ids });
    setAttachments(n.attachments);
    if ((location.state as { preview?: boolean } | null)?.preview) loadPreview(n.id).catch(() => {});
  }, [existing.data, form, location.state]);

  if (id && existing.isLoading) return <Spinner />;
  if (id && existing.error) return <ErrorState error={existing.error} />;
  if (existing.data && existing.data.status !== "draft") return <Navigate to={`/notices/${existing.data.id}`} replace />;

  const payload = (v: Form) => ({ ...v, body_html: body, ...sel });

  /** Validates and persists the draft; returns the notice id or null. */
  async function save(opts?: { preview?: boolean }): Promise<{ id: number; created: boolean } | null> {
    const ok = await form.trigger();
    if (!ok) return null;
    const v = form.getValues();
    try {
      if (noticeId) {
        await api.patch<Notice>(`/notices/${noticeId}`, payload(v));
        return { id: noticeId, created: false };
      }
      const n = await api.post<Notice>("/notices", payload(v));
      setNoticeId(n.id);
      qc.setQueryData(["notice", String(n.id)], n);
      nav(`/notices/${n.id}/edit`, { replace: true, state: { preview: !!opts?.preview } });
      return { id: n.id, created: true };
    } catch (e) {
      toast("error", errorMessage(e));
      return null;
    }
  }

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      toast("error", errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const loadPreview = (nid: number) => api.get<Preview>(`/notices/${nid}/preview`).then(setPreview);

  const onSave = () =>
    run(async () => {
      if (await save()) {
        qc.invalidateQueries({ queryKey: ["notices"] });
        toast("success", "Draft saved");
      }
    });
  const onPreview = () =>
    run(async () => {
      if (!body.trim() && !attachments.some((a) => a.content_type.startsWith("image/"))) {
        setBodyError("Add some text, or upload an image of the notice");
        return;
      }
      setBodyError("");
      const saved = await save({ preview: true });
      if (saved && !saved.created) await loadPreview(saved.id);
    });
  const onTest = () =>
    run(async () => {
      const v = form.getValues();
      const r = await api.post<{ message: string }>("/email/test", { to: testTo, title: v.title, body_html: body, category: v.category, priority: v.priority });
      toast("success", r.message);
    });
  const onPublish = () =>
    run(async () => {
      if (!noticeId || !preview) return;
      try {
        await api.post(`/notices/${noticeId}/publish`, { confirm: true, expected_recipient_count: preview.recipient_count });
      } catch (e) {
        if (e instanceof ApiError && e.code === "recipient_count_changed") {
          await loadPreview(noticeId);
          setConfirmOpen(false);
        }
        throw e;
      }
      qc.invalidateQueries({ queryKey: ["notices"] });
      toast("success", "Notice queued for sending");
      nav(`/notices/${noticeId}`);
    });
  const onSchedule = () =>
    run(async () => {
      const nid = (await save())?.id;
      if (!nid) return;
      await api.post(`/notices/${nid}/schedule`, { scheduled_at: nepalLocalToIso(when) });
      toast("success", "Notice scheduled");
      nav(`/notices/${nid}`);
    });
  const onUpload = (file: File) =>
    run(async () => {
      if (!noticeId) return;
      const a = await api.upload<Attachment>(`/notices/${noticeId}/attachments`, file);
      setAttachments((x) => [...x, a]);
      setPreview(null);
    });
  const onRemove = (a: Attachment) =>
    run(async () => {
      await api.del(`/notices/${noticeId}/attachments/${a.id}`);
      setAttachments((x) => x.filter((y) => y.id !== a.id));
      setPreview(null);
    });

  const e = form.formState.errors;
  return (
    <>
      <PageHeader title={id ? "Edit notice" : "Create notice"} subtitle="Save a draft, preview it, then publish." />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="space-y-4">
          <Card>
            <form className="space-y-4" onSubmit={(ev) => ev.preventDefault()} noValidate>
              <Field label="Title" error={e.title?.message}>
                {(p) => <input {...p} className={inputCls} maxLength={300} {...form.register("title")} />}
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Category">
                  {(p) => (
                    <select {...p} className={inputCls} {...form.register("category")}>
                      {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
                    </select>
                  )}
                </Field>
                <Field label="Priority">
                  {(p) => (
                    <select {...p} className={inputCls} {...form.register("priority")}>
                      {PRIORITIES.map((c) => <option key={c}>{c}</option>)}
                    </select>
                  )}
                </Field>
              </div>
              <div>
                <span className="mb-1 block text-sm font-semibold text-[#333333]">Body</span>
                <RichTextEditor value={body} onChange={setBody} label="Notice body" />
                {bodyError && <p role="alert" className="mt-1 text-xs text-red-600">{bodyError}</p>}
              </div>
              <RecipientPicker value={sel} onChange={(s) => { setSel(s); setPreview(null); }} />
            </form>
          </Card>
          <Card title="Image & attachments">
            <ul className="mb-3 space-y-1 text-sm">
              {attachments.map((a) => (
                <li key={a.id} className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    {a.content_type.startsWith("image/") && <img src={`/api/attachments/${a.id}/download`} alt="" className="h-12 w-12 rounded object-cover" />}
                    <span>{a.original_filename} <span className="text-[#86868b]">({formatBytes(a.size_bytes)})</span></span>
                  </span>
                  <Button variant="ghost" onClick={() => onRemove(a)} aria-label={`Remove ${a.original_filename}`}>Remove</Button>
                </li>
              ))}
              {attachments.length === 0 && <li className="text-[#6e6e73]">No attachments.</li>}
            </ul>
            <label className="text-sm">
              <span className="sr-only">Add attachment</span>
              <input type="file" disabled={!noticeId} accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv" onChange={(ev) => { const f = ev.target.files?.[0]; if (f) onUpload(f); ev.target.value = ""; }} />
            </label>
            <p className="mt-1 text-xs text-[#6e6e73]">{noticeId ? "Upload a photo of the physical notice (shown inside the email), or PDF/Office files (attached). Up to 20 MB each." : "Save the draft first, then add an image or files."}</p>
          </Card>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={onSave} disabled={busy}>Save draft</Button>
            <Button onClick={onPreview} disabled={busy}>Preview</Button>
          </div>
        </div>

        <div className="space-y-4">
          {preview ? (
            <Card title="Preview">
              <dl className="mb-3 grid grid-cols-[7rem_1fr] gap-y-1 text-sm">
                <dt className="text-[#6e6e73]">Subject</dt><dd className="font-semibold">{preview.subject}</dd>
                <dt className="text-[#6e6e73]">Sender</dt><dd>{preview.sender}</dd>
                <dt className="text-[#6e6e73]">Recipients</dt><dd className="font-semibold">{preview.recipient_count}</dd>
                <dt className="text-[#6e6e73]">Attachments</dt>
                <dd>{preview.attachments.length ? preview.attachments.map((a) => a.original_filename).join(", ") : "None"}</dd>
              </dl>
              <iframe title="Email preview" sandbox="" srcDoc={preview.html} className="h-[28rem] w-full rounded border border-hairline bg-white" />
              {can("ADMIN") && (
                <div className="mt-4 space-y-4 border-t border-[#f0f0f0] pt-4">
                  <div className="flex flex-wrap items-end gap-2">
                    <Field label="Send test email to one address">
                      {(p) => <input {...p} type="email" className={`${inputCls} w-64`} value={testTo} onChange={(ev) => setTestTo(ev.target.value)} placeholder="you@company.com" />}
                    </Field>
                    <Button variant="secondary" onClick={onTest} disabled={busy || !testTo}>Send test</Button>
                  </div>
                  <div className="flex flex-wrap items-end gap-2">
                    <Field label="Schedule (Nepal time)">
                      {(p) => <input {...p} type="datetime-local" className={`${inputCls} w-56`} value={when} onChange={(ev) => setWhen(ev.target.value)} />}
                    </Field>
                    <Button variant="secondary" onClick={onSchedule} disabled={busy || !when || preview.recipient_count === 0}>Schedule</Button>
                  </div>
                  <Button onClick={() => setConfirmOpen(true)} disabled={busy || preview.recipient_count === 0}>
                    Publish &amp; Email
                  </Button>
                  {preview.recipient_count === 0 && <p className="text-sm text-red-600">The selection contains no active employees.</p>}
                </div>
              )}
              {!can("ADMIN") && <p className="mt-3 text-sm text-[#6e6e73]">An Admin must publish this notice.</p>}
            </Card>
          ) : (
            <Card>
              <p className="text-sm text-[#6e6e73]">Click <strong>Preview</strong> to see the email, recipient count and sender before publishing.</p>
            </Card>
          )}
        </div>
      </div>
      <PublishDialog open={confirmOpen} preview={preview} busy={busy} onConfirm={onPublish} onClose={() => setConfirmOpen(false)} />
    </>
  );
}
