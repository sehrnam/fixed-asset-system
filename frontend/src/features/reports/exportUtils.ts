import { API_BASE } from "../../config";

/**
 * Fetch a binary resource (XLSX/PDF) with credentials and trigger a
 * browser download.
 *
 * Prepends API_BASE so callers pass short paths like:
 *   "/exports/reports/asset-register/pdf"
 * rather than full URLs. Absolute URLs (http://, https://) are passed
 * through unchanged — useful for edge cases.
 *
 * Surfaces backend error messages (400/403/500) as thrown Errors so the
 * caller can display them inline.
 */
export async function downloadBlob(
  path: string,
  filename: string
): Promise<void> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const res = await fetch(url, { credentials: "include" });

  if (!res.ok) {
    let detail = `Download failed (${res.status})`;
    try {
      const body = await res.json();
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      // Non-JSON error body; keep the default message.
    }
    throw new Error(detail);
  }

  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(objectUrl);
}

/** Sanitize a name for use as a download filename. */
export function safeFilename(name: string, ext: string): string {
  const base = name.replace(/[^a-zA-Z0-9-_]/g, "_").slice(0, 64);
  return `${base || "download"}.${ext}`;
}