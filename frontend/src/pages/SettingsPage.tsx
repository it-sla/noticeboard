import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useAuth } from "../app/auth";
import { Button, Card, ConfirmDialog, ErrorState, Field, inputCls, PageHeader, Spinner, Table, Td, useToast } from "../components/ui";
import { api, errorMessage } from "../lib/api";
import type { AppSettings, Role, User } from "../types";

const ROLES: Role[] = ["SUPER_ADMIN", "ADMIN", "NOTICE_EDITOR", "VIEWER"];

function Users() {
  const qc = useQueryClient();
  const toast = useToast();
  const users = useQuery({ queryKey: ["users"], queryFn: () => api.get<User[]>("/users") });
  const [f, setF] = useState({ email: "", name: "", role: "NOTICE_EDITOR" as Role, password: "" });
  const create = useMutation({
    mutationFn: () => api.post("/users", f),
    onSuccess: () => { setF({ email: "", name: "", role: "NOTICE_EDITOR", password: "" }); qc.invalidateQueries({ queryKey: ["users"] }); toast("success", "User created"); },
    onError: (e) => toast("error", errorMessage(e)),
  });
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: number; body: object }) => api.patch(`/users/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
    onError: (e) => toast("error", errorMessage(e)),
  });
  return (
    <Card title="Users">
      {users.isLoading ? <Spinner /> : users.error ? <ErrorState error={users.error} /> : (
        <Table head={["Name", "Email", "Role", "Active"]}>
          {users.data!.map((u) => (
            <tr key={u.id}>
              <Td>{u.name}</Td><Td>{u.email}</Td>
              <Td>
                <select aria-label={`Role for ${u.email}`} className={`${inputCls} w-auto`} value={u.role} onChange={(e) => patch.mutate({ id: u.id, body: { role: e.target.value } })}>
                  {ROLES.map((r) => <option key={r}>{r}</option>)}
                </select>
              </Td>
              <Td><input type="checkbox" aria-label={`Active: ${u.email}`} checked={u.is_active} onChange={(e) => patch.mutate({ id: u.id, body: { is_active: e.target.checked } })} /></Td>
            </tr>
          ))}
        </Table>
      )}
      <form className="mt-4 grid max-w-2xl gap-3 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
        <Field label="Name">{(p) => <input {...p} required className={inputCls} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />}</Field>
        <Field label="Email">{(p) => <input {...p} type="email" required className={inputCls} value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />}</Field>
        <Field label="Role">{(p) => <select {...p} className={inputCls} value={f.role} onChange={(e) => setF({ ...f, role: e.target.value as Role })}>{ROLES.map((r) => <option key={r}>{r}</option>)}</select>}</Field>
        <Field label="Initial password" hint="At least 12 characters.">{(p) => <input {...p} type="password" required minLength={12} autoComplete="new-password" className={inputCls} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />}</Field>
        <div><Button type="submit" disabled={create.isPending}>Add user</Button></div>
      </form>
    </Card>
  );
}

function ExpirySettings({ s }: { s: AppSettings }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [enabled, setEnabled] = useState(s.expiry_alerts_enabled);
  const [extra, setExtra] = useState(s.expiry_extra_recipients.join("\n"));
  const save = useMutation({
    mutationFn: () => api.put("/settings/expiry", { enabled, extra_recipients: extra.split(/[\s,;]+/).filter(Boolean) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["settings"] }); toast("success", "Expiry reminder settings saved"); },
    onError: (e) => toast("error", errorMessage(e)),
  });
  return (
    <Card title="Expiry reminders">
      <p className="mb-3 text-sm">A daily email (after 8:00 Nepal time) lists items that reached a reminder date, plus overdue items on Mondays. It goes to every active Admin and Super Admin, and to the extra addresses below. It is sent only when the email mode is SMTP.</p>
      <label className="mb-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} /> Send expiry reminder emails</label>
      <Field label="Extra recipients (optional)" hint="One address per line.">{(p) => <textarea {...p} rows={3} className={`${inputCls} max-w-md`} value={extra} onChange={(e) => setExtra(e.target.value)} />}</Field>
      <Button className="mt-3" onClick={() => save.mutate()} disabled={save.isPending}>Save</Button>
    </Card>
  );
}

export function SettingsPage() {
  const { can } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const [confirm, setConfirm] = useState(false);
  const q = useQuery({ queryKey: ["settings"], queryFn: () => api.get<AppSettings>("/settings") });
  const toggle = useMutation({
    mutationFn: (enabled: boolean) => api.put("/settings/broadcast", { enabled }),
    onSuccess: () => { qc.invalidateQueries(); setConfirm(false); toast("success", "Broadcast setting updated"); },
    onError: (e) => toast("error", errorMessage(e)),
  });
  const check = useMutation({
    mutationFn: () => api.post<{ ok: boolean; message: string }>("/settings/smtp-check"),
    onSuccess: (r) => toast(r.ok ? "success" : "error", r.message),
    onError: (e) => toast("error", errorMessage(e)),
  });
  if (q.isLoading) return <Spinner />;
  if (q.error || !q.data) return <ErrorState error={q.error} />;
  const s = q.data;
  return (
    <>
      <PageHeader title="Settings" subtitle="SMTP credentials are configured on the server and never shown here." />
      <div className="space-y-4">
        <Card title="Email broadcasting">
          <p className="mb-3 text-sm">
            Broadcasting is currently <strong className={s.broadcast_enabled ? "text-green-700" : "text-red-700"}>{s.broadcast_enabled ? "enabled" : "disabled"}</strong>.
            While disabled, notices cannot be published and the worker sends nothing.
          </p>
          {can("SUPER_ADMIN") ? (
            <Button variant={s.broadcast_enabled ? "danger" : "primary"} onClick={() => (s.broadcast_enabled ? toggle.mutate(false) : setConfirm(true))}>
              {s.broadcast_enabled ? "Disable broadcasting" : "Enable broadcasting"}
            </Button>
          ) : <p className="text-sm text-[#6e6e73]">Only a Super Admin can change this.</p>}
        </Card>
        <Card title="SMTP">
          <dl className="grid max-w-xl grid-cols-[10rem_1fr] gap-y-1 text-sm">
            <dt className="text-[#6e6e73]">Mode</dt><dd>{s.email_mode === "dry_run" ? "Dry run (no email is sent)" : "SMTP (live)"}</dd>
            <dt className="text-[#6e6e73]">Server</dt><dd>{s.smtp_host}:{s.smtp_port} {s.smtp_use_ssl ? "(SSL)" : ""}</dd>
            <dt className="text-[#6e6e73]">Sender</dt><dd>{s.smtp_from_email}</dd>
            <dt className="text-[#6e6e73]">Password set</dt><dd>{s.smtp_password_configured ? "Yes" : "No"}</dd>
            <dt className="text-[#6e6e73]">Rate limits</dt><dd>{s.rate_per_minute}/minute, {s.rate_per_day}/day</dd>
            <dt className="text-[#6e6e73]">Attachments</dt><dd>{s.attachment_mode === "attach" ? "Attached to email" : "Protected links"}</dd>
            <dt className="text-[#6e6e73]">Timezone</dt><dd>{s.timezone}</dd>
          </dl>
          {can("SUPER_ADMIN") && <Button className="mt-3" variant="secondary" onClick={() => check.mutate()} disabled={check.isPending}>Test SMTP connection</Button>}
        </Card>
        <ExpirySettings s={s} />
        {can("SUPER_ADMIN") && <Users />}
      </div>
      <ConfirmDialog open={confirm} title="Enable email broadcasting?" confirmLabel="Enable" busy={toggle.isPending} onClose={() => setConfirm(false)} onConfirm={() => toggle.mutate(true)}
        message="Admins will be able to publish notices that email real employees (when EMAIL_MODE is smtp). Confirm that the SMTP limits and test email have been verified." />
    </>
  );
}
