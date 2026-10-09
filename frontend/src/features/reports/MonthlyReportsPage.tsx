import { useEffect, useState } from "react";
import { reportsApi, MonthlyReportSummary } from "./api";

function prettyLabel(label: string): string {
  const MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  const [y, m] = label.split("-");
  const idx = Number(m) - 1;
  if (idx < 0 || idx > 11) return label;
  return `${MONTHS[idx]} ${y}`;
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

export default function MonthlyReportsPage() {
  const [reports, setReports] = useState<MonthlyReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    reportsApi
      .listMonthly()
      .then((data) => setReports(data.reports))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  const onPrint = (period: string) => {
    window.open(reportsApi.monthlyPdfPrintUrl(period), "_blank");
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">
          Monthly Fixed Asset Reports
        </h1>
        <p className="text-sm text-slate-500">
          One PDF per month, generated automatically on the last day of each
          month. Click <strong>Download</strong> to save, or <strong>Print</strong>{" "}
          to open in the browser&apos;s PDF viewer.
        </p>
      </div>

      {error && (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-sm text-slate-500">Loading reports…</div>
      ) : reports.length === 0 ? (
        <div className="bg-white border border-dashed border-slate-300 rounded p-8 text-center text-sm text-slate-600">
          No monthly reports yet. They are generated automatically at
          month-end, or on-demand when you open this page for the first time
          in a new month.
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="text-left px-5 py-2 font-medium">Period</th>
                <th className="text-left px-5 py-2 font-medium">Generated</th>
                <th className="text-right px-5 py-2 font-medium">Size</th>
                <th className="text-left px-5 py-2 font-medium">Source</th>
                <th className="text-right px-5 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.period_label} className="border-t border-slate-100">
                  <td className="px-5 py-2 font-medium">
                    {prettyLabel(r.period_label)}
                  </td>
                  <td className="px-5 py-2 text-slate-600">
                    {new Date(r.generated_at).toLocaleString()}
                  </td>
                  <td className="px-5 py-2 text-right tabular-nums text-slate-600">
                    {fmtSize(r.size_bytes)}
                  </td>
                  <td className="px-5 py-2 text-xs text-slate-500 capitalize">
                    {r.trigger.replace(/_/g, " ")}
                  </td>
                  <td className="px-5 py-2 text-right">
                    <div className="flex gap-3 justify-end">
                      <a
                        href={reportsApi.monthlyPdfDownloadUrl(r.period_label)}
                        download={r.filename}
                        className="text-brand-700 hover:underline text-sm font-medium"
                      >
                        Download
                      </a>
                      <button
                        onClick={() => onPrint(r.period_label)}
                        className="text-slate-700 hover:underline text-sm font-medium"
                      >
                        Print
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}