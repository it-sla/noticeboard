import { formatBytes, formatDateTime, nepalLocalToIso } from "../lib/format";

describe("format", () => {
  it("renders UTC timestamps in Asia/Kathmandu (+05:45)", () => {
    expect(formatDateTime("2026-12-01T00:00:00Z")).toContain("05:45");
  });
  it("converts a Nepal wall-clock input to an offset ISO string", () => {
    expect(nepalLocalToIso("2026-12-01T09:30")).toBe("2026-12-01T09:30:00+05:45");
    expect(new Date(nepalLocalToIso("2026-12-01T09:30")).toISOString()).toBe("2026-12-01T03:45:00.000Z");
  });
  it("formats bytes and empty dates", () => {
    expect(formatBytes(2048)).toBe("2 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
    expect(formatDateTime(null)).toBe("—");
  });
});
