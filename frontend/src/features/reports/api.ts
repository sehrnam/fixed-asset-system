import { API_BASE } from "../../config";
import { AssetMovementReport, TableReport } from "./types";

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

// ---------- Types for the new monthly reports ----------

export type MonthlyReportSummary = {
  period_label: string;   // "YYYY-MM"
  filename: string;
  size_bytes: number;
  generated_at: string;
  trigger: string;
};

export type MonthlyReportList = {
  reports: MonthlyReportSummary[];
};

// ---------- API ----------

export const reportsApi = {
  // Existing reports — period params are now "YYYY-MM"
  assetRegister: () => req<TableReport>("/reports/asset-register"),

  depreciationSchedule: (periodLabel?: string) =>
    req<TableReport>(
      `/reports/depreciation-schedule${
        periodLabel ? `?period_label=${encodeURIComponent(periodLabel)}` : ""
      }`
    ),

  assetMovement: (periodLabel: string) =>
    req<AssetMovementReport>(
      `/reports/asset-movement?period_label=${encodeURIComponent(periodLabel)}`
    ),

  disposalRegister: () => req<TableReport>("/reports/disposal-register"),

  // ---------- v3.0 monthly reports ----------

  /**
   * List every monthly report that has been generated, newest first.
   */
  listMonthly: () => req<MonthlyReportList>("/reports/monthly"),

  /**
   * URL for downloading a monthly PDF as an attachment.
   * Used directly in an <a href> or window.location.
   */
  monthlyPdfDownloadUrl: (periodLabel: string) =>
    `${API_BASE}/reports/monthly/${encodeURIComponent(periodLabel)}/pdf`,

  /**
   * URL for opening the monthly PDF inline (for printing).
   * The browser opens the PDF viewer and the user prints from there.
   */
  monthlyPdfPrintUrl: (periodLabel: string) =>
    `${API_BASE}/reports/monthly/${encodeURIComponent(periodLabel)}/pdf?inline=true`,
};