// Compile-time configuration for the frontend.
//
// API_BASE is derived from the VITE_API_BASE_URL environment variable at
// build time. Set it to the backend URL in the deploy environment:
//
//   VITE_API_BASE_URL=https://your-api.onrender.com
//
// If unset (local development), API_BASE falls back to "/api", which the
// Vite dev server proxies to http://localhost:8000 via vite.config.ts.
//
// The value is normalized so there is never a trailing slash, and it always
// ends with "/api".

export const CURRENCY = "GHS";

const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";
const trimmed = raw.replace(/\/+$/, ""); // strip trailing slashes

export const API_BASE = trimmed ? `${trimmed}/api` : "/api";