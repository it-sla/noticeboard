import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import { STATUS_LABEL } from "../lib/format";

const cx = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(" ");

// ------------------------------------------------------------------ buttons
type Variant = "primary" | "secondary" | "danger" | "ghost";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand-700 text-white hover:bg-brand-800 disabled:bg-[#d2d2d7]",
  secondary: "bg-white text-brand-700 ring-1 ring-inset ring-brand-700 hover:bg-[#f5f5f7] disabled:text-[#86868b] disabled:ring-[#d2d2d7]",
  danger: "bg-[#d70015] text-white hover:bg-[#b80012] disabled:bg-[#d2d2d7]",
  ghost: "text-brand-700 hover:bg-black/5 disabled:text-[#86868b]",
};
/** Same look as <Button> for router links / anchors. */
export const btnPrimaryCls = "btn inline-flex items-center justify-center rounded-full bg-brand-700 px-5 py-2 text-sm text-white hover:bg-brand-800";
export const btnSecondaryCls = "btn inline-flex items-center justify-center rounded-full bg-white px-5 py-2 text-sm text-brand-700 ring-1 ring-inset ring-brand-700 hover:bg-[#f5f5f7]";
export function Button({
  variant = "primary",
  className,
  ...p
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type="button"
      {...p}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-full px-5 py-2 text-sm disabled:cursor-not-allowed",
        VARIANTS[variant],
        className,
      )}
    />
  );
}

export const inputCls =
  "block w-full rounded-[11px] border border-hairline bg-white px-3 py-2 text-sm placeholder:text-[#86868b] focus:border-brand-600 disabled:bg-[#f5f5f7]";

export function Field({
  label,
  error,
  hint,
  children,
}: {
  label: string;
  error?: string;
  hint?: string;
  children: (props: { id: string; "aria-invalid": boolean; "aria-describedby"?: string }) => ReactNode;
}) {
  const id = useId();
  const msgId = `${id}-msg`;
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-semibold text-[#333333]">
        {label}
      </label>
      {children({ id, "aria-invalid": !!error, "aria-describedby": error || hint ? msgId : undefined })}
      {(error || hint) && (
        <p id={msgId} className={cx("text-xs", error ? "text-red-600" : "text-[#6e6e73]")} role={error ? "alert" : undefined}>
          {error ?? hint}
        </p>
      )}
    </div>
  );
}

// -------------------------------------------------------------------- cards
export function Card({ title, actions, children, className }: { title?: string; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cx("rounded-[18px] border border-hairline bg-white ", className)}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-[#f0f0f0] px-4 py-3">
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          {actions}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-[28px] font-semibold leading-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-[#6e6e73]">{subtitle}</p>}
      </div>
      <div className="flex flex-wrap gap-2">{actions}</div>
    </div>
  );
}

const TONES: Record<string, string> = {
  draft: "bg-[#f5f5f7] text-[#333333]",
  scheduled: "bg-blue-100 text-blue-800",
  queued: "bg-amber-100 text-amber-800",
  sending: "bg-amber-100 text-amber-800",
  pending: "bg-amber-100 text-amber-800",
  published: "bg-green-100 text-green-800",
  accepted: "bg-green-100 text-green-800",
  cancelled: "bg-slate-200 text-[#333333]",
  failed: "bg-red-100 text-red-800",
  unknown: "bg-orange-100 text-orange-800",
  dry_run: "bg-purple-100 text-purple-800",
  overdue: "bg-red-100 text-red-800",
  due7: "bg-red-50 text-red-700",
  due30: "bg-amber-100 text-amber-800",
  due60: "bg-yellow-50 text-yellow-800",
  ok: "bg-green-100 text-green-800",
};
export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cx("inline-block rounded-full px-2 py-0.5 text-xs font-semibold", TONES[status] ?? "bg-[#f5f5f7] text-[#333333]")}>
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}

// -------------------------------------------------------------------- states
export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 p-6 text-sm text-[#6e6e73]">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-hairline border-t-brand-700" aria-hidden />
      {label}…
    </div>
  );
}
export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="rounded-[18px] border border-dashed border-hairline p-10 text-center">
      <p className="font-semibold text-[#333333]">{title}</p>
      {hint && <p className="mt-1 text-sm text-[#6e6e73]">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  const msg = error instanceof Error ? error.message : "Something went wrong";
  return (
    <div role="alert" className="rounded-[18px] border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      {msg}
      {retry && (
        <Button variant="secondary" className="ml-3" onClick={retry}>
          Retry
        </Button>
      )}
    </div>
  );
}

export function Pagination({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <nav aria-label="Pagination" className="mt-4 flex items-center justify-between text-sm text-[#333333]">
      <span>
        {total} result{total === 1 ? "" : "s"}
      </span>
      <div className="flex items-center gap-2">
        <Button variant="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </Button>
        <span>
          Page {page} of {pages}
        </span>
        <Button variant="secondary" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next
        </Button>
      </div>
    </nav>
  );
}

// ------------------------------------------------------------------- dialog
export function Dialog({ open, title, onClose, children, footer }: { open: boolean; title: string; onClose: () => void; children: ReactNode; footer?: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onClose={onClose}
      onCancel={onClose}
      className="m-auto w-full max-w-lg rounded-[18px] p-0"
    >
      {open && (
        <div className="p-5">
          <h2 id={titleId} className="text-lg font-semibold text-ink">
            {title}
          </h2>
          <div className="mt-3 text-sm text-[#333333]">{children}</div>
          <div className="mt-5 flex justify-end gap-2">{footer}</div>
        </div>
      )}
    </dialog>
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  danger,
  busy,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Dialog
      open={open}
      title={title}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant={danger ? "danger" : "primary"} onClick={onConfirm} disabled={busy}>
            {busy ? "Working…" : confirmLabel}
          </Button>
        </>
      }
    >
      {message}
    </Dialog>
  );
}

// -------------------------------------------------------------------- toast
interface Toast {
  id: number;
  kind: "success" | "error";
  text: string;
}
const ToastCtx = createContext<(kind: Toast["kind"], text: string) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((kind: Toast["kind"], text: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, kind, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div aria-live="polite" className="fixed bottom-4 right-4 z-50 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            role={t.kind === "error" ? "alert" : "status"}
            className={cx("rounded-[11px] px-4 py-3 text-sm shadow-lg", t.kind === "error" ? "bg-red-600 text-white" : "bg-ink text-white")}
          >
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function Table({ head, children }: { head: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-[18px] border border-hairline bg-white">
      <table className="min-w-full divide-y divide-hairline text-sm">
        <thead className="bg-[#fafafc] text-left text-xs font-semibold uppercase tracking-wide text-[#6e6e73]">
          <tr>
            {head.map((h) => (
              <th key={h} scope="col" className="px-4 py-2.5">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#f0f0f0]">{children}</tbody>
      </table>
    </div>
  );
}
export const Td = ({ children, className }: { children?: ReactNode; className?: string }) => (
  <td className={cx("px-4 py-2.5 align-top", className)}>{children}</td>
);
