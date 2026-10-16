import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button, EmptyState, ErrorState, Field, inputCls, PageHeader, Spinner, Table, Td, useToast } from "../components/ui";
import { api, errorMessage } from "../lib/api";
import type { Department } from "../types";

const schema = z.object({ name: z.string().trim().min(1, "Name is required").max(120) });

export function DepartmentsPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const q = useQuery({ queryKey: ["departments", "all"], queryFn: () => api.get<Department[]>("/departments", { include_inactive: true }) });
  const { register, handleSubmit, reset, formState: { errors } } = useForm({ resolver: zodResolver(schema) });
  const refresh = () => qc.invalidateQueries({ queryKey: ["departments"] });
  const create = useMutation({
    mutationFn: (v: { name: string }) => api.post("/departments", v),
    onSuccess: () => { reset(); refresh(); toast("success", "Department created"); },
    onError: (e) => toast("error", errorMessage(e)),
  });
  const toggle = useMutation({
    mutationFn: (d: Department) => api.patch(`/departments/${d.id}`, { is_active: !d.is_active }),
    onSuccess: refresh,
    onError: (e) => toast("error", errorMessage(e)),
  });
  const rename = (d: Department) => {
    const name = window.prompt("Department name", d.name);
    if (name && name.trim() !== d.name) api.patch(`/departments/${d.id}`, { name }).then(refresh).catch((e) => toast("error", errorMessage(e)));
  };
  return (
    <>
      <PageHeader title="Departments" subtitle="Group employees for targeted notices." />
      <form onSubmit={handleSubmit((v) => create.mutate(v))} className="mb-6 flex max-w-md items-start gap-2" noValidate>
        <div className="flex-1">
          <Field label="New department" error={errors.name?.message}>
            {(p) => <input {...p} className={inputCls} {...register("name")} />}
          </Field>
        </div>
        <Button type="submit" className="mt-6" disabled={create.isPending}>Add</Button>
      </form>
      {q.isLoading ? <Spinner /> : q.error ? <ErrorState error={q.error} /> : q.data!.length === 0 ? (
        <EmptyState title="No departments yet" hint="Add your first department above." />
      ) : (
        <Table head={["Name", "Active employees", "Status", ""]}>
          {q.data!.map((d) => (
            <tr key={d.id}>
              <Td className="font-semibold">{d.name}</Td>
              <Td>{d.employee_count}</Td>
              <Td>{d.is_active ? "Active" : "Inactive"}</Td>
              <Td className="space-x-1 text-right">
                <Button variant="ghost" onClick={() => rename(d)}>Rename</Button>
                <Button variant="ghost" onClick={() => toggle.mutate(d)}>{d.is_active ? "Deactivate" : "Activate"}</Button>
              </Td>
            </tr>
          ))}
        </Table>
      )}
    </>
  );
}
