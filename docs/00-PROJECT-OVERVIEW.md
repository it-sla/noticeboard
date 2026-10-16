# Project overview

**Employee Notice Board** — an internal system for Shangri La Tours / UPS Nepal to publish company notices (holidays,
circulars, meetings, urgent and HR announcements, department notices) and email them to employees.

## What it does
1. Admin writes a notice (rich text, Nepali/Unicode supported), picks a category/priority, attaches files.
2. Admin selects recipients: all active employees, selected departments, or selected employees.
3. Preview shows subject, rendered email, **exact recipient count**, attachments and the sender address.
4. **Publish & Email** (explicit confirmation) freezes the content and the recipient list and creates one durable email job
   per recipient. A worker sends each message individually through the Hostinger mailbox `it@gohimalaya.travel`.
5. Dashboard and Email History show progress and per-recipient results. Notices can also be scheduled (Asia/Kathmandu).

## What it deliberately does not do
- No UPS API, no UPS website automation/scraping, no UPS branding.
- No n8n, Redis or Celery in the first version (clean seams exist; see ADR-004 and the roadmap).
- No claim of inbox delivery: "Accepted by SMTP" only means the mail server took the message. Bounces/read receipts are not tracked.
- No real email until an operator sets `EMAIL_MODE=smtp` on the server **and** a Super Admin enables broadcasting.

## Components
| Component | Tech | Runs as |
|---|---|---|
| API | FastAPI | `backend` container |
| Email worker + scheduler | same image, `python -m app.workers.email_worker` | `worker` container |
| Database | PostgreSQL 16 | `db` container, volume `pgdata` |
| SPA | React/Vite, served by nginx | `frontend` container |
| HTTPS proxy | Caddy | `proxy` container (80/443) |

See `02-ARCHITECTURE.md` for diagrams of the flows and `01-REQUIREMENTS.md` for the feature status matrix.
