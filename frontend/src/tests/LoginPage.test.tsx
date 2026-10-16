import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { AuthProvider } from "../app/auth";
import { LoginPage } from "../pages/LoginPage";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

function setup(fetchImpl: (url: string) => Response) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => fetchImpl(String(input)));
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AuthProvider>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("LoginPage", () => {
  it("validates before calling the API", async () => {
    const calls: string[] = [];
    setup((u) => (calls.push(u), json({ error: { code: "not_authenticated", message: "no" } }, 401)));
    await userEvent.click(await screen.findByRole("button", { name: /sign in/i }));
    expect(await screen.findByText("Email is required")).toBeInTheDocument();
    expect(screen.getByText("Password is required")).toBeInTheDocument();
    expect(calls.some((u) => u.includes("/auth/login"))).toBe(false);
  });

  it("shows the server's generic error on bad credentials", async () => {
    setup((u) =>
      u.includes("/auth/login")
        ? json({ error: { code: "invalid_credentials", message: "Invalid email or password" } }, 401)
        : json({ error: { code: "not_authenticated", message: "no" } }, 401),
    );
    await userEvent.type(await screen.findByLabelText("Email"), "a@corp.example.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Invalid email or password"));
  });
});
