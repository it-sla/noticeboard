import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Card, ErrorState, Field, inputCls, PageHeader, Spinner, useToast } from "../components/ui";
import { api, errorMessage } from "../lib/api";
import type { Template } from "../types";

function TemplateForm({ t }: { t: Template }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [v, setV] = useState({ subject_prefix: t.subject_prefix, header_text: t.header_text, footer_text: t.footer_text });
  const save = useMutation({
    mutationFn: () => api.patch(`/templates/${t.id}`, v),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["templates"] }); toast("success", "Template saved"); },
    onError: (e) => toast("error", errorMessage(e)),
  });
  return (
    <Card title={`${t.name}${t.is_default ? " (default)" : ""}`}>
      <div className="max-w-xl space-y-3">
        <Field label="Organization name (email header)">{(p) => <input {...p} className={inputCls} value={v.header_text} onChange={(e) => setV({ ...v, header_text: e.target.value })} />}</Field>
        <Field label="Subject prefix" hint="Added before every subject, e.g. “[SLT] ”.">{(p) => <input {...p} className={inputCls} value={v.subject_prefix} onChange={(e) => setV({ ...v, subject_prefix: e.target.value })} />}</Field>
        <Field label="Footer text">{(p) => <textarea {...p} rows={3} className={inputCls} value={v.footer_text} onChange={(e) => setV({ ...v, footer_text: e.target.value })} />}</Field>
        <Button onClick={() => save.mutate()} disabled={save.isPending || !v.header_text.trim()}>Save template</Button>
      </div>
    </Card>
  );
}

export function TemplatesPage() {
  const q = useQuery({ queryKey: ["templates"], queryFn: () => api.get<Template[]>("/templates") });
  return (
    <>
      <PageHeader title="Templates" subtitle="Branding for outgoing notice emails. Layout is a fixed responsive design." />
      {q.isLoading ? <Spinner /> : q.error ? <ErrorState error={q.error} /> : <div className="space-y-4">{q.data!.map((t) => <TemplateForm key={t.id} t={t} />)}</div>}
    </>
  );
}
