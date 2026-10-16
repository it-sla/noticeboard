export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
  }
}

let csrf = "";
export const setCsrf = (token: string) => {
  csrf = token;
};

type Params = Record<string, string | number | boolean | undefined | null>;

export function qs(params?: Params): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  let payload: BodyInit | undefined;
  if (body instanceof FormData) payload = body;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  if (method !== "GET" && csrf) headers["X-CSRF-Token"] = csrf;
  const res = await fetch(`/api${path}`, { method, headers, body: payload, credentials: "include" });
  if (res.status === 204) return undefined as T;
  const isJson = res.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await res.json() : null;
  if (!res.ok) {
    const e = data?.error;
    throw new ApiError(res.status, e?.code ?? "error", e?.message ?? res.statusText, e?.details);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, params?: Params) => request<T>("GET", path + qs(params)),
  post: <T>(path: string, body?: unknown, params?: Params) =>
    request<T>("POST", path + qs(params), body ?? {}),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, body),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
  del: <T>(path: string) => request<T>("DELETE", path),
  upload: <T>(path: string, file: File, params?: Params) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<T>("POST", path + qs(params), fd);
  },
};

export const errorMessage = (e: unknown) =>
  e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Something went wrong";
