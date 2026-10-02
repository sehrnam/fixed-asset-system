import { Disposal, DisposalCreate } from "./types";

import { API_BASE } from "../../config";

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const b = await res.json();
      if (b && typeof b.detail === "string") detail = b.detail;
    } catch {}
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export const disposalsApi = {
  list: (status?: string) =>
    req<Disposal[]>(`/disposals${status ? `?status=${status}` : ""}`),
  get: (id: number) => req<Disposal>(`/disposals/${id}`),
  create: (payload: DisposalCreate) =>
    req<Disposal>("/disposals", { method: "POST", body: JSON.stringify(payload) }),
  approve: (id: number) => req<Disposal>(`/disposals/${id}/approve`, { method: "POST" }),
  reject: (id: number) => req<Disposal>(`/disposals/${id}/reject`, { method: "POST" }),
};