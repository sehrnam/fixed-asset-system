import { downloadBlob, safeFilename } from "../reports/exportUtils";
import { SheetRender, SheetSummary, Workbook } from "./types";

import { API_BASE } from "../../config";

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    if (res.status === 204) return undefined as T;
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {}
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const workbookApi = {
  getDefault: () => req<Workbook>("/workbooks/default"),
  setActiveSheet: (workbookId: number, sheetId: number) =>
    req<Workbook>(`/workbooks/${workbookId}/active-sheet/${sheetId}`, { method: "POST" }),

  createSheet: (workbookId: number, name: string) =>
    req<SheetSummary>(`/workbooks/${workbookId}/sheets`, {
      method: "POST",
      body: JSON.stringify({ name }),
    }),

  renameSheet: (sheetId: number, name: string) =>
    req<SheetSummary>(`/sheets/${sheetId}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),

  deleteSheet: (sheetId: number) =>
    req<void>(`/sheets/${sheetId}`, { method: "DELETE" }),

  duplicateSheet: (sheetId: number, newName?: string) =>
    req<SheetSummary>(`/sheets/${sheetId}/duplicate`, {
      method: "POST",
      body: JSON.stringify({ new_name: newName ?? null }),
    }),

  reorderSheets: (workbookId: number, sheetIds: number[]) =>
    req<{ ok: boolean }>(`/workbooks/${workbookId}/sheets/reorder`, {
      method: "POST",
      body: JSON.stringify({ sheet_ids: sheetIds }),
    }),

  renderSheet: (sheetId: number) => req<SheetRender>(`/sheets/${sheetId}/render`),

  writeCells: (
    sheetId: number,
    cells: { row: number; col: number; raw: string }[]
  ) =>
    req<SheetRender>(`/sheets/${sheetId}/cells`, {
      method: "PATCH",
      body: JSON.stringify({ cells }),
    }),

  // --- M6b: export / import ---

  /**
   * Download the current user sheet as .xlsx.
   * System sheets must be exported via the Reports page, not this method.
   */
  exportSheetXlsx: async (sheetId: number, sheetName: string): Promise<void> => {
    await downloadBlob(
      `/exports/sheets/${sheetId}/xlsx`,
      safeFilename(sheetName, "xlsx")
    );
  },

  /**
   * Upload an .xlsx file and create a new user sheet from it.
   * The server enforces MIME type, size, and structural validation.
   * Imported content never overwrites authoritative accounting records.
   */
  importXlsx: async (
    workbookId: number,
    sheetName: string,
    file: File
  ): Promise<SheetSummary> => {
    const form = new FormData();
    form.append("workbook_id", String(workbookId));
    form.append("sheet_name", sheetName);
    form.append("file", file);

    const res = await fetch(`${API_BASE}/imports/xlsx-to-sheet`, {
      method: "POST",
      credentials: "include",
      body: form,
      // Do NOT set Content-Type: the browser must set the multipart boundary.
    });

    if (!res.ok) {
      let detail = `Import failed (${res.status})`;
      try {
        const body = await res.json();
        if (body && typeof body.detail === "string") detail = body.detail;
      } catch {}
      throw new Error(detail);
    }

    return (await res.json()) as SheetSummary;
  },
};