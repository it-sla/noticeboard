# ADR-003: Server-side sessions, role ranks, CSRF header

Status: accepted (2026-10-15)

## Decision
- Argon2id password hashes; opaque random session token in an HttpOnly cookie; server stores only its SHA-256 in `sessions`
  with idle (2 h) and absolute (12 h) expiry. Revocation = delete the row.
- CSRF: per-session token compared to the `X-CSRF-Token` header on unsafe methods, plus Origin allow-list; SameSite=Lax.
- Authorization: four roles in a strict hierarchy (VIEWER < NOTICE_EDITOR < ADMIN < SUPER_ADMIN) checked by `require_role`.
  Ownership rule: editors may modify only drafts they created.
- Lockout (per account) and failure throttle (per IP) stored in the database; no external rate-limit service.
- First Super Admin only via CLI with a password supplied at deploy time; no default credentials, no open registration.

## Consequences
+ Immediate revocation, no token-signing keys to manage, easy to audit.
− A DB lookup per request (negligible at this scale); lockout can be abused to inconvenience a known user.
− No MFA/SSO/password-reset flow yet (roadmap).

## Alternatives
JWT access/refresh tokens (harder revocation, more moving parts); an external IdP/SSO (not available now, can be added in front later).
