import { DepreciationRecord, PeriodSummary, RunResult } from "./types";

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
    } catch {
      // ignore non-JSON bodies
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export const depreciationApi = {
  run: (throughPeriod: string, assetIds?: number[]) =>
    req<RunResult>("/depreciation/run", {
      method: "POST",
      body: JSON.stringify({ through_period: throughPeriod, asset_ids: assetIds ?? null }),
    }),
  scheduleForAsset: (assetId: number) =>
    req<DepreciationRecord[]>(`/depreciation/assets/${assetId}`),
  periodSummary: (label: string) =>
    req<PeriodSummary>(`/depreciation/periods/${label}`),
};