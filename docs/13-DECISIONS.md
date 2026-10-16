# Decision log

Architecturally significant decisions have ADRs in `ADR/`. Smaller ones are recorded here (newest last).

| # | Decision | Why | Trade-off |
|---|---|---|---|
| D1 | Stack as specified; React Router **8**, Vite 8, TS 6, Tailwind 4, Vitest 5 | latest releases at build time (2026-10-15); all tests green | newer majors; pin via `package-lock.json` |
| D2 | Server-side sessions in DB (not JWT) | revocation, simple CSRF, matches "HttpOnly cookie sessions" | one DB read per request |
| D3 | Single `role` column on `users` (no role-assignment table) | four fixed roles, no multi-role need | changing to multi-role needs a migration |
| D4 | `repositories/` left empty | ORM in services is enough at this size; avoids pass-through layer | revisit if query code duplicates |
| D5 | Recipients for scheduled notices resolved at fire time | audience should reflect leavers/joiners at send time; revalidation required anyway | what is sent can differ from what was previewed at scheduling |
| D6 | Publish requires `expected_recipient_count` | guarantees "what you confirmed is what is sent" | extra 409 + re-confirm when directory changes |
| D7 | Default `ATTACHMENT_MODE=attach` | employees have no accounts yet, so protected links would be unusable | larger mails; Hostinger size limits apply (15 MB total cap) |
| D8 | DB-backed rate limits: email sends counted from `email_attempts`; login throttle via `audit_logs`/`users` | persists across restarts, no Redis | extra queries; approximate under concurrency |
| D9 | Test/dev domains `corp.example.com`; `.test` rejected by email-validator | reserved, cannot receive mail | none |
| D10 | Editor page uses `/notices/new/edit` + redirect with `location.state` | router remounts on redirect; state must survive | slightly indirect |
| D11 | `unknown` outcomes never auto-retried; retry needs explicit opt-in | avoids duplicate emails to employees | manual reconciliation work |
| D12 | Dry-run is a worker/mailer mode (`dry_run` job status), not a separate code path | exercises the whole pipeline safely | UI must label dry-run clearly |
| D13 | Bundle not code-split (865 kB) | internal tool; simplicity | lazy-load TipTap if it ever matters |
| D14 | One Playwright spec for the critical path | speed and stability | other UI flows covered by unit tests only |
