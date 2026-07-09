import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import PlanCard from "@/components/PlanCard";

export default function Pricing() {
  const [plans, setPlans] = useState([]);
  useEffect(() => {
    api.get("/billing/plans").then((r) => setPlans(r.data.plans)).catch(() => {});
  }, []);

  return (
    <div className="cg-dark min-h-screen font-dash-body">
      <header className="sticky top-0 z-30 border-b border-white/10 bg-[#0b0f19]/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-6 h-16">
          <Link to="/" className="flex items-center gap-2 text-white font-dash-head font-bold text-lg">
            <ShieldCheck className="text-emerald-400" /> ChurnGuard
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm text-slate-300 hover:text-white px-4 py-2 transition-colors">Sign in</Link>
            <Link to="/register" className="text-sm font-semibold rounded-full bg-emerald-500 text-[#0b0f19] px-5 py-2.5 hover:bg-emerald-400 transition-colors">Start free</Link>
          </div>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 py-20 text-center">
        <p className="cg-overline text-emerald-400 mb-4">Pricing</p>
        <h1 className="font-market-head text-4xl md:text-6xl font-black text-white tracking-tight">
          Pay for a fraction of what you save.
        </h1>
        <p className="mt-5 text-slate-400 max-w-xl mx-auto">
          Every plan starts with a 14-day free trial. No charge until it ends — cancel anytime.
        </p>

        <div className="mt-14 grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          {plans.map((p) => (
            <PlanCard
              key={p.id}
              plan={p}
              popular={p.id === "growth"}
              onSelect={() => {}}
              ctaLabel="Start 14-day trial"
              disabled={false}
            />
          ))}
        </div>

        <div className="mt-14">
          <Link to="/register" data-testid="pricing-cta-button"
            className="inline-flex items-center gap-2 rounded-full bg-emerald-500 text-[#0b0f19] px-8 py-4 font-semibold hover:bg-emerald-400 transition-colors">
            Start your free trial <ArrowRight className="h-4 w-4" />
          </Link>
          <p className="mt-4 text-xs text-slate-500">14 days free · Card required · Auto-converts to your plan when the trial ends</p>
        </div>
      </section>
    </div>
  );
}
