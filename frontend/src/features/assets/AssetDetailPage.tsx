import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CURRENCY } from "../../config";
import { useAuth } from "../auth/AuthContext";
import { assetsApi } from "./api";
import { Asset } from "./types";

function money(v: number) {
  return `${CURRENCY} ${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function AssetDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const canEdit = user?.role === "admin" || user?.role === "accounting";

  const [asset, setAsset] = useState<Asset | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    assetsApi
      .get(Number(id))
      .then(setAsset)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="text-sm text-slate-500">Loadingâ€¦</div>;
  if (error) return <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>;
  if (!asset) return null;

  return (
    <div className="space-y-4 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs text-slate-500">{asset.asset_code}</div>
          <h1 className="text-xl font-semibold text-slate-900">{asset.name}</h1>
          <div className="text-sm text-slate-500">
            {asset.category_name} Â· {asset.status}
          </div>
        </div>
        <div className="flex gap-2">
          <Link to="/assets" className="rounded border border-slate-300 px-3 py-2 text-sm">
            Back
          </Link>
          {canEdit && (
            <Link
              to={`/assets/${asset.id}/edit`}
              className="rounded bg-brand-600 text-white px-3 py-2 text-sm font-medium hover:bg-brand-700"
            >
              Edit
            </Link>
          )}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded p-5 grid grid-cols-2 gap-y-3 gap-x-6 text-sm">
        <div>
          <div className="text-slate-500">Cost</div>
          <div className="font-medium tabular-nums">{money(asset.cost)}</div>
        </div>
        <div>
          <div className="text-slate-500">Residual value</div>
          <div className="font-medium tabular-nums">{money(asset.residual_value)}</div>
        </div>
        <div>
          <div className="text-slate-500">Acquisition date</div>
          <div className="font-medium">
            {new Date(asset.acquisition_date).toISOString().slice(0, 10)}
          </div>
        </div>
        <div>
          <div className="text-slate-500">Useful life</div>
          <div className="font-medium">{asset.useful_life_years} years</div>
        </div>
        <div>
          <div className="text-slate-500">Method</div>
          <div className="font-medium">
            {asset.depreciation_method === "straight_line" ? "Straight-line" : "Reducing balance"}
          </div>
        </div>
        <div>
          <div className="text-slate-500">Rate</div>
          <div className="font-medium">{asset.rate != null ? `${asset.rate}%` : "â€”"}</div>
        </div>
        <div className="col-span-2">
          <div className="text-slate-500">Location</div>
          <div className="font-medium">{asset.location ?? "â€”"}</div>
        </div>
        <div className="col-span-2">
          <div className="text-slate-500">Description</div>
          <div className="font-medium">{asset.description ?? "â€”"}</div>
        </div>
      </div>
    </div>
  );
}