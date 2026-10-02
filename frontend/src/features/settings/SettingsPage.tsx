import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";

import { API_BASE } from "../../config";

type Period = {
  id: number;
  label: string;
  start_date: string;
  end_date: string;
  status: "OPEN" | "LOCKED";
};

type AuditEvent = {
  id: number;
  timestamp: string;
  actor_id: number | null;
  actor_username: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  result: string;
};

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const b = await res.json();
      if (b && typeof b.detail === "string") detail = b.detail;
    } catch {}
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

type Tab = "periods" | "audit";

export default function SettingsPage() {
  const { user } = useAuth();
  const canViewAudit = user?.role === "admin" || user?.role === "accounting" || user?.role === "approver" || user?.role === "auditor";
  const canLock = user?.role === "admin" || user?.role === "approver";

  const [tab, setTab] = useState<Tab>("periods");
  const [periods, setPeriods] = useState<Period[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshPeriods = () => req<Period[]>("/periods").then(setPeriods).catch(() => {});
  const refreshAudit = () => req<AuditEvent[]>("/audit?limit=200").then(setAudit).catch(() => {});

  useEffect(() => {
    Promise.all([refreshPeriods(), canViewAudit ? refreshAudit() : Promise.resolve()])
      .finally(() => setLoading(false));
  }, []);

  const togglePeriod = async (label: string, current: string) => {
    setError(null);
    try {
      if (current === "OPEN") await req(`/periods/${label}/lock`, { method: "POST" });
      else await req(`/periods/${label}/unlock`, { method: "POST" });
      await refreshPeriods();
      await refreshAudit();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    }
  };

  if (loading) return <div className="text-sm text-slate-500">Loading settingsâ€¦</div>;

  return (
    <div className="space-y-4 max-w-5xl">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Settings</h1>
        <p className="text-sm text-slate-500">Period management and audit trail.</p>
      </div>

      <div className="flex gap-2 border-b border-slate-200">
        <button
          onClick={() => setTab("periods")}
          className={`px-4 py-2 text-sm -mb-px border-b-2 ${
            tab === "periods" ? "border-brand-600 font-medium text-slate-900" : "border-transparent text-slate-500"
          }`}
        >
          Accounting Periods
        </button>
        {canViewAudit && (
          <button
            onClick={() => setTab("audit")}
            className={`px-4 py-2 text-sm -mb-px border-b-2 ${
              tab === "audit" ? "border-brand-600 font-medium text-slate-900" : "border-transparent text-slate-500"
            }`}
          >
            Audit Log
          </button>
        )}
      </div>

      {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}

      {tab === "periods" && (
        <section className="bg-white border border-slate-200 rounded overflow-hidden">
          {periods.length === 0 ? (
            <div className="p-5 text-sm text-slate-500">No accounting periods yet. Run depreciation to create one.</div>
          ) : (
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">Period</th>
                  <th className="text-left px-4 py-2 font-medium">Start</th>
                  <th className="text-left px-4 py-2 font-medium">End</th>
                  <th className="text-left px-4 py-2 font-medium">Status</th>
                  <th className="text-right px-4 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {periods.map((p) => (
                  <tr key={p.id} className="border-t border-slate-100">
                    <td className="px-4 py-2 font-mono text-xs">{p.label}</td>
                    <td className="px-4 py-2">{new Date(p.start_date).toISOString().slice(0, 10)}</td>
                    <td className="px-4 py-2">{new Date(p.end_date).toISOString().slice(0, 10)}</td>
                    <td className="px-4 py-2">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                        p.status === "LOCKED" ? "bg-brand-500 text-white" : "bg-emerald-100 text-emerald-800"
                      }`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right">
                      {canLock && (
                        <button
                          onClick={() => togglePeriod(p.label, p.status)}
                          className="text-sm underline text-slate-700 hover:text-slate-900"
                        >
                          {p.status === "OPEN" ? "Lock" : "Unlock"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      {tab === "audit" && canViewAudit && (
        <section className="bg-white border border-slate-200 rounded overflow-x-auto">
          {audit.length === 0 ? (
            <div className="p-5 text-sm text-slate-500">No audit events yet.</div>
          ) : (
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">Timestamp</th>
                  <th className="text-left px-4 py-2 font-medium">Actor</th>
                  <th className="text-left px-4 py-2 font-medium">Action</th>
                  <th className="text-left px-4 py-2 font-medium">Target</th>
                  <th className="text-left px-4 py-2 font-medium">Result</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((e) => (
                  <tr key={e.id} className="border-t border-slate-100">
                    <td className="px-4 py-2 whitespace-nowrap text-xs text-slate-500">
                      {new Date(e.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-2">{e.actor_username ?? "â€”"}</td>
                    <td className="px-4 py-2 font-mono text-xs">{e.action}</td>
                    <td className="px-4 py-2 text-xs">
                      {e.target_type ? `${e.target_type} ${e.target_id ?? ""}` : "â€”"}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                        e.result === "SUCCESS" ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-700"
                      }`}>
                        {e.result}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  );
}