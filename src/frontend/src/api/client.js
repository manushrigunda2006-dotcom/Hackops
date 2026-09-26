// Thin fetch wrapper. The real UI authenticates with a normal session
// cookie set at login. The acceptance checker never uses this file at
// all — it hits the backend directly with the raw headers listed in
// .dogfood.toml. Both paths have to be honored by the same backend
// middleware, so keep this dumb and let the backend own auth logic.

const BASE = ""; // same-origin; vite dev proxy forwards /api to the backend

async function request(path, { method = "GET", body, headers = {} } = {}) {
  const res = await fetch(BASE + path, {
    method,
    credentials: "include", // send the session cookie
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  const contentType = res.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await res.json().catch(() => null)
    : await res.text();

  if (!res.ok) {
    const message =
      (data && typeof data === "object" && data.detail) ||
      (typeof data === "string" && data) ||
      `Request failed (${res.status})`;
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }

  return data;
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
  patch: (path, body) => request(path, { method: "PATCH", body }),
  delete: (path) => request(path, { method: "DELETE" }),
};
