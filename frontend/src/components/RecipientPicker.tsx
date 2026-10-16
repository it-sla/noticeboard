import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../lib/api";
import type { Department, Employee, Page, RecipientMode } from "../types";
import { inputCls } from "./ui";

export interface Selection {
  recipient_mode: RecipientMode;
  department_ids: number[];
  employee_ids: number[];
}

const toggle = (list: number[], id: number) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

export function RecipientPicker({ value, onChange }: { value: Selection; onChange: (s: Selection) => void }) {
  const [search, setSearch] = useState("");
  const depts = useQuery({ queryKey: ["departments"], queryFn: () => api.get<Department[]>("/departments") });
  const emps = useQuery({
    queryKey: ["employees-pick", search],
    enabled: value.recipient_mode === "employees",
    queryFn: () => api.get<Page<Employee>>("/employees", { search, active: true, page_size: 50 }),
  });
  return (
    <fieldset className="space-y-3">
      <legend className="text-sm font-semibold text-[#333333]">Recipients</legend>
      <div className="flex flex-wrap gap-4 text-sm">
        {(
          [
            ["all", "All active employees"],
            ["departments", "Selected departments"],
            ["employees", "Selected employees"],
          ] as const
        ).map(([m, label]) => (
          <label key={m} className="flex items-center gap-2">
            <input type="radio" name="recipient_mode" checked={value.recipient_mode === m} onChange={() => onChange({ ...value, recipient_mode: m })} />
            {label}
          </label>
        ))}
      </div>
      {value.recipient_mode === "departments" && (
        <div className="grid gap-1 sm:grid-cols-2">
          {(depts.data ?? []).map((d) => (
            <label key={d.id} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={value.department_ids.includes(d.id)} onChange={() => onChange({ ...value, department_ids: toggle(value.department_ids, d.id) })} />
              {d.name} <span className="text-[#86868b]">({d.employee_count})</span>
            </label>
          ))}
          {depts.data?.length === 0 && <p className="text-sm text-[#6e6e73]">No departments yet.</p>}
        </div>
      )}
      {value.recipient_mode === "employees" && (
        <div>
          <input aria-label="Search employees" placeholder="Search by name or email…" className={`${inputCls} mb-2 max-w-sm`} value={search} onChange={(e) => setSearch(e.target.value)} />
          <div className="max-h-56 overflow-y-auto rounded border border-hairline p-2">
            {(emps.data?.items ?? []).map((e) => (
              <label key={e.id} className="flex items-center gap-2 py-0.5 text-sm">
                <input type="checkbox" checked={value.employee_ids.includes(e.id)} onChange={() => onChange({ ...value, employee_ids: toggle(value.employee_ids, e.id) })} />
                {e.name} <span className="text-[#86868b]">{e.email}</span>
              </label>
            ))}
            {emps.data?.items.length === 0 && <p className="text-sm text-[#6e6e73]">No matching employees.</p>}
          </div>
          <p className="mt-1 text-xs text-[#6e6e73]">{value.employee_ids.length} selected</p>
        </div>
      )}
    </fieldset>
  );
}
