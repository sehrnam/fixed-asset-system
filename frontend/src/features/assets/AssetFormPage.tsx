import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { assetsApi, categoriesApi } from "./api";
import { Category } from "./types";

const isoDateOnly = (v: string) => v.slice(0, 10);

export default function AssetFormPage({ mode }: { mode: "create" | "edit" }) {
  const { id } = useParams();
  const navigate = useNavigate();

  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(mode === "edit");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    asset_code: "",
    name: "",
    category_id: "" as number | "",
    cost: "",
    acquisition_date: "",
    useful_life_years: "",
    residual_value: "",
    description: "",
    location: "",
  });

  // Rate is derived from useful life (v3.0: straight-line only)
  const derivedRate = useMemo(() => {
    const life = Number(form.useful_life_years);
    if (!Number.isFinite(life) || life <= 0) return "";
    return (100 / life).toFixed(2);
  }, [form.useful_life_years]);

  useEffect(() => {
    categoriesApi.list().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    if (mode !== "edit" || !id) return;
    assetsApi
      .get(Number(id))
      .then((a) => {
        setForm({
          asset_code: a.asset_code,
          name: a.name,
          category_id: a.category_id,
          cost: String(a.cost),
          acquisition_date: isoDateOnly(a.acquisition_date),
          useful_life_years: String(a.useful_life_years),
          residual_value: String(a.residual_value),
          description: a.description ?? "",
          location: a.location ?? "",
        });
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load asset"))
      .finally(() => setLoading(false));
  }, [mode, id]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const payload = {
        asset_code: form.asset_code.trim() || null,
        name: form.name.trim(),
        category_id: Number(form.category_id),
        cost: Number(form.cost),
        acquisition_date: new Date(form.acquisition_date).toISOString(),
        useful_life_years: Number(form.useful_life_years),
        // v3.0: straight-line only
        depreciation_method: "straight_line" as const,
        residual_value: Number(form.residual_value || 0),
        // rate is informational; derived from useful life
        rate: derivedRate === "" ? null : Number(derivedRate),
        description: form.description.trim() || null,
        location: form.location.trim() || null,
      };

      if (mode === "create") {
        const created = await assetsApi.create(payload);
        navigate(`/assets/${created.id}`);
      } else {
        const updated = await assetsApi.update(Number(id), payload);
        navigate(`/assets/${updated.id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="text-sm text-slate-500">Loading…</div>;

  return (
    <div className="max-w-2xl space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">
          {mode === "create" ? "Add Asset" : "Edit Asset"}
        </h1>
        <p className="text-sm text-slate-500">
          {mode === "create"
            ? "Register a new fixed asset. Depreciation begins from the acquisition month."
            : "Update the accounting fields for this asset."}
        </p>
      </div>

      {error && (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      <form
        onSubmit={onSubmit}
        className="bg-white border border-slate-200 rounded p-5 space-y-4"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Asset code</span>
            <input
              value={form.asset_code}
              onChange={(e) => setForm({ ...form, asset_code: e.target.value })}
              placeholder="Auto-generated if left blank"
              disabled={mode === "edit"}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100"
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Name</span>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Category</span>
            <select
              value={form.category_id}
              onChange={(e) =>
                setForm({
                  ...form,
                  category_id: e.target.value === "" ? "" : Number(e.target.value),
                })
              }
              required
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm bg-white"
            >
              <option value="">Select a category</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Acquisition date</span>
            <input
              type="date"
              value={form.acquisition_date}
              onChange={(e) => setForm({ ...form, acquisition_date: e.target.value })}
              required
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Cost</span>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={form.cost}
              onChange={(e) => setForm({ ...form, cost: e.target.value })}
              required
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Residual value</span>
            <input
              type="number"
              step="0.01"
              min="0"
              value={form.residual_value}
              onChange={(e) => setForm({ ...form, residual_value: e.target.value })}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">
              Useful life (years)
            </span>
            <input
              type="number"
              step="1"
              min="1"
              value={form.useful_life_years}
              onChange={(e) =>
                setForm({ ...form, useful_life_years: e.target.value })
              }
              required
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">
              Annual rate (%)
            </span>
            <input
              value={derivedRate ? `${derivedRate}%` : ""}
              readOnly
              tabIndex={-1}
              placeholder="Derived from useful life"
              className="mt-1 w-full rounded border border-slate-200 px-3 py-2 text-sm bg-slate-50 text-slate-600"
            />
            <span className="text-xs text-slate-400">
              Straight-line: rate = 100 ÷ useful life
            </span>
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Location</span>
            <input
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
        </div>

        <label className="block">
          <span className="text-sm font-medium text-slate-700">Description</span>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={3}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
          />
        </label>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="rounded border border-slate-300 px-4 py-2 text-sm"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="rounded bg-brand-600 text-white px-4 py-2 text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
          >
            {submitting ? "Saving…" : mode === "create" ? "Create asset" : "Save changes"}
          </button>
        </div>
      </form>
    </div>
  );
}