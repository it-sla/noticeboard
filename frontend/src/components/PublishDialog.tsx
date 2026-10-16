import { useEffect, useState } from "react";
import type { Preview } from "../types";
import { Dialog, Button } from "./ui";

export function PublishDialog({
  open,
  preview,
  busy,
  onConfirm,
  onClose,
}: {
  open: boolean;
  preview: Preview | null;
  busy: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  const [ack, setAck] = useState(false);
  useEffect(() => {
    if (!open) setAck(false);
  }, [open]);
  if (!preview) return null;
  const blocked = !preview.broadcast_enabled;
  return (
    <Dialog
      open={open}
      title="Publish & Email"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={onConfirm} disabled={!ack || busy || blocked}>
            {busy ? "Publishing…" : `Publish & email ${preview.recipient_count}`}
          </Button>
        </>
      }
    >
      <dl className="grid grid-cols-[6rem_1fr] gap-y-1">
        <dt className="text-[#6e6e73]">Subject</dt>
        <dd className="font-semibold text-ink">{preview.subject}</dd>
        <dt className="text-[#6e6e73]">From</dt>
        <dd>{preview.sender}</dd>
        <dt className="text-[#6e6e73]">Recipients</dt>
        <dd className="font-semibold text-ink">{preview.recipient_count} active employees</dd>
        <dt className="text-[#6e6e73]">Attachments</dt>
        <dd>{preview.attachments.length}</dd>
      </dl>
      {blocked && (
        <p role="alert" className="mt-3 rounded bg-red-50 p-2 text-red-700">
          Email broadcasting is disabled. A Super Admin must enable it in Settings.
        </p>
      )}
      {preview.email_mode === "dry_run" && (
        <p className="mt-3 rounded bg-amber-50 p-2 text-amber-800">Dry-run mode: jobs are recorded but no real email is sent.</p>
      )}
      <p className="mt-3">The recipient list is fixed at the moment you publish, and the notice cannot be edited afterwards.</p>
      <label className="mt-3 flex items-start gap-2">
        <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} className="mt-1" />
        <span>I confirm this notice should be emailed to {preview.recipient_count} employees.</span>
      </label>
    </Dialog>
  );
}
