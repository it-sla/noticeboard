import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { api } from "../lib/api";
import { daysLabel, formatDate } from "../lib/format";
import type { ExpiryAlerts } from "../types";

/** Bell with a badge of overdue / due-within-7-days items. Renewing an item clears it. */
export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const q = useQuery({
    queryKey: ["expiry-alerts"],
    queryFn: () => api.get<ExpiryAlerts>("/expiry/alerts"),
    refetchInterval: 60_000,
  });
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);
  const count = q.data?.count ?? 0;
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label={`Expiry notifications, ${count} urgent`}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="relative flex h-11 w-11 items-center justify-center rounded-full bg-white text-ink ring-1 ring-inset ring-hairline hover:bg-[#f5f5f7]"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.7 21a2 2 0 0 1-3.4 0" />
        </svg>
        {count > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-[#d70015] px-1 text-xs font-semibold text-white">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>
      {open && (
        <div role="dialog" aria-label="Expiry notifications" className="absolute right-0 z-40 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-[18px] border border-hairline bg-white p-3">
          <div className="px-1 pb-2 text-sm font-semibold text-ink">Needs attention</div>
          {count === 0 ? (
            <p className="px-1 py-3 text-sm text-[#6e6e73]">Nothing is overdue or due within 7 days.</p>
          ) : (
            <ul className="divide-y divide-[#f0f0f0]">
              {q.data!.items.map((i) => (
                <li key={i.id} className="px-1 py-2 text-sm">
                  <div className="font-semibold text-ink">{i.subject}</div>
                  <div className="text-[#6e6e73]">{i.item_type}</div>
                  <div className={i.days_left < 0 ? "text-[#d70015]" : "text-[#333333]"}>
                    {formatDate(i.expires_on)} · {daysLabel(i.days_left)}
                  </div>
                </li>
              ))}
            </ul>
          )}
          <Link to="/expiry" onClick={() => setOpen(false)} className="mt-2 block rounded-full px-1 py-2 text-sm text-brand-700 hover:underline">
            Open Expiry Tracker
          </Link>
        </div>
      )}
    </div>
  );
}
