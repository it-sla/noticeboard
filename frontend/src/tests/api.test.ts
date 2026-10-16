import { api, ApiError, setCsrf } from "../lib/api";

const ok = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

afterEach(() => vi.restoreAllMocks());

describe("api client", () => {
  it("sends the CSRF header on unsafe requests only", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockImplementation(async () => ok({}));
    setCsrf("tok123");
    await api.get("/employees");
    await api.post("/departments", { name: "HR" });
    expect((f.mock.calls[0][1]!.headers as Record<string, string>)["X-CSRF-Token"]).toBeUndefined();
    expect((f.mock.calls[1][1]!.headers as Record<string, string>)["X-CSRF-Token"]).toBe("tok123");
    expect(f.mock.calls[1][1]!.credentials).toBe("include");
  });
  it("maps the error envelope to ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => ok({ error: { code: "duplicate_email", message: "Exists", details: null } }, 409));
    await expect(api.post("/employees", {})).rejects.toMatchObject({ status: 409, code: "duplicate_email", message: "Exists" });
    await expect(api.post("/employees", {})).rejects.toBeInstanceOf(ApiError);
  });
});
