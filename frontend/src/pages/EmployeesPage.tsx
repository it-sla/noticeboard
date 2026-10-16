import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button, ConfirmDialog, Dialog, EmptyState, ErrorState, Field, inputCls, PageHeader, Pagination, Spinner, Table, Td, useToast } from "../components/ui";
import { api, errorMessage } from "../lib/api";
import type { Department, Employee, ImportResult, Page } from "../types";

const schema = z.object({
  name: z.string().trim().min(1, "Name is required").max(200),
  email: z.string().trim().min(1, "Email is required").email("Enter a valid email address"),
  department_id: z.string(),
  job_title: z.string().max(200),
});
type Form = z.infer<typeof schema>;

function EmployeeDialog({ employee, departments, onClose }: { employee: Employee | "new" | null; departments: Department[]; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const { register, handleSubmit, reset, formState: { errors } } = useForm<Form>({ resolver: zodResolver(schema) });
  useEffect(() => {
    if (employee === null) return;
    const e = employee === "new" ? null : employee;
    reset({ name: e?.name ?? "", email: e?.email ?? "", department_id: e?.department_id?.toString() ?? "", job_title: e?.job_title ?? "" });
  }, [employee, reset]);
  const save = useMutation({
    mutationFn: (v: Form) => {
      const body = { name: v.name, email: v.email, job_title: v.job_title || null, department_id: v.department_id ? Number(v.department_id) : null };
      return employee === "new" ? api.post("/employees", body) : api.patch(`/employees/${(employee as Employee).id}`, body);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["employees"] }); qc.invalidateQueries({ queryKey: ["departments"] }); toast("success", "Employee saved"); onClose(); },
    onError: (e) => toast("error", errorMessage(e)),
  });
  return (
    <Dialog
      open={employee !== null}
      title={employee === "new" ? "Add employee" : "Edit employee"}
      onClose={onClose}
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={handleSubmit((v) => save.mutate(v))} disabled={save.isPending}>Save</Button></>}
    >
      <form className="space-y-3" noValidate onSubmit={handleSubmit((v) => save.mutate(v))}>
        <Field label="Name" error={errors.name?.message}>{(p) => <input {...p} className={inputCls} {...register("name")} />}</Field>
        <Field label="Email" error={errors.email?.message}>{(p) => <input {...p} type="email" className={inputCls} {...register("email")} />}</Field>
        <Field label="Department">
          {(p) => (
            <select {...p} className={inputCls} {...register("department_id")}>
              <option value="">— none —</option>
              {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          )}
        </Field>
        <Field label="Job title">{(p) => <input {...p} className={inputCls} {...register("job_title")} />}</Field>
        <button type="submit" hidden />
      </form>
    </Dialog>
  );
}

function ImportDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (!open) { setFile(null); setResult(null); } }, [open]);
  const run = async (commit: boolean) => {
    if (!file) return;
    setBusy(true);
    try {
      const r = await api.upload<ImportResult>("/employees/import", file, { commit });
      setResult(r);
      if (commit) {
        toast("success", `Imported ${r.ok} employees`);
        qc.invalidateQueries({ queryKey: ["employees"] });
        qc.invalidateQueries({ queryKey: ["departments"] });
        onClose();
      }
    } catch (e) {
      toast("error", errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open={open} title="Import employees" onClose={onClose}
      footer={<><Button variant="secondary" onClick={onClose}>Close</Button><Button variant="secondary" onClick={() => run(false)} disabled={!file || busy}>Preview</Button><Button onClick={() => run(true)} disabled={!result || result.ok === 0 || busy}>Import {result?.ok ?? 0}</Button></>}>
      <p className="mb-2">CSV (UTF-8) or Excel file with columns <strong>Name</strong>, <strong>Email</strong>, Department, Job Title. Existing emails are skipped, never overwritten.</p>
      <input type="file" aria-label="Import file" accept=".csv,.xlsx" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setResult(null); }} />
      {result && (
        <div className="mt-3">
          <p className="mb-2 text-sm">{result.ok} new · {result.skipped} skipped (existing/duplicate) · {result.errors} invalid</p>
          <div className="max-h-60 overflow-auto rounded border border-hairline text-xs">
            <table className="w-full">
              <thead className="bg-[#fafafc] text-left"><tr><th className="p-1.5">Row</th><th>Email</th><th>Result</th></tr></thead>
              <tbody>
                {result.rows.map((r) => (
                  <tr key={r.row} className={r.status === "ok" ? "" : "bg-amber-50"}>
                    <td className="p-1.5">{r.row}</td><td>{r.email}</td>
                    <td>{r.status === "ok" ? (r.new_department ? "OK (new department)" : "OK") : r.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Dialog>
  );
}

export function EmployeesPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [dept, setDept] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Employee | "new" | null>(null);
  const [importing, setImporting] = useState(false);
  const [deactivating, setDeactivating] = useState<Employee | null>(null);
  const depts = useQuery({ queryKey: ["departments"], queryFn: () => api.get<Department[]>("/departments") });
  const q = useQuery({ queryKey: ["employees", search, dept, page], queryFn: () => api.get<Page<Employee>>("/employees", { search, department_id: dept, page }) });
  const deactivate = useMutation({
    mutationFn: (e: Employee) => api.del(`/employees/${e.id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["employees"] }); qc.invalidateQueries({ queryKey: ["departments"] }); setDeactivating(null); toast("success", "Employee deactivated"); },
    onError: (e) => toast("error", errorMessage(e)),
  });
  return (
    <>
      <PageHeader title="Employees" subtitle="Inactive employees never receive notices; their history is kept."
        actions={<><Button variant="secondary" onClick={() => setImporting(true)}>Import CSV/Excel</Button><Button onClick={() => setEditing("new")}>Add employee</Button></>} />
      <div className="mb-4 flex flex-wrap gap-2">
        <input aria-label="Search employees" placeholder="Search name or email…" className={`${inputCls} max-w-xs`} value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        <select aria-label="Department" className={`${inputCls} w-auto`} value={dept} onChange={(e) => { setDept(e.target.value); setPage(1); }}>
          <option value="">All departments</option>
          {(depts.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      </div>
      {q.isLoading ? <Spinner /> : q.error ? <ErrorState error={q.error} retry={() => q.refetch()} /> : q.data!.items.length === 0 ? (
        <EmptyState title="No employees found" hint="Add employees or import a CSV/Excel list." />
      ) : (
        <>
          <Table head={["Name", "Email", "Department", "Job title", "Status", ""]}>
            {q.data!.items.map((e) => (
              <tr key={e.id} className={e.is_active ? "" : "text-[#86868b]"}>
                <Td className="font-semibold">{e.name}</Td><Td>{e.email}</Td><Td>{e.department_name ?? "—"}</Td><Td>{e.job_title ?? "—"}</Td>
                <Td>{e.is_active ? "Active" : "Inactive"}</Td>
                <Td className="space-x-1 text-right">
                  <Button variant="ghost" onClick={() => setEditing(e)}>Edit</Button>
                  {e.is_active
                    ? <Button variant="ghost" onClick={() => setDeactivating(e)}>Deactivate</Button>
                    : <Button variant="ghost" onClick={() => api.patch(`/employees/${e.id}`, { is_active: true }).then(() => qc.invalidateQueries({ queryKey: ["employees"] }))}>Activate</Button>}
                </Td>
              </tr>
            ))}
          </Table>
          <Pagination page={page} pageSize={q.data!.page_size} total={q.data!.total} onPage={setPage} />
        </>
      )}
      <EmployeeDialog employee={editing} departments={depts.data ?? []} onClose={() => setEditing(null)} />
      <ImportDialog open={importing} onClose={() => setImporting(false)} />
      <ConfirmDialog open={!!deactivating} title="Deactivate employee?" message={`${deactivating?.name} will no longer receive notices. Their history is kept.`}
        confirmLabel="Deactivate" danger busy={deactivate.isPending} onClose={() => setDeactivating(null)} onConfirm={() => deactivating && deactivate.mutate(deactivating)} />
    </>
  );
}
