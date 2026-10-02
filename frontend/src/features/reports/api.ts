import { AssetMovementReport, TableReport } from "./types";

import { API_BASE } from "../../config";

async function req<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { credentials: "include" });
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

export const reportsApi = {
  assetRegister: () => req<TableReport>("/reports/asset-register"),
  depreciationSchedule: (periodLabel?: string) =>
    req<TableReport>(`/reports/depreciation-schedule${periodLabel ? `?period_label=${encodeURIComponent(periodLabel)}` : ""}`),
  assetMovement: (periodLabel: string) =>
    req<AssetMovementReport>(`/reports/asset-movement?period_label=${encodeURIComponent(periodLabel)}`),
  disposalRegister: () => req<TableReport>("/reports/disposal-register"),
};