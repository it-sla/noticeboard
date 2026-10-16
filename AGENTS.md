# AGENTS.md — working agreements for coding agents

Applies to Claude Code sessions and any subagent. Entry point is `CLAUDE.md`.

## Responsibilities
- Understand before editing: read `docs/TASKS.md`, `docs/PROGRESS.md`, the matching `.claude/rules/*`.
- Deliver vertical slices (API + UI + tests + docs), not scaffolding.
- Keep the repo runnable at every commit: `bash scripts/test/run.sh all` is the gate.
- Report faithfully. A skipped or unavailable check is **UNVERIFIED**, never "passed".
- Stop and ask before anything outward-facing: real email, deploys, DNS, live mailbox/DB access, pushing.

## File ownership / safe parallel work
Two agents may work in parallel only when their write sets are disjoint:

| Area | Paths | Notes |
|---|---|---|
| Schema + models | `backend/app/models/`, `backend/alembic/` | One agent at a time; migration numbers must stay linear |
| API + services | `backend/app/api/`, `services/`, `schemas/`, `core/` | Coordinate on `schemas/common.py` |
| Worker/delivery | `services/delivery.py`, `mailer.py`, `workers/` | Changes need delivery tests |
| Frontend | `frontend/src/` | `types/index.ts` mirrors `schemas/common.py` — change both in one task |
| Infra/scripts | `infra/`, `scripts/`, `*/Dockerfile` | |
| Docs/harness | `docs/`, `.claude/`, `CLAUDE.md` | `PROGRESS.md`/`TASKS.md` are single-writer: the coordinating agent |

Reviewer subagents (`.claude/agents/*`) are read-only; they report, they do not edit.

## Coding standards
- Python: ruff (`E,F,I,B,UP,S`), 100 cols, type hints on public functions. TypeScript: strict, no `any`.
- Prefer the smallest change that works; reuse existing helpers (`paginate`, `audit`, `ApiError`, `ui.tsx`).
- No new dependency unless stdlib/installed packages cannot do it; record why in `docs/13-DECISIONS.md`.
- Errors use `ApiError(status, code, message)`; the response envelope is `{"error": {code, message, details}}`.
- Never log message bodies, recipient lists or secrets.

## Review requirements
Before marking a task done run the matching reviewer when the change touches auth/permissions, sending, migrations,
uploads or user-facing flows: `security-reviewer`, `backend-reviewer`, `frontend-reviewer`, `qa-reviewer`,
`architect` (design tradeoffs). Record in `docs/PROGRESS.md` which reviews **actually ran** and their findings.

## Testing expectations
Backend behaviour → pytest (fake mailer or aiosmtpd; never real SMTP). UI logic → Vitest. Cross-stack flows → Playwright
against the local stack only. Details: `docs/08-TESTING-STRATEGY.md`.

## Change documentation
Update in the same change: affected `docs/*.md`, `CHANGELOG.md` (user-visible), `docs/TASKS.md` status, and append to
`docs/PROGRESS.md` (what changed, files, commands run + results, blockers, next action). Decisions with trade-offs get a
line in `docs/13-DECISIONS.md` (or an ADR if architectural).

## Handoff and recovery
A fresh session must be able to resume from the repo alone:
1. `docs/PROGRESS.md` → "Next action" and "Blockers".
2. `docs/TASKS.md` → first non-DONE task with satisfied dependencies.
3. `git status`/`git log` for uncommitted work; run `bash scripts/test/run.sh all` to learn the real baseline.
If context is running out: write exact state to PROGRESS/TASKS/IMPLEMENTATION-PLAN before stopping.
