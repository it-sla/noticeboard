---
name: review-security
description: Security review of the Notice Board changes - auth, authorization, CSRF/sessions, injection/XSS, uploads, secrets, email-sending safeguards, deployment config. Use before merging changes in those areas and before first production deployment.
---

# review-security

## Prerequisites
- A diff or file list to review (`git diff`, or the whole repo for a pre-deployment audit).
- `docs/07-SECURITY.md` and `.claude/rules/security.md` read.

## Procedure
1. Delegate to the `security-reviewer` subagent with the scope (files/diff). If subagents are unavailable, do the checklist inline.
2. Verify mechanically:
   - `grep -rn "require_role\|current_auth" backend/app/api` → every route is covered (public: `/auth/login`, `/health`).
   - `grep -rniE "password|secret|token" backend/app --include=*.py` → no logging/printing of values.
   - `git ls-files | grep -E "^\.env"` → only `.env.example` tracked.
   - `bash scripts/test/run.sh backend-test` → authorization and CSRF tests pass.
3. Check email safeguards: publish needs `confirm` + matching count + `broadcast_enabled`; test-send single address; dry-run default.
4. Check infra: Postgres has no published port in `infra/compose.production.yaml`; containers run as non-root; prod guards in `core/config.py`.
5. Record findings in `docs/PROGRESS.md` with severity, and fix blockers/majors in code with tests.

## Evidence of success
List of reviewed areas, commands run with results, findings fixed or accepted (with rationale). State what was NOT reviewed.

## Failure handling
Do not claim a review happened if the subagent or commands did not run. A blocker finding stops deployment tasks.
