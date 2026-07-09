import React, { useEffect, useState } from "react";
import { TrendingUp, DollarSign, Users, Percent, Copy, Check } from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Cell,
} from "recharts";
import DashboardLayout from "@/components/DashboardLayout";
import { api } from "@/lib/api";
import { toast } from "sonner";

const StatCard = ({ label, value, icon: Icon, accent, testid, sub }) => (
  <div
    data-testid={testid}
    className={`cg-kpi cg-surface rounded-xl border border-white/10 p-6 ${accent ? "cg-glow" : ""}`}
  >
    <div className="flex items-center justify-between mb-4">
      <p className="cg-overline text-slate-500">{label}</p>
      <div className="h-9 w-9 rounded-lg bg-emerald-500/10 flex items-center justify-center">
        <Icon className="h-4 w-4 text-emerald-400" />
      </div>
    </div>
    <p className="font-dash-head text-3xl font-bold text-white tracking-tight">{value}</p>
    {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
  </div>
);

const PIE_COLORS = ["#10B981", "#38BDF8", "#EF4444"];

export default function Dashboard() {
  const [kpis, setKpis] = useState(null);
  const [org, setOrg] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.get("/dashboard/kpis").then((r) => setKpis(r.data)).catch(() => {});
    api.get("/organization").then((r) => setOrg(r.data)).catch(() => {});
  }, []);

  const copyKey = () => {
    if (!org) return;
    navigator.clipboard.writeText(org.api_key);
    setCopied(true);
    toast.success("API key copied");
    setTimeout(() => setCopied(false), 1500);
  };

  const testUrl = org
    ? `${window.location.origin}/cancel?user_id=ext_1001&subscription_id=sub_demo_1001&api_key=${org.api_key}`
    : "";

  return (
    <DashboardLayout title="Overview" subtitle={org ? org.name : ""}>
      {!kpis ? (
        <div className="text-slate-500">Loading metrics…</div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard testid="kpi-churn-saved" label="Churn Saved" value={`${kpis.churn_saved_pct}%`}
              icon={Percent} sub={`${kpis.retained_count} of ${kpis.total_sessions} saved`} />
            <StatCard testid="kpi-mrr-recovered" label="MRR Recovered" value={`$${kpis.mrr_recovered.toLocaleString()}`}
              icon={DollarSign} accent sub="Monthly recurring revenue retained" />
            <StatCard testid="kpi-mrr-lost" label="MRR Lost" value={`$${kpis.mrr_lost.toLocaleString()}`}
              icon={TrendingUp} sub={`${kpis.canceled_count} cancellations`} />
            <StatCard testid="kpi-sessions" label="Total Sessions" value={kpis.total_sessions}
              icon={Users} sub={`${org?.customer_count ?? 0} customers protected`} />
          </div>

          {/* Integration card */}
          <div className="cg-surface rounded-xl border border-white/10 p-6" data-testid="integration-card">
            <p className="cg-overline text-emerald-400 mb-2">Integration</p>
            <h3 className="font-dash-head text-white text-lg font-semibold mb-3">Your cancel redirect URL</h3>
            <div className="flex flex-col md:flex-row gap-3 md:items-center">
              <code className="flex-1 text-xs md:text-sm text-slate-300 bg-black/40 rounded-lg px-4 py-3 border border-white/10 break-all">
                {testUrl}
              </code>
              <div className="flex gap-2">
                <button onClick={copyKey} data-testid="copy-api-key-button"
                  className="flex items-center gap-2 rounded-lg border border-white/15 px-4 py-3 text-sm text-white hover:bg-white/5 transition-colors">
                  {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />} API Key
                </button>
                <a href={testUrl} target="_blank" rel="noopener noreferrer" data-testid="test-flow-link"
                  className="rounded-lg bg-emerald-500 px-4 py-3 text-sm font-semibold text-[#0b0f19] hover:bg-emerald-400 transition-colors">
                  Test flow →
                </a>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* MRR trend */}
            <div className="cg-surface rounded-xl border border-white/10 p-6 lg:col-span-2" data-testid="mrr-trend-chart">
              <p className="cg-overline text-slate-500 mb-1">MRR Recovered</p>
              <h3 className="font-dash-head text-white font-semibold mb-4">Last 8 weeks</h3>
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={kpis.mrr_trend}>
                  <defs>
                    <linearGradient id="mrrFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10B981" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#10B981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                  <XAxis dataKey="week" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: "#0b0f19", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#fff" }} />
                  <Area type="monotone" dataKey="mrr" stroke="#10B981" strokeWidth={2} fill="url(#mrrFill)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Outcome breakdown */}
            <div className="cg-surface rounded-xl border border-white/10 p-6" data-testid="outcome-chart">
              <p className="cg-overline text-slate-500 mb-1">Outcomes</p>
              <h3 className="font-dash-head text-white font-semibold mb-4">Session results</h3>
              <div className="space-y-4">
                {kpis.outcome_breakdown.map((o, i) => {
                  const total = kpis.outcome_breakdown.reduce((s, x) => s + x.value, 0) || 1;
                  const pct = Math.round((o.value / total) * 100);
                  return (
                    <div key={o.name}>
                      <div className="flex justify-between text-sm text-slate-300 mb-1">
                        <span>{o.name}</span>
                        <span className="text-slate-500">{o.value} · {pct}%</span>
                      </div>
                      <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                        <div className="h-full rounded-full transition-all"
                          style={{ width: `${pct}%`, background: PIE_COLORS[i] }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Top reasons */}
          <div className="cg-surface rounded-xl border border-white/10 p-6" data-testid="reasons-chart">
            <p className="cg-overline text-slate-500 mb-1">Top Cancellation Reasons</p>
            <h3 className="font-dash-head text-white font-semibold mb-4">Why customers try to leave</h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={kpis.top_reasons} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
                <XAxis type="number" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="reason" stroke="#94a3b8" fontSize={12} width={150} tickLine={false} axisLine={false} />
                <Tooltip cursor={{ fill: "rgba(16,185,129,0.08)" }}
                  contentStyle={{ background: "#0b0f19", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#fff" }} />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={22}>
                  {kpis.top_reasons.map((_, i) => (
                    <Cell key={i} fill={i === 0 ? "#10B981" : "#1f7a5c"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
