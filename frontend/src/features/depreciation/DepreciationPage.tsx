import { FormEvent, useEffect, useState } from "react";
import { CURRENCY } from "../../config";
import { useAuth } from "../auth/AuthContext";
import { assetsApi } from "../assets/api";
import { Asset } from "../assets/types";
import { depreciationApi } from "./api";
import { DepreciationRecord } from "./types";

function money(v: number) {
  return `${CURRENCY} ${v.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export default function DepreciationPage() {
  const { user } = useAuth();
  const canRun = user?.role === "admin" || user?.role === "accounting";

  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<number | "">("");
  const [schedule, setSchedule] = useState<DepreciationRecord[]>([]);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [scheduleError, setScheduleError] = useState<string | null>(null);

  const currentYear = new Date().getFullYear();
  const [throughPeriod, setThroughPeriod] = useState<string>(String(currentYear));
  const [running, setRunning] = useState(false);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  useEffect(() => {
    assetsApi.list().then(setAssets).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedAssetId === "") {
      setSchedule([]);
      return;
    }
    setScheduleLoading(true);
    setScheduleError(null);
    depreciationApi
      .scheduleForAsset(Number(selectedAssetId))
      .then(setSchedule)
      .catch((e) =>
        setScheduleError(e instanceof Error ? e.message : "Failed to load schedule")
      )
      .finally(() => setScheduleLoading(false));
  }, [selectedAssetId]);

  const onRun = async (e: FormEvent) => {
    e.preventDefault();
    setRunError(null);
    setRunMessage(null);
    setRunning(true);
    try {
      const result = await depreciationApi.run(throughPeriod.trim());
      setRunMessage(
        `Run complete: ${result.assets_processed} assets processed, ` +
          `${result.records_written} records written (through ${result.through_period}).`
      );
      // Refresh the schedule if one is selected.
      if (selectedAssetId !== "") {
        const fresh = await depreciationApi.scheduleForAsset(Number(selectedAssetId));
        setSchedule(fresh);
      }
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Depreciation</h1>
        <p className="text-sm text-slate-500">
          Run the server-side depreciation engine and inspect asset schedules.
        </p>
      </div>

      {canRun && (
        <section className="bg-white border border-slate-200 rounded p-5 space-y-3 max-w-xl">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Run depreciation</h2>
            <p className="text-xs text-slate-500">
              Computes and stores period records for all active assets from each
              asset's acquisition year through the entered period.
            </p>
          </div>

          {runError && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
              {runError}
            </div>
          )}
          {runMessage && (
            <div className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-3 py-2">
              {runMessage}
            </div>
          )}

          <form onSubmit={onRun} className="flex items-end gap-3">
            <label className="block">
              <span className="text-xs font-medium text-slate-600">Through period</span>
              <input
                value={throughPeriod}
                onChange={(e) => setThroughPeriod(e.target.value)}
                placeholder="2024"
                required
                className="mt-1 w-32 rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <button
              type="submit"
              disabled={running}
              className="rounded bg-brand-600 text-white px-4 py-2 text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
            >
              {running ? "Runningâ€¦" : "Run depreciation"}
            </button>
          </form>
        </section>
      )}

      <section className="space-y-3">
        <div className="flex items-end gap-3">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Asset schedule</span>
            <select
              value={selectedAssetId}
              onChange={(e) =>
                setSelectedAssetId(e.target.value === "" ? "" : Number(e.target.value))
              }
              className="mt-1 w-80 rounded border border-slate-300 px-3 py-2 text-sm bg-white"
            >
              <option value="">Select an asset to view its schedule</option>
              {assets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.asset_code} â€” {a.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        {scheduleError && (
          <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
            {scheduleError}
          </div>
        )}

        {selectedAssetId !== "" && (
          <>
            {scheduleLoading ? (
              <div className="text-sm text-slate-500">Loadingâ€¦</div>
            ) : schedule.length === 0 ? (
              <div className="bg-white border border-dashed border-slate-300 rounded p-6 text-center text-sm text-slate-600">
                No depreciation records yet for this asset. Run depreciation above.
              </div>
            ) : (
              <div className="bg-white border border-slate-200 rounded overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-50 text-slate-600">
                    <tr>
                      <th className="text-left px-3 py-2 font-medium">Period</th>
                      <th className="text-right px-3 py-2 font-medium">Months</th>
                      <th className="text-right px-3 py-2 font-medium">Opening NBV</th>
                      <th className="text-right px-3 py-2 font-medium">Depreciation</th>
                      <th className="text-right px-3 py-2 font-medium">Accumulated</th>
                      <th className="text-right px-3 py-2 font-medium">Closing NBV</th>
                      <th className="text-left px-3 py-2 font-medium">Method</th>
                    </tr>
                  </thead>
                  <tbody>
                    {schedule.map((r) => (
                      <tr key={r.id} className="border-t border-slate-100">
                        <td className="px-3 py-2 font-mono text-xs">{r.period_label}</td>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {r.months_charged_this_period}
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {money(r.opening_nbv)}
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {money(r.depreciation)}
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {money(r.accumulated_depreciation)}
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {money(r.closing_nbv)}
                        </td>
                        <td className="px-3 py-2 text-xs text-slate-600">
                          {r.method === "straight_line" ? "SL" : "RB"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}