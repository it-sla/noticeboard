export type Role = "SUPER_ADMIN" | "ADMIN" | "NOTICE_EDITOR" | "VIEWER";

export const ROLE_RANK: Record<Role, number> = {
  VIEWER: 0,
  NOTICE_EDITOR: 1,
  ADMIN: 2,
  SUPER_ADMIN: 3,
};

export const CATEGORIES = [
  "Holiday Notice",
  "General Announcement",
  "HR Notice",
  "Meeting",
  "Urgent Notice",
  "Policy Update",
  "Other",
] as const;
export const PRIORITIES = ["low", "normal", "high", "urgent"] as const;
export type Category = (typeof CATEGORIES)[number];
export type Priority = (typeof PRIORITIES)[number];
export type RecipientMode = "all" | "departments" | "employees";
export type NoticeStatus = "draft" | "scheduled" | "queued" | "published" | "cancelled";
export type JobStatus = "pending" | "sending" | "accepted" | "failed" | "unknown" | "dry_run";

export interface User {
  id: number;
  email: string;
  name: string;
  role: Role;
  is_active: boolean;
  last_login_at: string | null;
}
export interface Session {
  user: User;
  csrf_token: string;
}
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
export interface Department {
  id: number;
  name: string;
  is_active: boolean;
  employee_count: number;
}
export interface Employee {
  id: number;
  name: string;
  email: string;
  department_id: number | null;
  department_name: string | null;
  job_title: string | null;
  is_active: boolean;
}
export interface Attachment {
  id: number;
  original_filename: string;
  content_type: string;
  size_bytes: number;
}
export interface Notice {
  id: number;
  title: string;
  body_html: string;
  category: Category;
  priority: Priority;
  status: NoticeStatus;
  created_by_name: string | null;
  created_at: string;
  published_at: string | null;
  scheduled_at: string | null;
  archived_at: string | null;
  recipient_mode: RecipientMode;
  department_ids: number[];
  employee_ids: number[];
  attachments: Attachment[];
}
export type NoticeListItem = Omit<
  Notice,
  "body_html" | "recipient_mode" | "department_ids" | "employee_ids" | "attachments"
>;
export interface Preview {
  subject: string;
  html: string;
  text: string;
  sender: string;
  recipient_count: number;
  attachments: Attachment[];
  broadcast_enabled: boolean;
  email_mode: "dry_run" | "smtp";
}
export interface Job {
  id: number;
  notice_id: number;
  notice_title: string;
  recipient_name: string;
  recipient_email: string;
  status: JobStatus;
  attempt_count: number;
  last_attempt_at: string | null;
  accepted_at: string | null;
  error: string | null;
}
export interface ImportRow {
  row: number;
  name: string;
  email: string;
  department: string | null;
  status: string;
  message: string | null;
  new_department: boolean;
}
export interface ImportResult {
  committed: boolean;
  total: number;
  ok: number;
  skipped: number;
  errors: number;
  rows: ImportRow[];
}
export interface Template {
  id: number;
  name: string;
  subject_prefix: string;
  header_text: string;
  footer_text: string;
  is_default: boolean;
}
export type ExpiryCategory = "vehicle" | "staff" | "company" | "equipment";
export type ExpiryStatus = "overdue" | "due7" | "due30" | "due60" | "ok";
export interface ExpiryItem {
  id: number;
  category: ExpiryCategory;
  item_type: string;
  subject: string;
  employee_name: string | null;
  reference_no: string | null;
  issued_on: string | null;
  expires_on: string;
  reminder_days: number[];
  notes: string | null;
  is_archived: boolean;
  days_left: number;
  status: ExpiryStatus;
}
export interface ExpirySummary {
  overdue: number;
  due7: number;
  due30: number;
  due60: number;
  ok: number;
  total: number;
}
export interface ExpiryAlerts {
  count: number;
  items: { id: number; subject: string; item_type: string; expires_on: string; days_left: number }[];
}
export interface Renewal {
  id: number;
  old_expires_on: string;
  new_expires_on: string;
  cost: string | null;
  note: string | null;
  renewed_at: string;
}

export interface AppSettings {
  expiry_alerts_enabled: boolean;
  expiry_extra_recipients: string[];
  broadcast_enabled: boolean;
  email_mode: "dry_run" | "smtp";
  smtp_host: string;
  smtp_port: number;
  smtp_use_ssl: boolean;
  smtp_from_email: string;
  smtp_password_configured: boolean;
  rate_per_minute: number;
  rate_per_day: number;
  attachment_mode: string;
  timezone: string;
}
