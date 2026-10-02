import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";

const NAV = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/workbook", label: "Workbook" },
  { to: "/assets", label: "Assets" },
  { to: "/depreciation", label: "Depreciation" },
  { to: "/disposals", label: "Disposals" },
  { to: "/reports", label: "Reports" },
  { to: "/settings", label: "Settings" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="h-full flex">
      <aside className="w-56 bg-brand-600 text-white flex flex-col">
        <div className="px-4 py-4 border-b border-brand-700">
          <div className="font-semibold text-sm text-white">Fixed Asset</div>
          <div className="text-xs text-brand-100">Accounting Workbook</div>
        </div>

        <nav className="flex-1 px-2 py-4 space-y-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded text-sm ${
                  isActive
                    ? "bg-brand-500 text-white font-medium"
                    : "text-brand-50 hover:bg-brand-700 hover:text-white"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-3 border-t border-brand-700 text-xs">
          <div className="text-white truncate font-medium">{user?.full_name}</div>
          <div className="text-brand-100 capitalize">{user?.role}</div>
          <button
            onClick={onLogout}
            className="mt-2 text-brand-100 hover:text-white underline"
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}