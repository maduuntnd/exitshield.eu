import React, { useEffect, useState, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Loader2, CreditCard, AlertTriangle, Clock, CheckCircle2, XCircle } from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import PlanCard from "@/components/PlanCard";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";

const STATUS_META = {
  trialing: { label: "Free trial", cls: "text-emerald-400", icon: Clock },
  active: { label: "Active", cls: "text-emerald-400", icon: CheckCircle2 },
  past_due: { label: "Payment due", cls: "text-amber-400", icon: AlertTriangle },
  suspended: { label: "Suspended", cls: "text-red-400", icon: XCircle },
  canceled: { label: "Canceled", cls: "text-slate-400", icon: XCircle },
};

function UsageBar({ label, used, limit }) {
  const pct = Math.min(100, Math.round((used / limit) * 100));
  const over = used >= limit;
  return (
    <div data-testid={`usage-${label.toLowerCase()}`}>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-slate-300">{label}</span>
        <span className={over ? "text-amber-400" : "text-slate-500"}>{used.toLocaleString()} / {limit.toLocaleString()}</span>
      </div>
      <div className="h-2 rounded-full bg-white/5 overflow-hidden">
        <div className={`h-full rounded-full transition-all ${over ? "bg-amber-500" : "bg-emerald-500"}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function Billing() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [state, setState] = useState(null);
  const [plans, setPlans] = useState([]);
  const [busyPlan, setBusyPlan] = useState(null);
  const [polling, setPolling] = useState(false);

  const load = useCallback(async () => {
    const [s, p] = await Promise.all([
      api.get("/billing/subscription"),
      api.get("/billing/plans"),
    ]);
    setState(s.data);
    setPlans(p.data.plans);
  }, []);

  useEffect(() => { load().catch(() => {}); }, [load]);

  // Poll payment status when returning from Stripe checkout.
  useEffect(() => {
    const sessionId = params.get("session_id");
    if (!sessionId) return;
    setPolling(true);
    let attempts = 0;
    const poll = async () => {
      attempts += 1;
      try {
        const { data } = await api.get(`/billing/checkout/status/${sessionId}`);
        if (data.payment_status === "paid") {
          toast.success("Payment method added — you're all set!");
          setPolling(false);
          setParams({}, { replace: true });
          await load();
          return;
        }
        if (data.status === "expired") {
          toast.error("Checkout expired. Please try again.");
          setPolling(false);
          setParams({}, { replace: true });
          return;
        }
      } catch { /* keep trying */ }
      if (attempts >= 6) {
        setPolling(false);
        setParams({}, { replace: true });
        return;
      }
      setTimeout(poll, 2000);
    };
    poll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectPlan = async (plan) => {
    setBusyPlan(plan.id);
    try {
      const { data } = await api.post("/billing/checkout", {
        plan_id: plan.id,
        origin_url: window.location.origin,
      });
      window.location.href = data.url;
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Could not start checkout");
      setBusyPlan(null);
    }
  };

  const cancelSub = async () => {
    try {
      await api.post("/billing/cancel");
      toast.success("Subscription will cancel at period end");
      await load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  if (!state) {
    return (
      <DashboardLayout title="Billing" subtitle="Plan, usage & payment">
        <div className="text-slate-500">Loading…</div>
      </DashboardLayout>
    );
  }

  const sub = state.subscription;
  const meta = STATUS_META[sub.status] || STATUS_META.canceled;
  const StatusIcon = meta.icon;

  return (
    <DashboardLayout title="Billing" subtitle="Plan, usage & payment">
      <div className="space-y-6">
        {polling && (
          <div className="flex items-center gap-2 text-emerald-400 text-sm" data-testid="payment-polling">
            <Loader2 className="h-4 w-4 animate-spin" /> Confirming your payment…
          </div>
        )}

        {/* Status banner */}
        {(sub.status === "past_due" || sub.status === "suspended") && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5 flex items-start gap-3" data-testid="billing-alert">
            <AlertTriangle className="h-5 w-5 text-amber-400 mt-0.5" />
            <div>
              <p className="text-white font-medium">
                {sub.status === "suspended" ? "Your account is suspended" : "Your trial ended — payment is due"}
              </p>
              <p className="text-slate-400 text-sm mt-1">
                {sub.status === "suspended"
                  ? "Creating offers is disabled until you add a payment method."
                  : "Add a payment method now to keep your save flows running without interruption."}
              </p>
            </div>
          </div>
        )}

        {/* Current plan + usage */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="cg-surface rounded-xl border border-white/10 p-6 lg:col-span-1" data-testid="current-plan-card">
            <p className="cg-overline text-slate-500 mb-3">Current plan</p>
            <div className="flex items-center justify-between">
              <span className="font-dash-head text-2xl font-bold text-white">{state.plan.name}</span>
              <span className={`inline-flex items-center gap-1.5 text-sm ${meta.cls}`}>
                <StatusIcon className="h-4 w-4" /> {meta.label}
              </span>
            </div>
            <p className="text-slate-400 text-sm mt-2">${state.plan.price}/month</p>
            {sub.status === "trialing" && (
              <p className="mt-4 text-sm text-emerald-400" data-testid="trial-countdown">
                {state.trial_days_left} day{state.trial_days_left === 1 ? "" : "s"} left in trial
              </p>
            )}
            {sub.status === "active" && sub.cancel_at_period_end && (
              <p className="mt-4 text-sm text-amber-400">Cancels at the end of this period</p>
            )}
            {(sub.status === "trialing" || sub.status === "active" || sub.status === "past_due") && (
              <button onClick={cancelSub} data-testid="cancel-subscription-button"
                className="mt-4 text-xs text-slate-500 hover:text-red-400 transition-colors">
                Cancel subscription
              </button>
            )}
          </div>

          <div className="cg-surface rounded-xl border border-white/10 p-6 lg:col-span-2">
            <p className="cg-overline text-slate-500 mb-4">Usage this period</p>
            <div className="space-y-5">
              <UsageBar label="Sessions" used={state.usage.sessions} limit={state.limits.sessions} />
              <UsageBar label="Offers" used={state.usage.offers} limit={state.limits.offers} />
            </div>
            {state.soft_limited && (
              <p className="mt-4 text-sm text-amber-400" data-testid="soft-limit-warning">
                You're approaching or over a plan limit. Upgrade to avoid interruptions.
              </p>
            )}
          </div>
        </div>

        {/* Plans */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <CreditCard className="h-4 w-4 text-emerald-400" />
            <h3 className="font-dash-head text-white font-semibold">
              {sub.payment_method_on_file ? "Change your plan" : "Add a payment method"}
            </h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {plans.map((p) => (
              <PlanCard
                key={p.id}
                plan={p}
                current={p.id === sub.plan_id && sub.payment_method_on_file}
                popular={p.id === "growth"}
                onSelect={selectPlan}
                disabled={busyPlan === p.id}
                ctaLabel={
                  busyPlan === p.id
                    ? "Redirecting…"
                    : sub.payment_method_on_file
                    ? (p.price > state.plan.price ? "Upgrade" : "Switch")
                    : "Add payment & activate"
                }
              />
            ))}
          </div>
          <p className="mt-4 text-xs text-slate-500">
            Secure checkout via Stripe. Note: with the demo test key, recurring auto-charge is simulated in-app —
            connect a live Stripe key for real recurring billing.
          </p>
        </div>
      </div>
    </DashboardLayout>
  );
}
