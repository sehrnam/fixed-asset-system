import { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { AuthProvider, useAuth } from "./features/auth/AuthContext";
import LoginPage from "./features/auth/LoginPage";
import AssetDetailPage from "./features/assets/AssetDetailPage";
import AssetFormPage from "./features/assets/AssetFormPage";
import AssetListPage from "./features/assets/AssetListPage";
import DashboardPage from "./features/dashboard/DashboardPage";
import DepreciationPage from "./features/depreciation/DepreciationPage";
import DisposalsPage from "./features/disposals/DisposalsPage";
import MonthlyReportsPage from "./features/reports/MonthlyReportsPage";
import ReportsPage from "./features/reports/ReportsPage";
import SettingsPage from "./features/settings/SettingsPage";
import WorkbookPage from "./features/workbook/WorkbookPage";

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <div className="p-6 text-sm text-slate-500">Loading…</div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="p-6 text-sm text-slate-500">Loading…</div>;
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/dashboard" replace /> : <LoginPage />}
      />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        {/* Dashboard (M5) */}
        <Route path="/dashboard" element={<DashboardPage />} />

        {/* Workbook (M4) */}
        <Route path="/workbook" element={<WorkbookPage />} />

        {/* Asset domain (M2) */}
        <Route path="/assets" element={<AssetListPage />} />
        <Route path="/assets/new" element={<AssetFormPage mode="create" />} />
        <Route path="/assets/:id" element={<AssetDetailPage />} />
        <Route path="/assets/:id/edit" element={<AssetFormPage mode="edit" />} />

        {/* Depreciation (M3 / v3.0 monthly) */}
        <Route path="/depreciation" element={<DepreciationPage />} />

        {/* Disposals (M5) */}
        <Route path="/disposals" element={<DisposalsPage />} />

        {/* Reports (M5) */}
        <Route path="/reports" element={<ReportsPage />} />

        {/* Monthly Reports (v3.0 - bank-style schedule + download/print) */}
        <Route path="/reports/monthly" element={<MonthlyReportsPage />} />

        {/* Settings (M5) */}
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}