---
paths:
  - "docs/**/*.md"
  - "*.md"
  - ".claude/**/*.md"
---

# Documentation rules

- Docs describe what the code **does now**. If you change behaviour, change the doc in the same task.
- No placeholder files and no aspirational claims: unimplemented items are listed as such in `docs/01-REQUIREMENTS.md`
  and `docs/12-FUTURE-ROADMAP.md`.
- `docs/PROGRESS.md` is append-only per work session: completed work, files, commands + real results, blockers, next action.
  Mark anything not run as UNVERIFIED.
- `docs/TASKS.md` statuses: TODO · IN_PROGRESS · DONE · BLOCKED · UNVERIFIED (implemented but a required check could not run).
- Keep `CLAUDE.md` under 200 lines; link to docs instead of duplicating them.
- Commands in docs must be copy-pasteable and tested at least once; mark OS-specific ones.
- Never put secrets, real employee data or real email addresses in docs or fixtures.
