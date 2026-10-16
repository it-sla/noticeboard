import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { NotificationBell } from "../components/NotificationBell";

const json = (body: unknown) =>
  new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });

function setup(alerts: unknown) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => json(alerts));
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>
        <NotificationBell />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
afterEach(() => vi.restoreAllMocks());

describe("NotificationBell", () => {
  it("shows the urgent count and lists the items", async () => {
    setup({ count: 2, items: [
      { id: 1, subject: "Ba 1 Cha 1234", item_type: "Insurance", expires_on: "2026-10-10", days_left: -6 },
      { id: 2, subject: "Ram", item_type: "Driving licence", expires_on: "2026-10-20", days_left: 4 },
    ] });
    const bell = await screen.findByRole("button", { name: /2 urgent/i });
    await userEvent.click(bell);
    expect(screen.getByText("Ba 1 Cha 1234")).toBeInTheDocument();
    expect(screen.getByText(/6 days overdue/)).toBeInTheDocument();
    expect(screen.getByText(/in 4 days/)).toBeInTheDocument();
  });

  it("shows no badge and a calm message when nothing is urgent", async () => {
    setup({ count: 0, items: [] });
    const bell = await screen.findByRole("button", { name: /0 urgent/i });
    expect(bell).not.toHaveTextContent("0");
    await userEvent.click(bell);
    expect(screen.getByText(/Nothing is overdue/)).toBeInTheDocument();
  });
});
