# Admin user guide

## Sign in
Open the site and sign in with the account your Super Admin created. After 5 wrong passwords the account locks for 15 minutes.

## One-time setup (Admin)
1. **Departments** → add your departments (any names).
2. **Employees** → *Import CSV/Excel*. Columns: `Name`, `Email` (required), `Department`, `Job Title`. Click **Preview**: green rows
   will be created, amber rows are skipped (already exist / duplicate in file / invalid email). Click **Import N**. Existing employees
   are never changed by an import. Unknown departments are created.
3. **Templates** → set the organisation name shown in the email header, an optional subject prefix and the footer text.

## Send a notice
1. **Create Notice** → title, category, priority, body (bold, headings, lists, links). Nepali text works.
2. Choose **Recipients**: all active employees, selected departments, or selected employees. Inactive employees are never included.
3. Optional: **upload a photo of your physical notice board notice** (PNG/JPG). Save the draft first, then use *Image & attachments*. The photo is resized (max 1600 px), stripped of location data and shown inside the email and on the notice page; a notice may be image-only (no text needed). You can also attach PDF/Word/Excel/PowerPoint/text files (up to 20 MB each, 15 MB total; sent as real attachments).
4. **Preview** shows the subject, the rendered email, sender, attachment list and the **exact recipient count**.
5. **Send test** emails the preview to *one* address you type (never the directory). Disabled until an Admin and the mode allows it.
6. **Publish & Email** opens a confirmation: tick the box confirming the count and press the button. The audience and content are
   frozen at that moment; later directory changes do not affect this notice.
7. You land on the notice page with live **sending progress**. When everything has left "pending", the notice shows **Published**.
   "Accepted by SMTP" means the mail server accepted it - not that it reached the inbox.

**Schedule** instead: pick a time in Nepal time and press *Schedule*. Cancel a scheduled notice from its page before it fires.
If broadcasting is switched off or nobody matches when the time comes, the notice goes back to *Draft* instead of sending.

## Watch and fix delivery
- **Dashboard**: live counts, recent activity, failed-email warnings.
- **Email History**: one row per recipient; filter by status/date/recipient; **Export CSV**; **Retry** a failed row.
  "Unknown outcome" rows may already have been delivered; check before using *Retry…*.

## Expiry Tracker
Sidebar → **Expiry Tracker**. Add anything that expires: vehicle registration (bluebook), insurance, pollution test, driving licences,
company licences, contracts, fire-extinguisher refills, domain/software renewals. Enter the **expiry date** (and optionally number, issue date,
reminder days). The tiles show Overdue / 7 / 30 / 60 days / OK; click a tile to filter. When you renew, press **Renew** (+6 months / +1 year or
a date, optional cost) - the old date stays in **History**. The **bell** at the top right shows overdue items and those due within 7 days, and
admins get a daily email when a reminder date is reached (Settings → Expiry reminders). Dates are entered in AD (the normal calendar).

## Other actions
Duplicate a notice (copies text and audience, not attachments) · Archive/Unarchive · Deactivate employees (history kept).

## Roles
Viewer reads published notices · Notice Editor drafts and previews · Admin publishes, manages people and sees history ·
Super Admin also manages users, SMTP check and the **broadcasting switch** (Settings). While broadcasting is disabled, nothing is sent.

## Messages you may see
"Email broadcasting is disabled" → ask a Super Admin. "Recipient count changed" → the directory changed while you were reviewing; re-check the preview and confirm again. "Dry-run mode" → the system is configured not to send real email.
