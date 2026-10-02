import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CURRENCY } from "../../config";
import { useAuth } from "../auth/AuthContext";
import { assetsApi, categoriesApi } from "./api";
import { Asset, Category } from "./types";

function formatMoney(v: number) {
  return `${CURRENCY} ${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: "bg-emerald-100 text-emerald-800",
  DISPOSED: "bg-slate-200 text-slate-700",
  RETIRED: "bg-amber-100 text-amber-800",
};

export default function AssetListPage() {
  const { user } = useAuth();
  const canEdit = user?.role === "admin" || user?.role === "accounting";

  const [assets, setAssets] = useState<Asset[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState<number | "">("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    categoriesApi.list().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    assetsApi
      .list({
        search: search || undefined,
        category_id: typeof categoryId === "number" ? categoryId : undefined,
        status: status || undefined,
      })
      .then(setAssets)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load assets"))
      .finally(() => setLoading(false));
  }, [search, categoryId, status]);

  const hasFilters = useMemo(
    () => Boolean(search || categoryId !== "" || status),
    [search, categoryId, status]
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Asset Register</h1>
          <p className="text-sm text-slate-500">All fixed assets in the system.</p>
        </div>
        {canEdit && (
          <Link
            to="/assets/new"
            className="rounded bg-brand-600 text-white px-4 py-2 text-sm font-medium hover:bg-brand-700"
          >
            + Add Asset
          </Link>
        )}
      </div>

      <div className="flex flex-wrap gap-3 items-end">
        <label className="flex-1 min-w-[200px]">
          <span className="text-xs font-medium text-slate-600">Search</span>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Code or name"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

        <label className="min-w-[180px]">
          <span className="text-xs font-medium text-slate-600">Category</span>
          <select
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value === "" ? "" : Number(e.target.value))}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm bg-white"
          >
            <option value="">All</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>

        <label className="min-w-[140px]">
          <span className="text-xs font-medium text-slate-600">Status</span>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm bg-white"
          >
            <option value="">All</option>
            <option value="ACTIVE">Active</option>
            <option value="DISPOSED">Disposed</option>
            <option value="RETIRED">Retired</option>
          </select>
        </label>
      </div>

      {error && (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-sm text-slate-500">Loadingâ€¦</div>
      ) : assets.length === 0 ? (
        <div className="bg-white border border-dashed border-slate-300 rounded p-8 text-center">
          <p className="text-sm text-slate-600">
            {hasFilters ? "No assets match the current filters." : "No assets have been added yet."}
          </p>
          {canEdit && !hasFilters && (
            <Link
              to="/assets/new"
              className="mt-3 inline-block text-sm text-slate-900 underline"
            >
              Add the first asset
            </Link>
          )}
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="text-left px-4 py-2 font-medium">Code</th>
                <th className="text-left px-4 py-2 font-medium">Name</th>
                <th className="text-left px-4 py-2 font-medium">Category</th>
                <th className="text-right px-4 py-2 font-medium">Cost</th>
                <th className="text-left px-4 py-2 font-medium">Acquired</th>
                <th className="text-right px-4 py-2 font-medium">Life (y)</th>
                <th className="text-left px-4 py-2 font-medium">Method</th>
                <th className="text-left px-4 py-2 font-medium">Status</th>
                <th className="text-right px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {assets.map((a) => (
                <tr key={a.id} className="border-t border-slate-100">
                  <td className="px-4 py-2 font-mono text-xs">{a.asset_code}</td>
                  <td className="px-4 py-2">{a.name}</td>
                  <td className="px-4 py-2 text-slate-600">{a.category_name ?? "â€”"}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{formatMoney(a.cost)}</td>
                  <td className="px-4 py-2">
                    {new Date(a.acquisition_date).toISOString().slice(0, 10)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">{a.useful_life_years}</td>
                  <td className="px-4 py-2 text-slate-600">
                    {a.depreciation_method === "straight_line" ? "Straight-line" : "Reducing balance"}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[a.status] ?? "bg-slate-100 text-slate-700"}`}>
                      {a.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <Link to={`/assets/${a.id}`} className="text-slate-700 hover:underline">
                      View
                    </Link>
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