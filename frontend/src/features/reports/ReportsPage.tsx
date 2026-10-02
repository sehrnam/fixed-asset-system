import { useState } from "react";
import { CURRENCY } from "../../config";
import { reportsApi } from "./api";
import { downloadBlob, safeFilename } from "./exportUtils";
import { AssetMovementReport, TableReport } from "./types";

type ReportKey = "asset-register" | "depreciation-schedule" | "asset-movement" | "disposal-register";

const REPORTS: { key: ReportKey; label: string; needsPeriod: boolean; exportable: boolean }[] = [
  { key: "asset-register", label: "Asset Register", needsPeriod: false, exportable: true },
  { key: "depreciation-schedule", label: "Depreciation Schedule", needsPeriod: false, exportable: true },
  { key: "asset-movement", label: "Asset Movement", needsPeriod: true, exportable: false },
  { key: "disposal-register", label: "Disposal Register", needsPeriod: false, exportable: true },
];

function money(v: number) {
  return `${CURRENCY} ${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function ReportsPage() {
  const currentYear = new Date().getFullYear();
  const [selected, setSelected] = useState<ReportKey>("asset-register");
  const [periodLabel, setPeriodLabel] = useState(String(currentYear));
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<null | "xlsx" | "pdf">(null);
  const [error, setError] = useState<string | null>(null);
  const [table, setTable] = useState<TableReport | null>(null);
  const [movement, setMovement] = useState<AssetMovementReport | null>(null);

  const selectedMeta = REPORTS.find((r) => r.key === selected);

  const run = async (key: ReportKey) => {
    setSelected(key);
    setLoading(true);
    setError(null);
    setTable(null);
    setMovement(null);
    try {
      if (key === "asset-register") setTable(await reportsApi.assetRegister());
      else if (key === "depreciation-schedule") setTable(await reportsApi.depreciationSchedule());
      else if (key === "disposal-register") setTable(await reportsApi.disposalRegister());
      else if (key === "asset-movement") setMovement(await reportsApi.assetMovement(periodLabel));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  };

  const onExport = async (format: "xlsx" | "pdf") => {
    if (!selectedMeta?.exportable) return;
    setError(null);
    setExporting(format);
    try {
      const url =
       format === "xlsx"
        ? `/exports/reports/${selected}/xlsx`
        : `/exports/reports/${selected}/pdf`;
      const filename = safeFilename(table?.title ?? selected, format);
      await downloadBlob(url, filename);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Reports</h1>
        <p className="text-sm text-slate-500">Generate fixed-asset accounting reports from authoritative data.</p>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        {REPORTS.map((r) => (
          <button
            key={r.key}
            onClick={() => run(r.key)}
            className={`px-3 py-2 text-sm rounded border ${
              selected === r.key
                ? "bg-brand-600 text-white border-brand-600"
                : "bg-white border-slate-300 text-slate-700 hover:bg-slate-50"
            }`}
          >
            {r.label}
          </button>
        ))}

        {selected === "asset-movement" && (
          <label className="flex items-center gap-2 ml-2">
            <span className="text-xs text-slate-600">Period</span>
            <input
              value={periodLabel}
              onChange={(e) => setPeriodLabel(e.target.value)}
              className="w-24 rounded border border-slate-300 px-2 py-1 text-sm"
            />
            <button
              onClick={() => run("asset-movement")}
              className="rounded bg-brand-600 text-white px-3 py-1 text-sm hover:bg-brand-700"
            >
              Run
            </button>
          </label>
        )}
      </div>

      {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}

      {loading && <div className="text-sm text-slate-500">Loading report…</div>}

      {table && (
        <div className="bg-white border border-slate-200 rounded overflow-x-auto">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between gap-4">
            <h2 className="text-sm font-semibold text-slate-800">{table.title}</h2>

            <div className="flex items-center gap-3">
              {table.totals && (
                <div className="text-xs text-slate-500 space-x-3">
                  {Object.entries(table.totals).map(([k, v]) => (
                    <span key={k}>
                      <span className="font-medium">{k.replace(/_/g, " ")}: </span>
                      <span className="tabular-nums">{money(v)}</span>
                    </span>
                  ))}
                </div>
              )}

              {selectedMeta?.exportable && (
                <div className="flex gap-2">
                  <button
                    onClick={() => onExport("xlsx")}
                    disabled={exporting !== null}
                    className="rounded border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                  >
                    {exporting === "xlsx" ? "Exporting…" : "Export XLSX"}
                  </button>
                  <button
                    onClick={() => onExport("pdf")}
                    disabled={exporting !== null}
                    className="rounded border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                  >
                    {exporting === "pdf" ? "Exporting…" : "Export PDF"}
                  </button>
                </div>
              )}
            </div>
          </div>

          {table.rows.length === 0 ? (
            <div className="p-5 text-sm text-slate-500">No data.</div>
          ) : (
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  {table.columns.map((c) => (
                    <th key={c} className="text-left px-4 py-2 font-medium whitespace-nowrap">{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    {row.map((v, j) => (
                      <td key={j} className="px-4 py-2 tabular-nums whitespace-nowrap">{v}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {movement && (
        <div className="bg-white border border-slate-200 rounded overflow-x-auto">
          <div className="px-5 py-3 border-b border-slate-100">
            <h2 className="text-sm font-semibold text-slate-800">Asset Movement — {movement.period_label}</h2>
            <p className="text-xs text-slate-500">Opening + Additions − Disposals = Closing</p>
          </div>
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="text-left px-4 py-2 font-medium">Category</th>
                <th className="text-right px-4 py-2 font-medium">Opening Cost</th>
                <th className="text-right px-4 py-2 font-medium">Additions</th>
                <th className="text-right px-4 py-2 font-medium">Disposals</th>
                <th className="text-right px-4 py-2 font-medium">Closing Cost</th>
                <th className="text-right px-4 py-2 font-medium">Dep Charge</th>
                <th className="text-right px-4 py-2 font-medium">Closing Accum</th>
                <th className="text-right px-4 py-2 font-medium">Closing NBV</th>
              </tr>
            </thead>
            <tbody>
              {movement.rows.map((r, i) => (
                <tr key={i} className="border-t border-slate-100">
                  <td className="px-4 py-2">{r.category_name}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{money(r.opening_cost)}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{money(r.additions)}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{money(r.disposals)}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{money(r.closing_cost)}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{money(r.dep_charge)}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{money(r.closing_accum)}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{money(r.closing_nbv)}</td>
                </tr>
              ))}
              <tr className="border-t-2 border-slate-300 bg-slate-50 font-medium">
                <td className="px-4 py-2">TOTAL</td>
                <td className="px-4 py-2 text-right tabular-nums">{money(movement.totals.opening_cost)}</td>
                <td className="px-4 py-2 text-right tabular-nums">{money(movement.totals.additions)}</td>
                <td className="px-4 py-2 text-right tabular-nums">{money(movement.totals.disposals)}</td>
                <td className="px-4 py-2 text-right tabular-nums">{money(movement.totals.closing_cost)}</td>
                <td className="px-4 py-2 text-right tabular-nums">{money(movement.totals.dep_charge)}</td>
                <td className="px-4 py-2 text-right tabular-nums">{money(movement.totals.closing_accum)}</td>
                <td className="px-4 py-2 text-right tabular-nums">{money(movement.totals.closing_nbv)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}