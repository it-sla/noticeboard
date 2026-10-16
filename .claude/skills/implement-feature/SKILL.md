---
name: implement-feature
description: Implement a feature or fix in the Notice Board as a verified vertical slice (task lookup, rules, code, tests, docs, progress update). Use for any non-trivial change request.
---

# implement-feature

## Prerequisites
- Repo at `employee-notice-board/`; backend venv exists (`bash scripts/dev/setup.sh`) and `npm install` done.
- You have read `CLAUDE.md`, `docs/TASKS.md`, `docs/PROGRESS.md`, and the `.claude/rules/*` matching the files you will touch.

## Procedure
1. Find or add the task in `docs/TASKS.md` (ID, acceptance criteria, dependencies). Set it IN_PROGRESS.
2. Design the smallest slice: schema (Alembic) → service → route (+ `require_role`) → types → UI → tests.
3. Write the failing test first when fixing a bug; otherwise add tests alongside the code.
4. Implement. Reuse `paginate`, `audit`, `ApiError`, `ui.tsx`. No new dependency unless unavoidable.
5. Run: `bash scripts/test/run.sh backend-lint backend-test` (one step per call), then the frontend steps if UI changed,
   `migrations` if models changed.
6. For auth/sending/upload/migration changes run the matching reviewer subagent; record what actually ran.
7. Update affected docs, `CHANGELOG.md` (user-visible), `docs/TASKS.md`, append to `docs/PROGRESS.md`.

## Commands
`bash scripts/test/run.sh <backend-lint|backend-test|migrations|frontend-lint|frontend-typecheck|frontend-test|frontend-build|e2e|all>`

## Evidence of success
Command output showing the steps passing (counts of tests), updated TASKS/PROGRESS with those results, docs matching code.

## Failure handling
- Test fails: fix root cause; never weaken the assertion to pass. Unrelated failure: record in PROGRESS as a blocker.
- Tool/service unavailable (Docker, PostgreSQL, network): mark the task UNVERIFIED with the reason and continue.
- Never send real email, deploy, or touch production to "verify".
