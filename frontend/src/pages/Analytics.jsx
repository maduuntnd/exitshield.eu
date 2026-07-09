import React, { useEffect, useState } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import { api } from "@/lib/api";

const OUTCOME_BADGE = {
  retained_discount: { label: "Saved · Discount", cls: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
  retained_pause: { label: "Saved · Pause", cls: "bg-sky-500/15 text-sky-400 border-sky-500/30" },
  canceled: { label: "Canceled", cls: "bg-red-500/15 text-red-400 border-red-500/30" },
  null: { label: "In progress", cls: "bg-white/10 text-slate-400 border-white/15" },
};

function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch { return iso; }
}

export default function Analytics() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    api.get("/analytics/sessions").then((r) => setSessions(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const filtered = sessions.filter((s) => {
    if (filter === "all") return true;
    if (filter === "saved") return (s.final_outcome || "").startsWith("retained");
    if (filter === "canceled") return s.final_outcome === "canceled";
    return true;
  });

  return (
    <DashboardLayout title="Analytics" subtitle="Recent cancellation sessions and outcomes">
      <div className="flex gap-2 mb-6">
        {[
          { k: "all", label: "All" },
          { k: "saved", label: "Saved" },
          { k: "canceled", label: "Canceled" },
        ].map((f) => (
          <button key={f.k} onClick={() => setFilter(f.k)} data-testid={`filter-${f.k}`}
            className={`rounded-lg px-4 py-2 text-sm transition-colors ${filter === f.k ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "text-slate-400 border border-white/10 hover:bg-white/5"}`}>
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-slate-500">Loading…</div>
      ) : (
        <div className="cg-surface rounded-xl border border-white/10 overflow-hidden" data-testid="sessions-table">
          <div className="grid grid-cols-12 px-6 py-3 border-b border-white/10 cg-overline text-slate-500 text-[0.65rem]">
            <div className="col-span-3">Customer</div>
            <div className="col-span-3">Reason</div>
            <div className="col-span-2">MRR</div>
            <div className="col-span-2">Outcome</div>
            <div className="col-span-2 text-right">Date</div>
          </div>
          {filtered.length === 0 ? (
            <div className="px-6 py-12 text-center text-slate-500">No sessions match this filter.</div>
          ) : (
            filtered.map((s) => {
              const badge = OUTCOME_BADGE[s.final_outcome] || OUTCOME_BADGE.null;
              return (
                <div key={s.id} data-testid={`session-row-${s.id}`}
                  className="grid grid-cols-12 items-center px-6 py-4 border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                  <div className="col-span-3 text-sm text-white truncate">{s.external_user_id || "—"}</div>
                  <div className="col-span-3 text-sm text-slate-400 truncate">{s.selected_reason || "—"}</div>
                  <div className="col-span-2 text-sm text-slate-300">${s.mrr || 0}</div>
                  <div className="col-span-2">
                    <span className={`inline-flex text-xs px-2.5 py-1 rounded-full border ${badge.cls}`}>{badge.label}</span>
                  </div>
                  <div className="col-span-2 text-right text-xs text-slate-500">{fmtDate(s.created_at)}</div>
                </div>
              );
            })
          )}
        </div>
      )}
    </DashboardLayout>
  );
}
