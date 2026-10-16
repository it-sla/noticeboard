import { expect, test } from "@playwright/test";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

const mailFile = path.join(import.meta.dirname, ".tmp", "mail.jsonl");
const mails = () =>
  existsSync(mailFile)
    ? readFileSync(mailFile, "utf-8").split("\n").filter(Boolean).map((l) => JSON.parse(l))
    : [];

test("admin login -> import -> notice -> preview -> test send -> publish -> history", async ({ page }) => {
  // login
  await page.goto("/");
  await page.getByLabel("Email").fill("admin@corp.example.com");
  await page.getByLabel("Password").fill("e2e-password-123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  // broadcasting is off by default: enable it explicitly
  await page.getByRole("link", { name: "Settings" }).click();
  await page.getByRole("button", { name: "Enable broadcasting" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Enable", exact: true }).click();
  await expect(page.getByRole("button", { name: "Disable broadcasting" })).toBeVisible();

  // employee import (preview then commit)
  await page.getByRole("link", { name: "Employees" }).click();
  await page.getByRole("button", { name: "Import CSV/Excel" }).click();
  await page.getByLabel("Import file").setInputFiles(path.join(import.meta.dirname, "employees.csv"));
  await page.getByRole("button", { name: "Preview" }).click();
  await expect(page.getByText("3 new")).toBeVisible();
  await page.getByRole("button", { name: "Import 3" }).click();
  await expect(page.getByText("Sita Sharma")).toBeVisible();

  // create notice
  await page.getByRole("link", { name: "Create Notice" }).click();
  await page.getByLabel("Title").fill("Dashain holiday notice");
  await page.getByLabel("Category").selectOption("Holiday Notice");
  await page.getByRole("textbox", { name: "Notice body" }).click();
  await page.keyboard.type("कार्यालय दशैंको अवधिमा बन्द रहनेछ।");

  // preview shows subject, sender, exact count
  await page.getByRole("button", { name: "Preview" }).click();
  await expect(page.getByText("it@gohimalaya.travel")).toBeVisible();
  await expect(page.locator("dd", { hasText: /^3$/ })).toBeVisible();

  // test send goes to exactly one captured address
  await page.getByLabel("Send test email to one address").fill("tester@corp.example.com");
  await page.getByRole("button", { name: "Send test" }).click();
  await expect.poll(() => mails().length).toBe(1);
  expect(mails()[0].to).toEqual(["tester@corp.example.com"]);
  expect(mails()[0].subject).toContain("[TEST]");

  // explicit confirmation required
  await page.getByRole("button", { name: "Publish & Email" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("3 active employees")).toBeVisible();
  await expect(dialog.getByRole("button", { name: /Publish & email 3/ })).toBeDisabled();
  await dialog.getByRole("checkbox").check();
  await dialog.getByRole("button", { name: /Publish & email 3/ }).click();

  // worker delivers; detail page reaches Complete
  await expect(page.getByText("Complete")).toBeVisible({ timeout: 30_000 });
  await expect.poll(() => mails().length, { timeout: 30_000 }).toBe(4); // 1 test + 3 notices
  const real = mails().slice(1);
  expect(real.map((m) => m.to[0]).sort()).toEqual([
    "asha@corp.example.com",
    "bikash@corp.example.com",
    "sita@corp.example.com",
  ]);
  expect(real[0].text).toContain("कार्यालय दशैंको अवधिमा बन्द रहनेछ।");

  // history lists each recipient as accepted by SMTP
  await page.getByRole("link", { name: "Email History" }).click();
  await expect(page.getByText("Accepted by SMTP", { exact: true })).toHaveCount(3);
});

test("expiry tracker: add item -> bell badge -> renew -> bell clears", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Email").fill("admin@corp.example.com");
  await page.getByLabel("Password").fill("e2e-password-123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("link", { name: "Expiry Tracker" }).click();
  await expect(page.getByText("Nothing here yet")).toBeVisible();

  const soon = new Date(Date.now() + 3 * 86_400_000).toISOString().slice(0, 10);
  await page.getByRole("button", { name: "Add item" }).first().click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Type").fill("Insurance");
  await dialog.getByLabel("Vehicle (plate number)").fill("Ba 1 Cha 1234");
  await dialog.getByLabel("Expires on").fill(soon);
  await dialog.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Ba 1 Cha 1234")).toBeVisible();

  await expect(page.getByRole("button", { name: /1 urgent/ })).toBeVisible();
  await page.getByRole("button", { name: /1 urgent/ }).click();
  await expect(page.getByRole("dialog", { name: "Expiry notifications" }).getByText("Ba 1 Cha 1234")).toBeVisible();
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: "Renew" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "+1 year" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Save renewal" }).click();
  await expect(page.getByRole("button", { name: /0 urgent/ })).toBeVisible();
  await page.getByRole("button", { name: "History" }).click();
  await expect(page.getByRole("dialog").getByText("→")).toBeVisible();
});
