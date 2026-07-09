import React, { useEffect, useState } from "react";
import { NavLink, useNavigate, Link } from "react-router-dom";
import { ShieldCheck, LayoutDashboard, Gift, BarChart3, LogOut, CreditCard, Clock, AlertTriangle, Plug } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";

const nav = [
  { to: "/dashboard", label: "Overview", icon: LayoutDashboard, end: true, testid: "nav-overview" },
  { to: "/dashboard/offers", label: "Offer Manager", icon: Gift, testid: "nav-offers" },
  { to: "/dashboard/analytics", label: "Analytics", icon: BarChart3, testid: "nav-analytics" },
  { to: "/dashboard/settings", label: "Integration", icon: Plug, testid: "nav-settings" },
  { to: "/dashboard/billing", label: "Billing", icon: CreditCard, testid: "nav-billing" },
];

function BillingBanner() {
  const [state, setState] = useState(null);
  useEffect(() => {
    api.get("/billing/subscription").then((r) => setState(r.data)).catch(() => {});
  }, []);
  if (!state) return null;
  const s = state.subscription.status;
  if (s === "active" && !state.subscription.cancel_at_period_end && !state.soft_limited) return null;

  let cfg = null;
  if (s === "trialing")
    cfg = { icon: Clock, tone: "emerald",
      text: `${state.trial_days_left} day${state.trial_days_left === 1 ? "" : "s"} left in your free trial. Add a payment method to keep your save flows running.`,
      cta: "Add payment" };
  else if (s === "past_due")
    cfg = { icon: AlertTriangle, tone: "amber", text: "Your trial ended and payment is due. Add a payment method to avoid interruption.", cta: "Fix billing" };
  else if (s === "suspended")
    cfg = { icon: AlertTriangle, tone: "red", text: "Your account is suspended. Creating offers is disabled until you update billing.", cta: "Reactivate" };
  else if (state.soft_limited)
    cfg = { icon: AlertTriangle, tone: "amber", text: "You're near a plan limit. Upgrade to keep scaling without interruption.", cta: "Upgrade" };
  else if (state.subscription.cancel_at_period_end)
    cfg = { icon: AlertTriangle, tone: "amber", text: "Your subscription is set to cancel at the end of this period.", cta: "Manage" };
  if (!cfg) return null;

  const tones = {
    emerald: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    amber: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    red: "border-red-500/30 bg-red-500/10 text-red-300",
  };
  const Icon = cfg.icon;
  return (
    <div className={`flex items-center justify-between gap-4 border-b px-6 md:px-8 py-3 ${tones[cfg.tone]}`} data-testid="billing-banner">
      <div className="flex items-center gap-2 text-sm">
        <Icon className="h-4 w-4 shrink-0" /> {cfg.text}
      </div>
      <Link to="/dashboard/billing" data-testid="banner-billing-cta"
        className="shrink-0 rounded-full bg-white/10 hover:bg-white/20 px-4 py-1.5 text-xs font-semibold text-white transition-colors">
        {cfg.cta}
      </Link>
    </div>
  );
}

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
        <BillingBanner />
        <div className="p-6 md:p-8">{children}</div>
      </main>
    </div>
  );
}
