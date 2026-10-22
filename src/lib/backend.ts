// Server-side helper for Next.js route handlers that forward to the local FastAPI NLP service.
export const NLP_API_URL = process.env.NLP_API_URL || "http://127.0.0.1:8000";

export async function forward(path: string, init: RequestInit & { cookie?: string | null } = {}) {
  const { cookie, ...rest } = init;
  return fetch(NLP_API_URL + path, {
    ...rest,
    headers: { ...(rest.headers || {}), ...(cookie ? { cookie } : {}) },
    cache: "no-store",
  });
}
