# ADR-001: Technology stack and modular monolith

Status: accepted (2026-10-15)

## Context
Small internal tool (hundreds of employees, a few notices per week) on a single Ubuntu Docker host, maintained mostly with
Claude Code. Needs reliable email, auditability, and low operational overhead.

## Decision
- One Python/FastAPI codebase with a React SPA; PostgreSQL 16; Alembic; Docker Compose. API and worker are two processes of the
  same image. No microservices, message broker or workflow engine.
- Libraries chosen for maturity and few moving parts: SQLAlchemy 2, Pydantic 2, argon2-cffi, nh3 (Rust HTML sanitiser, allow-list),
  Jinja2 (autoescaped email template), openpyxl (xlsx import), TipTap (rich text), TanStack Query, React Hook Form + Zod.
- Tests run on SQLite through the real Alembic migration so they are fast and need no services; PostgreSQL-only behaviour is
  verified separately (and flagged UNVERIFIED where it was not).

## Consequences
+ One deployable unit, simple recovery, easy for another session to understand.
+ Fast feedback loop locally on Windows without Docker.
− PostgreSQL row-locking semantics are only exercised in production-like runs.
− Newer major versions (React Router 8, Vite 8, TypeScript 6) were adopted; lockfile pins them.

## Alternatives considered
Django (heavier, different ORM), Node/NestJS (team uses Python for automation), microservices/Kubernetes (no scale need).
