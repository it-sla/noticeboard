import { defineConfig } from "@playwright/test";

// LOCAL end-to-end only: backend runs on SQLite with SMTP pointed at a local capture sink.
const py = process.env.E2E_PYTHON ?? "../backend/.venv/Scripts/python.exe";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: "http://localhost:5173", trace: "retain-on-failure" },
  webServer: [
    { command: `"${py}" ../scripts/test/smtp_capture.py 1025 e2e/.tmp/mail.jsonl`, port: 1025, reuseExistingServer: false },
    { command: `"${py}" ../scripts/test/e2e_backend.py`, url: "http://127.0.0.1:8000/api/health", timeout: 90_000, reuseExistingServer: false },
    { command: "npm run dev -- --host localhost", url: "http://localhost:5173", reuseExistingServer: false },
  ],
});
