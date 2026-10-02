import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CURRENCY } from "../../config";
import { dashboardApi } from "./api";
import { Dashboard } from "./types";

function money(v: number) {
  return `${CURRENCY} ${v.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function Kpi({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded p-4">
      <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</div>
      <div className={`mt-2 text-xl font-semibold tabular-nums ${accent ?? "text-slate-900"}`}>
        {value}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    dashboardApi
      .get()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-sm text-slate-500">Loading dashboardâ€¦</div>;
  if (error) return <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500">Portfolio summary for period {data.current_period_label}</p>
        </div>
        <div className="flex gap-2">
          <Link to="/assets/new" className="rounded bg-brand-600 text-white px-3 py-2 text-sm font-medium hover:bg-brand-700">
            + Add Asset
          </Link>
          <Link to="/workbook" className="rounded border border-slate-300 px-3 py-2 text-sm">
            Open Workbook
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi label="Total Asset Cost" value={money(data.total_asset_cost)} />
        <Kpi label="Accumulated Depreciation" value={money(data.total_accumulated_depreciation)} />
        <Kpi label="Net Book Value" value={money(data.total_nbv)} accent="text-emerald-700" />
        <Kpi label={`Depreciation ${data.current_period_label}`} value={money(data.current_period_depreciation)} />
      </div>

      <section className="bg-white border border-slate-200 rounded">
        <div className="px-5 py-3 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-800">Category Summary</h2>
        </div>
        {data.category_summary.length === 0 ? (
          <div className="p-5 text-sm text-slate-500">No categories yet.</div>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="text-left px-5 py-2 font-medium">Category</th>
                <th className="text-right px-5 py-2 font-medium">Assets</th>
                <th className="text-right px-5 py-2 font-medium">Total Cost</th>
                <th className="text-right px-5 py-2 font-medium">Total NBV</th>
              </tr>
            </thead>
            <tbody>
              {data.category_summary.map((c) => (
                <tr key={c.category_id} className="border-t border-slate-100">
                  <td className="px-5 py-2">{c.category_name}</td>
                  <td className="px-5 py-2 text-right tabular-nums">{c.asset_count}</td>
                  <td className="px-5 py-2 text-right tabular-nums">{money(c.total_cost)}</td>
                  <td className="px-5 py-2 text-right tabular-nums">{money(c.total_nbv)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}