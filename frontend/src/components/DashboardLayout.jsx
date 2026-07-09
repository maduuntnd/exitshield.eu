import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { ShieldCheck, LayoutDashboard, Gift, BarChart3, LogOut } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const nav = [
  { to: "/dashboard", label: "Overview", icon: LayoutDashboard, end: true, testid: "nav-overview" },
  { to: "/dashboard/offers", label: "Offer Manager", icon: Gift, testid: "nav-offers" },
  { to: "/dashboard/analytics", label: "Analytics", icon: BarChart3, testid: "nav-analytics" },
];

export default function DashboardLayout({ children, title, subtitle }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="cg-dark min-h-screen font-dash-body flex">
      {/* Sidebar */}
      <aside className="hidden md:flex w-64 flex-col border-r border-white/10 bg-[#0b0f19] fixed h-screen">
        <div className="flex items-center gap-2 px-6 h-16 border-b border-white/10">
          <ShieldCheck className="text-emerald-400" />
          <span className="font-dash-head font-bold text-white text-lg">ChurnGuard</span>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              data-testid={n.testid}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                  isActive
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "text-slate-400 hover:text-white hover:bg-white/5"
                }`
              }
            >
              <n.icon className="h-4 w-4" />
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-white/10">
          <div className="flex items-center gap-3 mb-3">
            {user?.picture ? (
              <img src={user.picture} alt="" className="h-8 w-8 rounded-full" />
            ) : (
              <div className="h-8 w-8 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 text-sm font-semibold">
                {(user?.name || "U").charAt(0).toUpperCase()}
              </div>
            )}
            <div className="min-w-0">
              <p className="text-sm text-white truncate">{user?.name}</p>
              <p className="text-xs text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            data-testid="logout-button"
            className="w-full flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 md:ml-64">
        <header className="h-16 border-b border-white/10 flex items-center px-6 md:px-8 sticky top-0 bg-[#0b0f19]/80 backdrop-blur-md z-10">
          <div>
            <h1 className="font-dash-head text-lg font-semibold text-white" data-testid="page-title">{title}</h1>
            {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
          </div>
        </header>
        <div className="p-6 md:p-8">{children}</div>
      </main>
    </div>
  );
}
