import { FormEvent, useEffect, useMemo, useState } from "react";
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

// -------- Monthly period helpers --------

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function currentMonthLabel(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function recentMonths(count: number): string[] {
  const out: string[] = [];
  const d = new Date();
  for (let i = 0; i < count; i++) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    out.push(`${y}-${m}`);
    d.setMonth(d.getMonth() - 1);
  }
  return out;
}

function prettyLabel(label: string): string {
  const parts = label.split("-");
  if (parts.length !== 2) return label;
  const y = parts[0];
  const mIdx = Number(parts[1]) - 1;
  if (mIdx < 0 || mIdx > 11) return label;
  return `${MONTH_NAMES[mIdx]} ${y}`;
}

// -------- Page --------

export default function DepreciationPage() {
  const { user } = useAuth();
  const canRun = user?.role === "admin" || user?.role === "accounting";

  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<number | "">("");
  const [schedule, setSchedule] = useState<DepreciationRecord[]>([]);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [scheduleError, setScheduleError] = useState<string | null>(null);

  const monthOptions = useMemo(() => recentMonths(24), []);
  const [throughPeriod, setThroughPeriod] = useState<string>(currentMonthLabel());
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
      const result = await depreciationApi.run(throughPeriod);
      setRunMessage(
        `Run complete: ${result.assets_processed} assets processed, ` +
          `${result.records_written} records written (through ${prettyLabel(
            result.through_period
          )}).`
      );
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
          Monthly straight-line depreciation. Runs automatically on the last day
          of each month; the controls below are for admin verification and testing.
        </p>
      </div>

      {canRun && (
        <section className="bg-white border border-slate-200 rounded p-5 space-y-3 max-w-xl">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">
              Run depreciation (admin)
            </h2>
            <p className="text-xs text-slate-500">
              Computes and stores monthly records for all active assets from each
              asset&apos;s acquisition month through the selected month.
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
              <span className="text-xs font-medium text-slate-600">
                Through month
              </span>
              <select
                value={throughPeriod}
                onChange={(e) => setThroughPeriod(e.target.value)}
                className="mt-1 w-48 rounded border border-slate-300 px-3 py-2 text-sm bg-white"
              >
                {monthOptions.map((m) => (
                  <option key={m} value={m}>
                    {prettyLabel(m)}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="submit"
              disabled={running}
              className="rounded bg-brand-600 text-white px-4 py-2 text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
            >
              {running ? "Running…" : "Run depreciation"}
            </button>
          </form>
        </section>
      )}

      <section className="space-y-3">
        <div className="flex items-end gap-3">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">
              Asset schedule
            </span>
            <select
              value={selectedAssetId}
              onChange={(e) =>
                setSelectedAssetId(e.target.value === "" ? "" : Number(e.target.value))
              }
              className="mt-1 w-96 rounded border border-slate-300 px-3 py-2 text-sm bg-white"
            >
              <option value="">Select an asset to view its schedule</option>
              {assets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.asset_code} — {a.name}
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
              <div className="text-sm text-slate-500">Loading…</div>
            ) : schedule.length === 0 ? (
              <div className="bg-white border border-dashed border-slate-300 rounded p-6 text-center text-sm text-slate-600">
                No depreciation records yet for this asset.
              </div>
            ) : (
              <div className="bg-white border border-slate-200 rounded overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-50 text-slate-600">
                    <tr>
                      <th className="text-left px-3 py-2 font-medium">Period</th>
                      <th className="text-left px-3 py-2 font-medium">Basis</th>
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
                        <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">
                          {r.period_label}
                        </td>
                        <td className="px-3 py-2 text-xs">
                          {r.is_first_month ? (
                            <span title="First-month proration">
                              First month{" "}
                              <span className="tabular-nums">
                                ({r.eligible_days}/{r.days_in_month} days)
                              </span>
                            </span>
                          ) : r.capped ? (
                            <span className="text-amber-700 font-medium">Capped</span>
                          ) : (
                            "Full month"
                          )}
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
                        <td className="px-3 py-2 text-xs text-slate-600">SL</td>
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