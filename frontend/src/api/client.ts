const BASE = "/api";

export type User = {
  user_id: string;
  display_name: string;
  email: string;
  created_at: string;
};
export type RegisterRequest = { display_name: string; email: string; password: string };
export type LoginRequest = { email: string; password: string };
export type LoginResponse = { message: string; user: User };
export type Mode = "guest" | "member";
export type Usage = { mode: Mode; limit: number; used: number; remaining: number; reset_at: number };
export type Thread = { thread_id: string; created_at: string };
export type CreatedThread = { thread_id: string; message: string };
export type History = { thread_id: string; messages: { role: "user" | "assistant"; content: string }[] };
export type ChatResponse = { thread_id: string; answer: string; usage?: { limit: number; remaining: number; reset_at: number } };

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(status: number, message: string, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function explain(data: unknown): { message: string; code?: string } {
  if (typeof data === "string") return { message: data };
  if (!data || typeof data !== "object") return { message: "Request failed." };
  const outer = data as Record<string, unknown>;
  const detail = outer.detail;
  if (typeof detail === "string") return { message: detail };
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const x = detail as Record<string, unknown>;
    return {
      message: typeof x.message === "string" ? x.message : "Request failed.",
      code: typeof x.code === "string" ? x.code : undefined,
    };
  }
  if (Array.isArray(detail)) {
    return { message: detail.map((x: unknown) => {
      if (x && typeof x === "object" && "msg" in x) return String(x.msg);
      return "Invalid input";
    }).join(". ") };
  }
  return { message: typeof outer.message === "string" ? outer.message : "Request failed." };
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body != null && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(BASE + path, { ...options, headers, credentials: "same-origin" });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") throw error;
    throw new ApiError(0, "Cannot connect to the server. Confirm FastAPI is running on port 8000.");
  }
  const body = await response.text();
  let data: unknown;
  try { data = body ? JSON.parse(body) as unknown : null; } catch { data = body; }
  if (!response.ok) {
    const { message, code } = explain(data);
    throw new ApiError(response.status, message, code);
  }
  return data as T;
}

async function csrf(mode: Mode): Promise<string> {
  const result = await request<{ csrf_token: string }>(mode === "guest" ? "/guest/csrf-token" : "/csrf-token");
  if (!result || typeof result.csrf_token !== "string") throw new Error("Invalid CSRF token response.");
  return result.csrf_token;
}
async function mutation<T>(mode: Mode, path: string, method: "POST" | "DELETE", payload?: unknown): Promise<T> {
  const token = await csrf(mode);
  return request<T>(path, {
    method,
    headers: { "X-CSRF-Token": token },
    ...(payload === undefined ? {} : { body: JSON.stringify(payload) }),
  });
}

export const authApi = {
  register: (payload: RegisterRequest) => request<User>("/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload: LoginRequest) => request<LoginResponse>("/login", { method: "POST", body: JSON.stringify(payload) }),
  me: (signal?: AbortSignal) => request<User>("/me", { signal }),
  logout: () => mutation<{ message: string }>("member", "/logout", "POST"),
};

export const guestApi = {
  session: () => request<{ mode: "guest"; limit: number; remaining: number }>("/guest/session", { method: "POST" }),
};

export const chatApi = {
  usage: () => request<Usage>("/usage"),
  threads: (mode: Mode) => request<Thread[]>(mode === "guest" ? "/guest/threads" : "/threads"),
  create: (mode: Mode) => mutation<CreatedThread>(mode, mode === "guest" ? "/guest/threads" : "/threads", "POST"),
  history: (mode: Mode, id: string) => request<History>(`${mode === "guest" ? "/guest/threads" : "/threads"}/${encodeURIComponent(id)}/messages`),
  send: (mode: Mode, id: string, message: string) => mutation<ChatResponse>(mode, mode === "guest" ? "/guest/chat" : "/chat", "POST", { thread_id: id, message }),
  delete: (id: string) => mutation<{ status: string }>("member", `/threads/${encodeURIComponent(id)}`, "DELETE"),
};
