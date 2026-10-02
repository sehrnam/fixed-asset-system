import { Asset, AssetInput, Category } from "./types";

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
      const body = await res.json();
      if (body && typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail)) detail = body.detail.map((e: any) => e.msg).join("; ");
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export const categoriesApi = {
  list: () => req<Category[]>("/categories"),
  create: (payload: { name: string; description?: string | null }) =>
    req<Category>("/categories", { method: "POST", body: JSON.stringify(payload) }),
};

export const assetsApi = {
  list: (params?: { search?: string; category_id?: number; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.search) q.set("search", params.search);
    if (params?.category_id != null) q.set("category_id", String(params.category_id));
    if (params?.status) q.set("status", params.status);
    const qs = q.toString() ? `?${q}` : "";
    return req<Asset[]>(`/assets${qs}`);
  },
  get: (id: number) => req<Asset>(`/assets/${id}`),
  create: (payload: AssetInput) =>
    req<Asset>("/assets", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: number, payload: Partial<AssetInput>) =>
    req<Asset>(`/assets/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
};