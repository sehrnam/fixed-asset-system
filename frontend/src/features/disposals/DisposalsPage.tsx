import { FormEvent, useEffect, useState } from "react";
import { CURRENCY } from "../../config";
import { useAuth } from "../auth/AuthContext";
import { assetsApi } from "../assets/api";
import { Asset } from "../assets/types";
import { disposalsApi } from "./api";
import { Disposal } from "./types";

function money(v: number) {
  return `${CURRENCY} ${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: "bg-amber-100 text-amber-800",
  APPROVED: "bg-emerald-100 text-emerald-800",
  REJECTED: "bg-red-100 text-red-700",
};

export default function DisposalsPage() {
  const { user } = useAuth();
  const canRequest = user?.role === "admin" || user?.role === "accounting";
  const canApprove = user?.role === "admin" || user?.role === "approver";

  const [items, setItems] = useState<Disposal[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    asset_id: "" as number | "",
    disposal_date: "",
    proceeds: "",
    reason: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const refresh = () =>
    disposalsApi.list().then(setItems).catch((e) => setError(e instanceof Error ? e.message : "Load failed"));

  useEffect(() => {
    Promise.all([
      refresh(),
      assetsApi.list({ status: "ACTIVE" }).then(setAssets),
    ]).finally(() => setLoading(false));
  }, []);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      await disposalsApi.create({
        asset_id: Number(form.asset_id),
        disposal_date: new Date(form.disposal_date).toISOString(),
        proceeds: Number(form.proceeds),
        reason: form.reason.trim() || null,
      });
      setShowForm(false);
      setForm({ asset_id: "", disposal_date: "", proceeds: "", reason: "" });
      await refresh();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Failed to submit");
    } finally {
      setSubmitting(false);
    }
  };

  const onApprove = async (id: number) => {
    try {
      await disposalsApi.approve(id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed");
    }
  };

  const onReject = async (id: number) => {
    if (!confirm("Reject this disposal request?")) return;
    try {
      await disposalsApi.reject(id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reject failed");
    }
  };

  if (loading) return <div className="text-sm text-slate-500">Loadingâ€¦</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Disposals</h1>
          <p className="text-sm text-slate-500">
            Request â†’ Approve â†’ Finalize. Gain/loss is computed by the accounting engine.
          </p>
        </div>
        {canRequest && (
          <button
            onClick={() => setShowForm((v) => !v)}
            className="rounded bg-brand-600 text-white px-4 py-2 text-sm font-medium hover:bg-brand-700"
          >
            {showForm ? "Cancel" : "+ Request Disposal"}
          </button>
        )}
      </div>

      {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}

      {showForm && (
        <form onSubmit={onSubmit} className="bg-white border border-slate-200 rounded p-5 space-y-4 max-w-xl">
          <h2 className="text-sm font-semibold text-slate-800">New disposal request</h2>

          {formError && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{formError}</div>}

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Asset</span>
            <select
              value={form.asset_id}
              onChange={(e) => setForm({ ...form, asset_id: e.target.value === "" ? "" : Number(e.target.value) })}
              required
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm bg-white"
            >
              <option value="">Select an active asset</option>
              {assets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.asset_code} â€” {a.name}
                </option>
              ))}
            </select>
          </label>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Disposal date</span>
              <input
                type="date"
                value={form.disposal_date}
                onChange={(e) => setForm({ ...form, disposal_date: e.target.value })}
                required
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </label>

            <label className="block">
              <span className="text-sm font-medium text-slate-700">Proceeds</span>
              <input
                type="number"
                step="0.01"
                min="0"
                value={form.proceeds}
                onChange={(e) => setForm({ ...form, proceeds: e.target.value })}
                required
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
          </div>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Reason (optional)</span>
            <textarea
              value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })}
              rows={3}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </label>

          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowForm(false)} className="rounded border border-slate-300 px-4 py-2 text-sm">
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded bg-brand-600 text-white px-4 py-2 text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
            >
              {submitting ? "Submittingâ€¦" : "Submit request"}
            </button>
          </div>
        </form>
      )}

      {items.length === 0 ? (
        <div className="bg-white border border-dashed border-slate-300 rounded p-8 text-center text-sm text-slate-600">
          No disposal requests yet.
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="text-left px-4 py-2 font-medium">Asset</th>
                <th className="text-left px-4 py-2 font-medium">Disposal date</th>
                <th className="text-right px-4 py-2 font-medium">Proceeds</th>
                <th className="text-right px-4 py-2 font-medium">NBV</th>
                <th className="text-right px-4 py-2 font-medium">Gain/Loss</th>
                <th className="text-left px-4 py-2 font-medium">Status</th>
                <th className="text-right px-4 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((d) => (
                <tr key={d.id} className="border-t border-slate-100">
                  <td className="px-4 py-2">
                    <div className="font-mono text-xs text-slate-500">{d.asset_code}</div>
                    <div>{d.asset_name}</div>
                  </td>
                  <td className="px-4 py-2">{new Date(d.disposal_date).toISOString().slice(0, 10)}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{money(d.proceeds)}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{money(d.nbv_at_disposal)}</td>
                  <td className={`px-4 py-2 text-right tabular-nums font-medium ${d.gain_loss >= 0 ? "text-emerald-700" : "text-red-700"}`}>
                    {money(d.gain_loss)}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[d.status]}`}>
                      {d.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    {d.status === "PENDING" && canApprove && (
                      <div className="flex gap-2 justify-end">
                        <button onClick={() => onApprove(d.id)} className="text-emerald-700 hover:underline text-sm">Approve</button>
                        <button onClick={() => onReject(d.id)} className="text-red-700 hover:underline text-sm">Reject</button>
                      </div>
                    )}
                    {d.status === "PENDING" && !canApprove && (
                      <span className="text-xs text-slate-400">Awaiting approver</span>
                    )}
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