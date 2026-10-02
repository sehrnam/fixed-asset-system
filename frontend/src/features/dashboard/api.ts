import { Dashboard } from "./types";

import { API_BASE } from "../../config";

export const dashboardApi = {
  get: async (): Promise<Dashboard> => {
    const res = await fetch(`${API_BASE}/dashboard`, { credentials: "include" });
    if (!res.ok) throw new Error(`Failed to load dashboard (${res.status})`);
    return (await res.json()) as Dashboard;
  },
};