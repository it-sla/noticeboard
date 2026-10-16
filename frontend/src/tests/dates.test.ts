import { addMonths, daysLabel } from "../lib/format";

describe("date helpers", () => {
  it("adds months without overflowing short months", () => {
    expect(addMonths("2026-01-31", 1)).toBe("2026-02-28");
    expect(addMonths("2026-10-16", 12)).toBe("2027-10-16");
    expect(addMonths("2028-02-29", 12)).toBe("2029-02-28");
    expect(addMonths("2026-10-16", 6)).toBe("2027-04-16");
  });
  it("labels days left and overdue", () => {
    expect(daysLabel(-1)).toBe("1 day overdue");
    expect(daysLabel(-5)).toBe("5 days overdue");
    expect(daysLabel(0)).toBe("today");
    expect(daysLabel(1)).toBe("in 1 day");
    expect(daysLabel(30)).toBe("in 30 days");
  });
});
