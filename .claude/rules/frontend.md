---
paths:
  - "frontend/src/**/*.{ts,tsx,css}"
---

# Frontend rules

- Visual design follows `/DESIGN.md` (Apple-inspired: one blue accent, pill buttons, hairline 18px cards, no shadows, weights 400/600). Use `Button`, `btnPrimaryCls`/`btnSecondaryCls`, `inputCls`, `Card` from `components/ui.tsx`; do not hand-roll colours.
- TypeScript strict; no `any`. API types live in `src/types/index.ts` and mirror `backend/app/schemas/common.py`.
- All HTTP goes through `src/lib/api.ts` (adds credentials + CSRF header). Never call `fetch` directly in components.
- Server state with TanStack Query (queryKeys per resource; invalidate after mutations). Local UI state with `useState`.
- Forms: React Hook Form + Zod; show field errors in `<Field>` (`role="alert"`), map server errors to toasts.
- Accessibility: labelled controls (`Field`), native `<dialog>` via `Dialog`/`ConfirmDialog`, `aria-live` toasts,
  keyboard operable, visible focus, tables with `<th scope>`. Don't convey state by colour alone (badges carry text).
- Every list has loading (`Spinner`), empty (`EmptyState`) and error (`ErrorState`) states.
- Destructive or outward actions (publish, cancel, deactivate, enable broadcasting) require a confirmation dialog.
- UI role guards are convenience only; the backend is the authority. Never hide a security rule in the UI.
- Render notice HTML only from server-sanitised fields; previews go in a `sandbox` iframe.
- Dates: store/send UTC ISO; display with `lib/format.ts` (Asia/Kathmandu). Scheduling input is Nepal wall-clock → `nepalLocalToIso`.
- Check with `npm run lint && npm run typecheck && npm test && npm run build`.
